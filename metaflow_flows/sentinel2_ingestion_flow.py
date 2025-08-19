import os
import sys
from pathlib import Path
import pandas as pd
from typing import List, Optional, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from metaflow import FlowSpec, Parameter,  step, kubernetes, conda_base
import json
from flows_utils import  search_items_and_compare_with_local_state

def chunk_list(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]




@conda_base(
    python='3.12.3',
    libraries={
        "boto3": "1.40.6",
        "planetary-computer": "1.0.0",
        "psycopg2-binary": "2.9.10",
        "pystac-client": "0.9.0",
        "rasterio": "1.4.3",
        "rio-cogeo": "5.4.2",
        "rio-tiler": "7.8.1",
        "pandas": "2.3",
    }
)
class Sentinel2IngestionFlow(FlowSpec):
    csv_path = Parameter(
        "csv_path",
        help="Path to CSV file containing PORT_NAME,minx,miny,maxx,maxy",
        default="./output_data/port_path/ports_aoi.csv",
    )

    batch_size = Parameter(
        "batch_size", help="Number of ports to process in each parallel task", default=1
    )

    collection_name = Parameter(
        "collection_name",
        help="STAC collection name to use for processing",
        default="sentinel-2-l2a",
    )

    asset_list = Parameter(
        "asset_list",
        help="Comma-separated list of asset keys to download, e.g. green,red,blue",
        default="green,red,blue",
        type=str,
    )

    metadata_path = Parameter(
        "metadata_path",    
        help="Path to metadata directory",
        default="./output_data/metadata",
        type=str,
    )

    local_path = Parameter(
        "local_storage_path",   
        help="Local storage path for downloaded assets",
        default="./output_data/raster",
        type=str,
    )


    @step
    def start(self):
        df = pd.read_csv(self.csv_path)[:2]
        ports = df.to_dict(orient="records")
        print(f"Loaded {len(ports)} ports from {self.csv_path}")
        
        self.port_batches = list(chunk_list(ports, int(self.batch_size)))
        print(
            f"Split into {len(self.port_batches)} batches of up to {self.batch_size} ports"
        )

        self.next(self.process_batch, foreach="port_batches")

    
    @step
    def process_batch(self):
        self.asset_list = [x.strip() for x in self.asset_list.split(",")]
        batch = self.input
        self.items = []  # Store items instead of download results

        for port in batch:
            port_name = port["PORT_NAME"]
            bbox = [port["minx"], port["miny"], port["maxx"], port["maxy"]]
            
            port_items = search_items_and_compare_with_local_state(

                asset_list=self.asset_list,
                collection_name=self.collection_name,
                metadata_path=self.metadata_path,

                port_name=port_name,
                bbox=bbox,
                datetime_range="2025-01-05T00:00:00Z/2025-08-05T00:00:00Z",
                filters=None,
                max_items=1,
            )
            self.items.extend(port_items)

        self.next(self.join_items)

    

    @step
    def join_items(self, inputs):
         
        self.all_items = [item for inp in inputs for item in inp.items]
        print(f"Total items to process: {len(self.all_items)}")
        self.next(self.split_for_download)

    @step
    def split_for_download(self):
        # If empty, add a dummy no-op element
        self.real_items = self.all_items if self.all_items else [None]
        self.empty_list = len(self.all_items) == 0
        self.next(self.download_assets, foreach="real_items")

    @step
    def download_assets(self):
        from flows_utils import download_items
        self.asset_list = [x.strip() for x in self.asset_list.split(",")]
        if self.input is None:
            # no-op task
            print("No items to process. Skipping download.")
            self.download_result = None
        else:
           
            self.download_result = download_items(

                asset_list= self.asset_list,
                collection_name=self.collection_name,
                metadata_path=self.metadata_path,
                local_storage_path=self.local_path,

                item=self.input["item"],
                port_name=self.input.get("port", None),
                bbox=self.input.get("bbox", None),
                download_type="bbox" 
            )
        self.next(self.download_join)

    @step
    def download_join(self, inputs):
        self.all_downloads = [inp.download_result for inp in inputs]
        self.next(self.write_to_db)

    @step
    def write_to_db(self):
        import os
        import psycopg2

        dsn = os.environ.get("INGEST_DB_DSN")
        if dsn is None:
            raise RuntimeError("INGEST_DB_DSN environment variable is required")

        with psycopg2.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS ingestion_log (item_id TEXT PRIMARY KEY, port TEXT)"
                )
                for rec in self.all_downloads:
                    if rec:
                        cur.execute(
                            "INSERT INTO ingestion_log (item_id, port) VALUES (%s, %s) ON CONFLICT (item_id) DO NOTHING",
                            (rec["item_id"], rec["port"]),
                        )
                cur.execute("SELECT COUNT(*) FROM ingestion_log")
                self.ingest_count = cur.fetchone()[0]

        pgstac_dsn = os.environ.get("PGSTAC_DSN")
        if pgstac_dsn:
            with psycopg2.connect(pgstac_dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT count(*) FROM pgstac.collections")
                    self.pgstac_collections = cur.fetchone()[0]

        self.next(self.end)

    
    @step
    def end(self):
        print("Flow completed.")
        if hasattr(self, "ingest_count"):
            print(f"Ingestion log rows: {self.ingest_count}")
        if hasattr(self, "pgstac_collections"):
            print(f"Collections in pgSTAC: {self.pgstac_collections}")


if __name__ == "__main__":
    Sentinel2IngestionFlow()
