import os
from datetime import datetime
import json
import shutil
import pystac
import subprocess
from pathlib import Path


class PgStacLoader:
    def __init__(self, dsn):
        self.dsn = dsn

    def load_collection(self, collection_path):
        subprocess.run([
            "pypgstac", "load", "collections", collection_path,
            "--dsn", self.dsn, "--method" ,"insert_ignore",
        ], check=True)
       
    def load_item(self, item_path):
        subprocess.run([
            "pypgstac", "load","items", item_path,
            "--dsn", self.dsn, "--method" ,"insert_ignore",
        ], check=True)
        


    


class MetadataManager:
    def __init__(self, catalog_path: str, pgstac_dsn: str):
        """
        Initialize the metadata manager with the path to the STAC catalog.
        """
        self.catalog_path = catalog_path
        self.catalog = None

        self.pypgstac_client = PgStacLoader(pgstac_dsn) if pgstac_dsn else None
            

    def _get_catalog_path(self) -> str:
        return os.path.join(self.catalog_path, "catalog.json")

    def _get_collection_dir(self, collection_id: str) -> str:
        return os.path.join(self.catalog_path, "collections", collection_id)

    def _get_collection_path(self, collection_id: str) -> str:
        return os.path.join(
            self._get_collection_dir(collection_id), "collection.json"
        )

    def _get_item_dir(self, collection_id: str, item_id: str) -> str:
        return os.path.join(self._get_collection_dir(collection_id), item_id)

    def _get_item_path(self, collection_id: str, item_id: str) -> str:
        return os.path.join(
            self._get_item_dir(collection_id, item_id), f"{item_id}.json"
        )

    def load_or_create_catalog(self) -> pystac.Catalog:
        """
        Loads an existing STAC catalog or creates a new one.
        """
        catalog_path = self._get_catalog_path()

        if os.path.exists(catalog_path):
            self.catalog = pystac.Catalog.from_file(catalog_path)
            print("Catalog loaded from disk.")
        else:
            os.makedirs(self.catalog_path, exist_ok=True)
            self.catalog = pystac.Catalog(
                id="ubotica-catalog",
                description="STAC Catalog for Ubotica Technologies Data Platform Project",
                title="Ubotica Technologies - Data Platform STAC Catalog",
                extra_fields={
                    "company": "Ubotica Technologies",
                    "project": "Data Platform",
                },
                catalog_type=pystac.CatalogType.SELF_CONTAINED,
            )
            self.catalog.normalize_hrefs(self.catalog_path)
            self.catalog.save(dest_href=self.catalog_path)
            print("New catalog created and saved.")

        return self.catalog

    def load_or_create_collection(self, collection_id: str) -> pystac.Collection:
        """
        Loads an existing STAC collection or creates a new one.
        """
        collection_dir = self._get_collection_dir(collection_id)
        collection_path = self._get_collection_path(collection_id)
        os.makedirs(collection_dir, exist_ok=True)

        if os.path.exists(collection_path):
            collection = pystac.Collection.from_file(collection_path)
            print(f"Collection '{collection_id}' loaded from disk.")
        else:
            collection = pystac.Collection(
                id=collection_id,
                description=f"Collection {collection_id} for Ubotica Data Platform",
                extent=pystac.Extent(
                    spatial=pystac.SpatialExtent([[-180.0, -90.0, 180.0, 90.0]]),
                    temporal=pystac.TemporalExtent([[None, None]]),
                ),
                title=f"Ubotica Collection {collection_id}",
                license="proprietary",
                extra_fields={"company": "Ubotica Technologies"},
                catalog_type=pystac.CatalogType.SELF_CONTAINED,
            )
            collection.normalize_hrefs(collection_path)
            collection.save(dest_href=collection_dir)

        if self.pypgstac_client:
            self.pypgstac_client.load_collection(collection_path)
        

        return collection

    def load_or_create_item(
        self,
        collection: pystac.Collection,
        item: pystac.Item,
        item_filename: str,
        aoi_geojson: dict,
        aoi: list,
        new_band_key: str,
        new_band_path: str,
        port_name: str,
    ) -> pystac.Item:
        """
        Loads or creates a STAC item and adds a new band asset to it incrementally.

        Args:
            collection: The STAC collection the item belongs to.
            item: A pystac.Item instance with id, datetime, and properties.
            aoi_geojson: Geometry in GeoJSON format.
            aoi: Bounding box list [minLon, minLat, maxLon, maxLat].
            new_band_key: Asset key (e.g., "red", "green").
            new_band_path: Path to the band GeoTIFF.

        Returns:
            The updated STAC item.
        """
        item_dir = self._get_item_dir(collection.id, item_filename)
        item_path = self._get_item_path(collection.id, item_filename)
        os.makedirs(item_dir, exist_ok=True)

        if os.path.exists(item_path):
            item = pystac.Item.from_file(item_path)  ## TODO: check from the pgstac database of the item.id + region name => could "goulette" and "tunis" ports have the same item id, but different region names
            print(f"Item '{item_filename}' loaded from disk.")
        else:
      
            item = pystac.Item(
                id=item.id,
                geometry=aoi_geojson,
                bbox=aoi,
                datetime=item.datetime or datetime.utcnow(),
                properties=item.properties,
                collection=collection.id,
            )
            item.properties['port_name'] = port_name
            print(f"New item '{item.id}' created.")

        if new_band_key not in item.assets:
            item.add_asset(
                new_band_key,
                pystac.Asset(
                    href=new_band_path,
                    media_type="image/tiff; application=geotiff",
                    roles=["data"],
                    title=f"{new_band_key.capitalize()} Band",
                ),
            )
            print(f"Band '{new_band_key}' added.")
        else:
            print(f"Band '{new_band_key}' already exists, skipping.")

        item.save_object(dest_href=str(item_path))

        
        if self.pypgstac_client:
            self.pypgstac_client.load_item(str(item_path))

        # try:
        #     Path(item_path).unlink() ## TODO :  removing the json files from the disk is crucial, we need to make sure it's an atomic process
        #     print(f"Temporary item file '{item_filename}' removed.")
        # except Exception as e:
        #     print(f"Warning: Could not remove temporary file '{item_filename}': {e}")
        
        return item
