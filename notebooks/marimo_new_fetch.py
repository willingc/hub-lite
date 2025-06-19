import marimo

__generated_with = "0.14.0"
app = marimo.App(width="medium")


@app.cell
def _():
    """Get plugins data, clean the data, and convert it to a CSV file."""

    from __future__ import annotations

    import logging
    from concurrent.futures import ThreadPoolExecutor
    from urllib.parse import urljoin

    import janitor
    import pandas as pd
    import requests

    API_SUMMARY_URL = "https://npe2api.vercel.app/api/extended_summary"
    API_CONDA_MAP_URL = "https://npe2api.vercel.app/api/conda"
    API_CONDA_BASE_URL = "https://npe2api.vercel.app/api/conda/"
    API_MANIFEST_BASE_URL = "https://npe2api.vercel.app/api/manifest/"
    API_PYPI_BASE_URL = "https://npe2api.vercel.app/api/pypi/"

    # Define columns needed for the plugin html page
    PLUGIN_PAGE_COLUMNS = [
        "normalized_name",
        "name",
        "display_name",
        "version",
        "created_at",
        "modified_at",
        "author",
        "package_metadata_author_email",
        "license",
        "home",
        "package_metadata_home_page",
        "summary",
        "package_metadata_requires_python",
        "package_metadata_requires_dist",
        "package_metadata_description",
        "package_metadata_classifier",
        "package_metadata_project_url",
        "contributions_readers_0_command",
        "contributions_writers_0_command",
        "contributions_widgets_0_command",
        "contributions_sample_data_0_command",
        "contributions_readers_0_filename_patterns",
        "contributions_writers_0_filename_extensions",
        "contributions_writers_1_filename_extensions",
        "operating_system",
        "license_spdx_identifier",
    ]

    # Configure logging
    logging.basicConfig(
        level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    DEFAULT_TIMEOUT = 10  # Timeout for requests in seconds

    return (
        API_CONDA_MAP_URL,
        API_MANIFEST_BASE_URL,
        API_SUMMARY_URL,
        DEFAULT_TIMEOUT,
        ThreadPoolExecutor,
        logger,
        pd,
        requests,
        urljoin,
    )


@app.cell
def _(DEFAULT_TIMEOUT, logger, requests, urljoin):
    def fetch(url: str):
        """Fetches data from the given URL and returns it as a JSON object"""
        try:
            response = requests.get(url, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx, 5xx)
            logger.info(f"Successfully fetched data: {url}")
            return response.json()  # Assuming JSON response
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error occurred: {e}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error occurred: {e}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error occurred: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred: {e}")
        return None

    def split_dict_by_none_values(original_dict: dict) -> tuple[dict, dict]:
        """Split dictionary using dictionary comprehensions into two."""
        none_values = {
            name: url_fragment
            for name, url_fragment in original_dict.items()
            if url_fragment is None
        }
        valid_values = {
            name: url_fragment
            for name, url_fragment in original_dict.items()
            if url_fragment is not None
        }

        return none_values, valid_values

    def fetch_plugin_summary(url: str) -> dict:
        """Fetches plugin summary from the given URL"""
        logger.info(f"Fetching data from URL: {url}")
        return fetch(url)

    def fetch_conda_name_map(url: str) -> dict:
        """Fetches plugin summary from the given URL"""
        logger.info(f"Fetching data from URL: {url}")
        return fetch(url)

    def fetch_plugin_manifest(url_base: str, plugin_name: str) -> dict:
        """Fetches the manifest data for a given plugin"""
        url = urljoin(url_base, plugin_name)
        logger.info(f"Fetching data for manifest for: {plugin_name} from URL: {url}")
        return fetch(url)

    return (
        fetch_conda_name_map,
        fetch_plugin_manifest,
        fetch_plugin_summary,
        split_dict_by_none_values,
    )


@app.cell
def _():
    build_dir = "."
    return (build_dir,)


@app.cell
def _(build_dir):
    data_dir = f"{build_dir}/data"
    return


@app.cell
def _(API_CONDA_MAP_URL, fetch_conda_name_map, split_dict_by_none_values):
    # Get conda name map Key: pypi name Value: conda-forge entry
    conda_name_map_json_raw = fetch_conda_name_map(API_CONDA_MAP_URL)
    conda_location_missing, conda_location_exists = split_dict_by_none_values(
        conda_name_map_json_raw
    )
    print(
        f"{len(conda_name_map_json_raw)} = Nones: {len(conda_location_missing)} + Exists: {len(conda_location_exists)}"
    )

    return conda_location_exists, conda_location_missing


@app.cell
def _(conda_location_exists):
    conda_location_exists
    return


@app.cell
def _(conda_location_missing):
    conda_location_missing
    return


@app.cell
def _(API_MANIFEST_BASE_URL, fetch_plugin_manifest):
    # Get manifest for a plugin
    manifest_json_raw = fetch_plugin_manifest(
        API_MANIFEST_BASE_URL, "vollseg-napari-mtrack"
    )
    print(manifest_json_raw)
    return


@app.cell
def _(API_SUMMARY_URL, fetch_plugin_summary, pd):
    # Get a raw, uncleaned json file from the summary endpoint
    summary_json_raw = fetch_plugin_summary(API_SUMMARY_URL)
    df_summary_raw = pd.DataFrame(summary_json_raw)

    # Begin cleaning the raw dataframe
    df_summary_clean = (
        df_summary_raw
        .clean_names()
        .remove_empty()
    )
    return (df_summary_clean,)


@app.cell
def _(df_summary_clean):
    df_summary_clean
    return


@app.cell
def _(
    API_CONDA_MAP_URL,
    API_SUMMARY_URL,
    ThreadPoolExecutor,
    conda_name_map,
    fetch_conda,
    fetch_conda_name_map,
    fetch_manifest,
    fetch_plugin_summary,
    flatten_and_merge,
    pd,
):
    # --- Main Data Processing Function ---
    def build_plugins_dataframe() -> pd.DataFrame:
        summary_raw = fetch_plugin_summary(API_SUMMARY_URL)
        df_summary = pd.DataFrame(summary_raw)
        print(df_summary.head(2))

        conda_name_map_raw = fetch_conda_name_map(API_CONDA_MAP_URL)
        index = ["row1"]
        df_conda_name_map = pd.DataFrame(conda_name_map_raw, index=index)
        print(df_conda_name_map.head(2))

        def process_plugin(plugin):
            print(f"Processing {plugin}")
            plugin_data = plugin.copy()
            plugin_normalized_name = plugin.get("normalized_name")

            # Fetch and flatten Conda info and Manifest
            conda_info = (
                fetch_conda(plugin_normalized_name)
                if conda_name_map[plugin_normalized_name] is not None
                else {}
            )
            print(conda_info)
            manifest_info = fetch_manifest(plugin_normalized_name)
            print(manifest_info)
            if conda_info:
                flatten_and_merge(plugin_data, conda_info)

            if manifest_info:
                flatten_and_merge(plugin_data, manifest_info)

        with ThreadPoolExecutor() as executor:
            executor.map(process_plugin, df_summary)

    return


if __name__ == "__main__":
    app.run()
