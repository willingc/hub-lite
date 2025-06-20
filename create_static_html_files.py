from __future__ import annotations

import ast
import json
import logging
import os
from string import Template

import pandas as pd
from markdown_it import MarkdownIt
from markdown_it.common.utils import escapeHtml
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer

# Configure logging
logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
MISSING_LEXERS = [
    "angular2",
    "bitex",
    "commandline",
    "math",
    "mermaid",
    "{important}",
    "{note}",
    "{warning}",
]


class MarkdownRenderer:
    """Handles markdown-to-HTML conversion with code highlighting."""

    @staticmethod
    def _highlight_code(code, lang_name, lang_attrs):
        """Highlight code using Pygments with the signature markdown-it expects."""
        try:
            lexer = get_lexer_by_name(lang_name)
        except Exception as e:
            if lang_name in MISSING_LEXERS:
                logger.warning(f"Lexer {lang_name} is missing. Using guess_lexer: {e}")
            else:
                logger.error(f"Unknown error. Using guess_lexer: {e}")
            lexer = guess_lexer(code)

        formatter = HtmlFormatter()
        return highlight(code, lexer, formatter)

    @staticmethod
    def _code_block_plugin(md):
        """Plugin to render indented code blocks the same as fenced code blocks."""

        def _render_code_block(tokens, idx, options, env):
            token = tokens[idx]
            return (
                "<pre"
                + md.renderer.renderAttrs(token)
                + "><code>"
                + MarkdownRenderer._highlight_code(escapeHtml(token.content), "", {})
                + "</code></pre>\n"
            )

        md.renderer.rules["code_block"] = _render_code_block

    @classmethod
    def create_renderer(cls):
        """Create and return a configured markdown renderer."""
        return MarkdownIt("gfm-like", {"highlight": cls._highlight_code}).use(
            cls._code_block_plugin
        )


