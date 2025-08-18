# from .copernicus import CopernicusSTACClient
import json
from pathlib import Path

from .element84 import Element84STACClient
from .planetary import PlanetarySTACClient


def load_collection_config(config_filename: str) -> dict:
    """
    Loads the STAC collection-to-endpoint mapping from a JSON config file.

    Args:
        config_path (str): Path to the JSON config file.

    Returns:
        dict: Mapping of collection keys to STAC API endpoints.
    """
    CONFIG_FILENAME = config_filename
    CONFIG_DIR = Path(__file__).resolve().parents[3]/ "configs"
    CONFIG_PATH = CONFIG_DIR / CONFIG_FILENAME

    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")

    with CONFIG_PATH.open("r") as f:
        return json.load(f)


def _get_stac_client(url: str):
    if "planetarycomputer" in url:
        return PlanetarySTACClient(url)
    elif "earth-search.aws" in url:
        return Element84STACClient(url)
    # elif "copernicus" in url:
    #     return CopernicusSTACClient(url)
    else:
        raise ValueError(f"Unsupported STAC API: {url}")


def _validate_collection_exists(client, collection_id: str) -> bool:
    """
    Checks if the specified collection_id exists in the STAC client's catalog.

    Args:
        client: A STAC client instance.
        collection_id (str): The collection ID to validate.

    Returns:
        bool: True if collection exists, else raises ValueError.
    """
    collection_id = collection_id.lower()

    available_ids = [col.lower() for col in client.get_available_collections()]

    if collection_id in available_ids:
        return True

    raise ValueError(
        f"Collection '{collection_id}' not found in STAC endpoint.\n"
        f"Available collections: {available_ids}"
    )


def get_stac_client_from_collection(
    collection: str, config_filename="stac_collection.json"
):
    """
    Returns a STAC client for the given collection based on a JSON config file.

    Args:
        collection (str): Name or ID of the collection
        config_path (str): Path to the JSON config file

    Returns:
        STACClient instance

    Raises:
        ValueError if the collection is not supported
    """
    collection = collection.lower()
    collection_map = load_collection_config(config_filename)

    for prefix, endpoint in collection_map.items():
        if prefix in collection:
            client = _get_stac_client(endpoint)

            _validate_collection_exists(client, collection)
            return client

    raise ValueError(
        f"Collection '{collection}' not mapped to any STAC endpoint in config."
    )
