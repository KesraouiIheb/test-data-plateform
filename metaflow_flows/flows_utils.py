from pathlib import Path
import pandas as pd
from typing import List, Optional, Dict
import json 
from src.data_ingestion.stac_clients import get_stac_client_from_collection
from src.data_ingestion.geodata import download_utils
from src.data_ingestion.metadata.manager import MetadataManager

def get_item_by_id(collection_path: Path, item_id: str) -> Optional[dict]:
    """
    Check if a STAC item with the given ID exists in the collection.
    If found, returns the item as a dict; otherwise returns None.
    """
    for item_file in collection_path.glob("*.json"):
        try:
            with open(item_file, "r") as f:
                item = json.load(f)
                if item.get("id") == item_id:
                    return item
        except Exception as e:
            print(f"Error reading {item_file}: {e}")
            continue
    return None

def search_items_and_compare_with_local_state(
    asset_list: List[str],
    collection_name: str,
    metadata_path: str,
    port_name: str,
    bbox: list,
    datetime_range: str = "2025-01-05T00:00:00Z/2025-08-05T00:00:00Z",
    filters: Optional[dict] = None,
    max_items: int = 1
) -> List[Dict]:
    stac_client = get_stac_client_from_collection(collection_name)
    items = stac_client.search(
        aoi=bbox,
        product=collection_name,
        datetime_range=datetime_range,
        filters=filters,
        max_items=max_items,
    )

    metadata_dir = Path(metadata_path) / collection_name
    results = []

    for item in items:
        item_filename = f"{item.id}_{port_name.replace('/', '_').replace('\\', '_').replace(' ', '_')}"
        item_path = metadata_dir / item_filename

        existing_item = get_item_by_id(item_path, item.id)

        if existing_item:
            existing_assets = existing_item.get("assets", {}).keys()
            needed_assets = set(asset_list)
            if needed_assets.issubset(existing_assets):
                print(f"Skipping item {item.id} for port {port_name} — all assets already present.")
                continue
            else:
                print(f"Item {item.id} for port {port_name} exists, but some assets are missing.")
        else:
            print(f"Item {item.id} for port {port_name} is new.")

        results.append({"port": port_name, "item": item, "bbox": bbox})

    return results


def download_items(
    asset_list: List[str],
    collection_name: str,
    metadata_path: str,
    local_storage_path: str,
    item,
    port_name: str,
    bbox,
    download_type: str = "bbox"
) -> Dict:
    downloader_utils = download_utils.STACAssetDownloaderUtils()
    manager = MetadataManager(catalog_path=metadata_path,pgstac_dsn=None)
    collection = manager.load_or_create_collection(collection_name)
    local_storage = Path(local_storage_path)

    item_filename_base = f"{item.id}_{port_name.replace('/', '_').replace('\\', '_').replace(' ', '_')}" if port_name else f"{item.id}"
    downloaded_assets = []

    for asset_key in asset_list:
        try:
            asset_url = downloader_utils.get_asset_url(item, asset_key)
            band_basename = downloader_utils.get_filename_from_url(asset_url).split(".")[0]
            item_filename_with_ext = f"{item_filename_base}_{band_basename}.tif"
            filepath = local_storage / item_filename_with_ext

            downloader_utils.download_single_asset(
                url=asset_url,
                local_path=str(filepath),
                download_type=download_type,
                aoi=bbox
            )

            manager.load_or_create_item(
                collection=collection,
                item=item,
                item_filename=item_filename_base,
                aoi_geojson=item.geometry,
                aoi=bbox,
                new_band_key=asset_key,
                new_band_path=str(filepath),
                port_name=port_name,
            )

            downloaded_assets.append({
                "asset": asset_key,
                "filepath": str(filepath)
            })

            print(f"Prepared {item_filename_with_ext} for port {port_name}, asset: {asset_key}")
        except Exception as e:
            print(f"Failed to process asset '{asset_key}' for item {item.id}: {e}")

    return {
        "port": port_name,
        "item_id": item.id,
        "downloaded_assets": downloaded_assets
    }