class HtmlGenerator:
    """Generates HTML content for plugin pages."""

    def __init__(self, md_renderer):
        self.md_renderer = md_renderer

    def generate_plugin_types_html(self, row):
        """Generate HTML for plugin types section."""
        plugin_types = []
        if not pd.isna(row.get("contributions_readers_0_command")):
            plugin_types.append("reader")
        if not pd.isna(row.get("contributions_writers_0_command")):
            plugin_types.append("writer")
        if not pd.isna(row.get("contributions_widgets_0_command")):
            plugin_types.append("widget")
        if not pd.isna(row.get("contributions_sample_data_0_command")):
            plugin_types.append("sample_data")

        if not plugin_types:
            return ""

        html = '<ul class="MetadataList_list__3DlqI list-none text-sm leading-normal inline space-y-sds-s MetadataList_inline__jHQLo">'
        for pt in plugin_types:
            html += f'<li class="MetadataList_textItem__KKmMN"><a class="MetadataList_textItem__KKmMN underline" href="../index.html?pluginType={pt}">{pt.capitalize()}</a></li>'
        html += "</ul>"
        return html

    def generate_open_extensions_html(self, row):
        """Generate HTML for file open extensions section."""
        if pd.isna(row.get("contributions_readers_0_filename_patterns")):
            return ""

        try:
            patterns = ast.literal_eval(
                row.get("contributions_readers_0_filename_patterns")
            )
            if not patterns:
                return ""

            html = '<ul class="MetadataList_list__3DlqI list-none text-sm leading-normal inline space-y-sds-s MetadataList_inline__jHQLo">'
            for pattern in patterns:
                html += f'<li class="MetadataList_textItem__KKmMN"><a class="MetadataList_textItem__KKmMN underline" href="../index.html?readerFileExtensions={pattern}">{pattern}</a></li>'
            html += "</ul>"
            return html
        except (ValueError, SyntaxError):
            logger.warning(
                f"Invalid pattern format: {row.get('contributions_readers_0_filename_patterns')}"
            )
            return ""

    def generate_save_extensions_html(self, row):
        """Generate HTML for file save extensions section."""
        file_extensions = []

        for col in [
            "contributions_writers_0_filename_extensions",
            "contributions_writers_1_filename_extensions",
        ]:
            if not pd.isna(row.get(col)):
                try:
                    file_extensions.extend(ast.literal_eval(row.get(col)))
                except (ValueError, SyntaxError):
                    logger.warning(f"Invalid extension format in {col}: {row.get(col)}")

        if not file_extensions:
            return ""

        html = '<ul class="MetadataList_list__3DlqI list-none text-sm leading-normal inline space-y-sds-s MetadataList_inline__jHQLo">'
        for ext in file_extensions:
            html += f'<li class="MetadataList_textItem__KKmMN"><a class="MetadataList_textItem__KKmMN underline" href="../index.html?writerFileExtensions={ext}">{ext}</a></li>'
        html += "</ul>"
        return html

    def generate_requirements_html(self, row):
        """Generate HTML for requirements section."""
        if pd.isna(row.get("package_metadata_requires_dist")):
            return ""

        try:
            requirements = ast.literal_eval(row.get("package_metadata_requires_dist"))
            if not requirements:
                return ""

            html = (
                '<ul class="MetadataList_list__3DlqI list-none text-sm leading-normal">'
            )
            for req in requirements:
                html += f'<li class="MetadataList_textItem__KKmMN">{req}</li>'
            html += "</ul>"
            return html
        except (ValueError, SyntaxError):
            logger.warning(
                f"Invalid requirements format: {row.get('package_metadata_requires_dist')}"
            )
            return ""

    @staticmethod
    def parse_version_specifier(specifier, default_min_version="3.6"):
        """Parse Python version specifiers to get min and max versions."""
        min_version = default_min_version
        max_version = None

        for spec in specifier.split(","):
            if ">=" in spec:
                min_version = spec.split(">=")[1]
            elif "<=" in spec:
                max_version = spec.split("<=")[1]
            elif "<" in spec:
                max_version = str(float(spec.split("<")[1]) - 0.1)

        return min_version, max_version

    def generate_python_versions_html(
        self, row, max_supported_version="3.11", default_min_version="3.6"
    ):
        """Generate HTML for Python versions section."""
        if pd.isna(row.get("package_metadata_requires_python")):
            return ""

        requirement = row.get("package_metadata_requires_python")
        min_version, max_version = self.parse_version_specifier(
            requirement, default_min_version
        )

        # Use the given maximum version if no upper bound is specified
        max_version = max_version if max_version else max_supported_version

        try:
            min_minor = int(min_version.split(".")[1])
            max_minor = int(max_version.split(".")[1])

            # Generate a list of versions from min_version to max_version
            versions = [f"3.{v}" for v in range(min_minor, max_minor + 1)]

            html = '<ul class="MetadataList_list__3DlqI list-none text-sm leading-normal inline space-y-sds-s MetadataList_inline__jHQLo">'
            for version in versions:
                html += f'<li class="MetadataList_textItem__KKmMN"><a class="MetadataList_textItem__KKmMN underline" href="../index.html?python={version}">{version}</a></li>'
            html += "</ul>"
            return html
        except (ValueError, IndexError):
            logger.warning(f"Invalid Python version format: {requirement}")
            return ""

    @staticmethod
    def get_os_html(classifiers):
        """Generate HTML for operating system compatibility."""
        return (
            '<ul class="MetadataList_list__3DlqI list-none text-sm leading-normal">'
            '<li class="flex justify-between items-center"><span '
            'class="text-napari-gray font-normal lowercase">Information not '
            "submitted</span></li>"
            "</ul>"
        )

    def generate_home_html(self, home_pypi, home_github, home_other):
        """Generate HTML for homepage links section."""
        html = f'''
        <div class="flex items-center" style="gap: 10px; ; align-items: center;"">
            <a href="{home_pypi}" rel="noreferrer" target="_blank">
            <img src="../static/images/PyPI_logo.svg.png" alt="PyPI" style="height: 42px;" />
            </a>
        '''

        # Add GitHub link if available
        if home_github and str(home_github).lower() not in ["n/a", "none", "nan", ""]:
            html += f'''
            <a href="{home_github}" rel="noreferrer" target="_blank">
                <img src="../static/images/GitHub_Invertocat_Logo.svg.png" alt="GitHub" style="height: 42px;" />
            </a>
            '''

        # Add other link if available
        if home_other and str(home_other).lower() not in ["n/a", "none", "nan", ""]:
            html += f'''
            <a href="{home_other}" rel="noreferrer" target="_blank">
            <svg width="21" height="21" viewBox="0 0 21 21" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="10.8331" cy="10.0835" r="9.33333" stroke="#000" stroke-width="1.33333"></circle>
                <path
                    d="M15.4998 10.0835C15.4998 12.7576 14.9202 15.1456 14.0161 16.8408C13.0967 18.5648 11.9398 19.4168 10.8331 19.4168C9.7264 19.4168 8.56951 18.5648 7.65009 16.8408C6.74594 15.1456 6.16642 12.7576 6.16642 10.0835C6.16642 7.40935 6.74594 5.02142 7.65009 3.32615C8.56951 1.60224 9.7264 0.750163 10.8331 0.750163C11.9398 0.750163 13.0967 1.60224 14.0161 3.32615C14.9202 5.02142 15.4998 7.40935 15.4998 10.0835Z"
                    stroke="#000" stroke-width="1.33333"></path>
                <path d="M10.8331 0.270996V19.896" stroke="#000" stroke-width="1.33333"></path>
                <path d="M1.02063 10.0835L20.6456 10.0835" stroke="#000" stroke-width="1.33333"></path>
            </svg>
            </a>
            '''

        html += "</div>"
        return html

    def process_markdown_description(self, description):
        """Process markdown description to HTML."""
        if pd.isna(description):
            return "Not available"

        # Remove the first Markdown header if present
        lines = description.split("\n")
        if lines and lines[0].startswith("#"):
            description = "\n".join(lines[1:])

        return self.md_renderer.render(description)

    def generate_plugin_html(self, row, template, plugin_dir):
        """Generate HTML for a plugin page using the template."""
        # Process description
        html_description = self.process_markdown_description(
            row["package_metadata_description"]
        )

        # Generate HTML sections
        plugin_types_html = self.generate_plugin_types_html(row)
        openfile_types_html = self.generate_open_extensions_html(row)
        savefile_types_html = self.generate_save_extensions_html(row)
        requirements_html = self.generate_requirements_html(row)
        python_versions_html = self.generate_python_versions_html(row)
        home_html = self.generate_home_html(
            row["home_pypi"], row["home_github"], row["home_other"]
        )

        # Prepare data for template
        row_data = {
            col: (str(row[col]) if not pd.isna(row[col]) else "Not available")
            for col in row.index
        }

        # Add HTML sections to data
        row_data.update(
            {
                "open_extension": openfile_types_html,
                "save_extension": savefile_types_html,
                "plugin_types": plugin_types_html,
                "requirements": requirements_html,
                "python_versions": python_versions_html,
                "os": self.get_os_html(row),
                "package_metadata_description": html_description,
                "home_link": home_html,
            }
        )

        # Fill template and save file
        filled_template = Template(template).safe_substitute(row_data)

        os.makedirs(plugin_dir, exist_ok=True)
        with open(f"{plugin_dir}/{row['html_filename']}", "w") as file:
            file.write(filled_template)


