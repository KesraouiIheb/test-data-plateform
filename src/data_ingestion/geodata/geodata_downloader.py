import logging
from pathlib import Path
from typing import Dict, List, Optional

from storage import get_storage

from metadata.manager import MetadataManager
from stac_clients import get_stac_client_from_collection
from download_utils import STACAssetDownloaderUtils

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class STACDownloaderService:
    def __init__(
        self,
        collection_name: str,
        output_dir: str,
        pgstac_dsn: str,
        storage_type: str = "local",
        catalog_metadata_path: str = "./metadata/catalog",
        
    ):
        self.collection_name = collection_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.storage = get_storage(storage_type)
        self.downloader_utils = STACAssetDownloaderUtils()
        self.manager = MetadataManager(catalog_path=catalog_metadata_path,pgstac_dsn = pgstac_dsn)
        self.stac_client = get_stac_client_from_collection(collection_name)

        self.manager.load_or_create_catalog()
        self.collection = self.manager.load_or_create_collection(collection_name)

    def download_assets(
        self,
        asset_keys: List[str],
        aoi: List[float],
        datetime_range: str,
        filters: Optional[Dict] = None,
        download_type: str = "all",
        max_items: int = 10,
        port_name: Optional[str] = None,
    ) -> None:
        """
        Download specified assets from STAC items matching the AOI and datetime range.

        Args:
            asset_keys: List of asset keys to download.
            aoi: Bounding box as [min_lon, min_lat, max_lon, max_lat].
            datetime_range: ISO8601 datetime or range (e.g., "2023-01-01/2023-02-01").
            filters: Additional query filters.
            download_type: Type of download ('all' for full download, 'bbox' for AOI cropping).
            max_items: Maximum number of items to process.
            port_name: Name of the port for filename purposes.

        Raises:
            ValueError: If no valid asset keys are found.
            RuntimeError: If no items are found.
        """
        try:
            items = self.stac_client.search(
                aoi=aoi,
                product=self.collection,
                datetime_range=datetime_range,
                filters=filters,
                max_items=max_items,
            )
        except Exception as e:
            logging.error(f"STAC search failed: {e}")
            raise RuntimeError("Failed to search STAC items.") from e

        if not items:
            raise RuntimeError("No items found for the given parameters.")

        available_assets = list(items[0].assets.keys())
        logging.info(f"Available assets in the collection: {available_assets}")

        if not asset_keys:
            raise ValueError("No asset keys provided for download.")

        if asset_keys == ["all"]:
            # TODO: Exclude non-image assets if needed
            asset_keys = available_assets
        elif not any(k in available_assets for k in asset_keys):
            raise ValueError(
                "None of the specified asset keys are present in the item."
            )

        logging.info(f"Found {len(items)} items. Downloading: {asset_keys}")

        for item in items:
            logging.info(f"Processing item: {item.id}")
            item_dir = Path(self.output_dir) / item.id
            item_dir.mkdir(exist_ok=True)

            for asset_key in asset_keys:
                try:
                    asset_url = self.downloader_utils.get_asset_url(item, asset_key)
                    band_basename = self.downloader_utils.get_filename_from_url(
                        asset_url
                    ).split(".")[0]
                    item_filename = (
                        f"{item.id}_{port_name}" if port_name else f"{item.id}"
                    )
                    item_filename_with_ext = f"{item_filename}_{band_basename}.tif"
                    filepath = item_dir / item_filename_with_ext

                    if filepath.exists():
                        logging.info(f"Skipping download: {filepath} already exists.")
                    else:
                        final_filepath = self.downloader_utils.download_single_asset(
                            asset_url,
                            str(filepath),
                            download_type=download_type,
                            aoi=aoi,
                        )
                        self.storage.save_file(str(final_filepath), str(final_filepath))

                    self.manager.load_or_create_item(
                        collection=self.collection,
                        item=item,
                        item_filename=item_filename,
                        aoi_geojson=item.geometry,
                        aoi=aoi,
                        new_band_key=asset_key,
                        new_band_path=str(final_filepath),
                        port_name=port_name
                    )

                except FileNotFoundError as e:
                    logging.error(
                        f"Local file system error for {asset_key} in {item.id}: {e}"
                    )
                except ConnectionError as e:
                    logging.error(
                        f"Network error downloading {asset_key} in {item.id}: {e}"
                    )
                except TimeoutError as e:
                    logging.error(f"Timeout downloading {asset_key} in {item.id}: {e}")
                except Exception as e:
                    logging.error(f"Unexpected error for {asset_key} in {item.id}: {e}")