class PluginListGenerator:
    """Generates the HTML list of all plugins."""

    @staticmethod
    def create_plugins_list_html(df_plugins, output_path):
        """Create HTML for the plugins list page."""
        html_content = "<html>\n<body>\n"

        for index, row in df_plugins.iterrows():
            # Fill NaN values
            row = row.fillna("N/A")

            # Get basic plugin info
            display_name = (
                row["display_name"] if row["display_name"] != "N/A" else "Unknown"
            )
            name = row["name"] if row["name"] != "N/A" else "unknown"
            normalized_name = (
                row["normalized_name"] if row["normalized_name"] != "N/A" else "unknown"
            )
            summary = row["summary"]
            authors = [row["author"]]
            release_date = row["created_at"]
            last_updated = row["modified_at"]

            # Determine plugin type
            plugin_type = []
            for contribution in ["readers", "writers", "widgets", "sample_data"]:
                if row[f"contributions_{contribution}_0_command"] != "N/A":
                    plugin_type.append(contribution.rstrip("s"))
            plugin_type = ", ".join(plugin_type) if plugin_type else "N/A"

            # Generate HTML for this plugin
            html_content += f'''
            <a class="col-span-2 screen-1425:col-span-3 searchResult py-sds-xl border-black border-t-2 last:border-b-2 hover:bg-hub-gray-100"
               data-testid="pluginSearchResult" href="./plugins/{normalized_name}.html" data-plugin-id="{index}">
                <article class="grid gap-x-sds-xl screen-495:gap-x-12 screen-600:grid-cols-2 screen-1425:grid-cols-napari-3" data-testid="searchResult">
                    <div class="col-span-2 screen-495:col-span-1 screen-1425:col-span-2 flex flex-col justify-between">
                        <div>
                            <h3 class="font-bold text-lg" data-testid="searchResultDisplayName">{display_name}</h3>
                            <span class="mt-sds-m screen-495:mt-3 text-[0.6875rem]" data-testid="searchResultName">{name}</span>
                            <p class="mt-3" data-testid="searchResultSummary">{summary}</p>
                        </div>
                        <ul class="mt-3 text-xs">
            '''

            for author in authors:
                html_content += f'<li class="my-sds-s font-bold PluginSearchResult_linkItem__Vvs7H" data-testid="searchResultAuthor">{author}</li>\n'

            html_content += f'''
                        </ul>
                    </div>
                    <ul class="mt-sds-l screen-600:m-0 space-y-1 text-sm col-span-2 screen-495:col-span-1">
                        <li class="grid grid-cols-[auto,1fr]" data-label="First released" data-testid="searchResultMetadata" data-value="{release_date}">
                            <h4 class="inline whitespace-nowrap">First released<!-- -->: </h4>
                            <span class="ml-sds-xxs font-bold">{release_date}</span>
                        </li>
                        <li class="grid grid-cols-[auto,1fr]" data-label="Last updated" data-testid="searchResultMetadata" data-value="{last_updated}">
                            <h4 class="inline whitespace-nowrap">Last updated<!-- -->: </h4>
                            <span class="ml-sds-xxs font-bold">{last_updated}</span>
                        </li>
                        <li class="grid grid-cols-[auto,1fr]" data-label="Plugin type" data-testid="searchResultMetadata" data-value="{plugin_type}">
                            <h4 class="inline whitespace-nowrap">Plugin type<!-- -->: </h4>
                            <span class="ml-sds-xxs font-bold">{plugin_type}</span>
                        </li>
                    </ul>
                    <div class="mt-sds-xl text-xs flex flex-col gap-sds-s col-span-2 screen-1425:col-span-3"></div>
                </article>
            </a>
            '''

        html_content += "</body>\n</html>"

        with open(output_path, "w") as file:
            file.write(html_content)


class StaticHtmlGenerator:
    """Main class for generating static HTML files."""

    def __init__(self, build_dir="."):
        self.build_dir = build_dir
        self.data_dir = f"{build_dir}/data"
        self.static_dir = f"{build_dir}/static"
        self.plugin_dir = f"{build_dir}/plugins"
        self.template_dir = f"{build_dir}/templates"

        # Initialize components
        self.md_renderer = MarkdownRenderer.create_renderer()
        self.html_generator = HtmlGenerator(self.md_renderer)
        self.plugin_list_generator = PluginListGenerator()

    def load_and_prepare_data(self):
        """Load plugin data and prepare it for HTML generation."""
        # Load DataFrame
        df_plugins = pd.read_csv(f"{self.data_dir}/final_plugins.csv")

        # Sort by modification date and reset index
        df_plugins = df_plugins.sort_values(by="modified_at", ascending=False)
        df_plugins.reset_index(drop=True, inplace=True)

        # Add ID and HTML filename
        df_plugins["plugin_id"] = df_plugins.index
        df_plugins["html_filename"] = df_plugins["normalized_name"].apply(
            lambda x: f"{x}.html"
        )

        return df_plugins

    def generate_manifest(self, df_plugins):
        """Generate plugins manifest JSON file."""
        plugins_manifest = df_plugins[["plugin_id", "html_filename"]].to_dict(
            orient="records"
        )
        manifest_path = f"{self.build_dir}/plugins_manifest.json"

        with open(manifest_path, "w") as f:
            json.dump(plugins_manifest, f, indent=4)

    def generate_all_html(self, df_plugins):
        """Generate all HTML files."""
        # Create plugins list HTML
        self.plugin_list_generator.create_plugins_list_html(
            df_plugins, f"{self.build_dir}/plugins_list.html"
        )

        # Load plugin template
        with open(f"{self.template_dir}/each_plugin_template.html") as file:
            template = file.read()

        # Generate individual plugin pages
        df_plugins.apply(
            lambda row: self.html_generator.generate_plugin_html(
                row, template, self.plugin_dir
            ),
            axis=1,
        )

    def run(self):
        """Run the complete HTML generation process."""
        # Load and prepare data
        df_plugins = self.load_and_prepare_data()

        # Generate manifest
        self.generate_manifest(df_plugins)

        # Generate all HTML files
        self.generate_all_html(df_plugins)


if __name__ == "__main__":
    build_dir = "./_build"
    generator = StaticHtmlGenerator(build_dir)
    generator.run()
