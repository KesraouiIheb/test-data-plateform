import logging
import os
import subprocess
from typing import List, Optional
from urllib.parse import unquote, urlparse

import boto3
import rasterio
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from rasterio.transform import from_bounds
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles
from rio_tiler.io import COGReader


class STACAssetDownloaderUtils:
    def __init__(self):
        """
        storage: instance of BaseStorage subclass to save files
        """

        pass

    def _get_s3_client(self):
        return boto3.client("s3", config=Config(signature_version=UNSIGNED))

    def get_asset_url(self, item, asset_key: str) -> Optional[str]:
        """
        Extracts the asset URL from a STAC Item's assets.
        Args:
            item: STAC Item object containing assets.
            asset_key (str): Key of the asset to retrieve.
        Returns:
            str: URL of the asset if found, else None.
        """

        asset = item.assets.get(asset_key)
        if not asset:
            logging.error(f"Asset '{asset_key}' not found in item {item.id}")
            return None

        href = asset.href

        if href and href.startswith("http"):
            return href

        # Check alternate URLs for HTTP
        alternates = asset.extra_fields.get("alternate", {})
        aws_http = alternates.get("aws_http", {}).get("href")
        if aws_http and aws_http.startswith("http"):
            return aws_http

        if href and href.startswith("s3://"):
            return href

        logging.warning(f"No valid URL found for asset '{asset_key}' in item {item.id}")
        return None

    def download_single_asset(
        self, url: str, local_path: str, download_type: str, aoi: List[float]
    ) -> None:
        """
        Download a single asset from a URL to a local path, with optional AOI cropping.
        Args:
            url (str): URL of the asset to download.
            local_path (str): Local file path to save the downloaded asset.
            download_type (str): Type of download ('all' for full download, 'bbox' for AOI cropping).
            aoi (List[float]): Bounding box as [min_lon, min_lat, max_lon, max_lat] for cropping.
        Raises:
            RuntimeError: If the download fails or the URL scheme is unsupported.
        Returns:
            None

        """
        if download_type == "all":
            if url.startswith("http"):
                self._download_http(url, local_path)
                print(f"Done - Downloaded via HTTP: {local_path}")
            elif url.startswith("s3://"):
                self._download_from_s3(url, local_path)
                print(f"Done - Downloaded via S3: {local_path}")
            else:
                print(f"Unsupported URL scheme for download: {url}")
                return None
        elif download_type == "bbox" and (
            "tif" in url or "TIF" in url or "tiff" in url or "jp2" in url
        ):
            self._tile_cog(url, local_path, aoi)
        else:
            print(f"Unsupported URL scheme for download: {url}")
            self._download_http(url, local_path)

        cog_filepath = local_path.replace(".tif", "_cog.tif").replace(
            ".TIF", "_cog.tif"
        )
        try:
            self._convert_to_cog(local_path, cog_filepath)
            print(f"COG saved to {cog_filepath}")
            try:
                os.remove(local_path)
            except OSError as e:
                logging.warning(f"Failed to remove {local_path}: {e}")
        except Exception as e:
            print(f"Failed to convert to COG: {e}")
            return local_path  # fallback to non-COG file path

        return cog_filepath

    def _download_http(self, url: str, local_path: str):
        """
        Download a file from the given HTTP URL to the specified local path using curl.

        Args:
            url (str): The HTTP URL of the file to download.
            local_path (str): The local filesystem path where the file will be saved.

        Raises:
            subprocess.CalledProcessError: If the curl command fails.
            OSError: If directory creation fails.

        """
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        try:
            subprocess.run(
                [
                    "curl",
                    "--fail",
                    "--location",
                    "--max-time",
                    "3600",
                    "-o",
                    local_path,
                    url,
                ],
                check=True,
            )
            print(f"Downloaded via HTTP: {local_path}")

        except subprocess.CalledProcessError as e:
            logging.error(
                f"Failed to download {url} to {local_path}: {e.stderr.decode().strip()}"
            )
            raise
        except OSError as e:
            logging.error(f"Failed to create directory for {local_path}: {e}")
            raise

    def _download_from_s3(self, s3_url: str, local_path: str) -> None:
        """Download a file from S3 to a local path."""
        self.s3_client = self._get_s3_client()
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            bucket, *key_parts = s3_url.replace("s3://", "").split("/")
            key = "/".join(key_parts)
            self.s3_client.download_file(bucket, key, local_path)
            print(f"Downloaded via S3: {local_path}")
        except NoCredentialsError:
            print("AWS credentials not found.")
            raise
        except PartialCredentialsError:
            print("AWS credentials are incomplete.")
            raise

    def get_filename_from_url(self, url: str) -> str:
        """Extracts the filename from a URL, handling both HTTP and S3 URLs."""
        parsed_url = urlparse(url)
        return unquote(parsed_url.path.split("/")[-1])

    def _tile_cog(self, url: str, local_path: str, aoi: List[float]) -> None:
        """
        Crop a COG file to the AOI bounding box and save as a new GeoTIFF.
        """
        print(f"Creating bbox GeoTIFF from COG: {url} to {local_path}")
        try:
            with COGReader(url) as cog:
                img = cog.part(aoi)

                if img.data is None or img.data.size == 0:
                    print(f" No data extracted from bbox: {local_path}")
                    return

                data = img.data
                bounds = img.bounds
                crs = img.crs

                transform = from_bounds(
                    *bounds, width=data.shape[2], height=data.shape[1]
                )
                print("done")
                with rasterio.open(
                    local_path,
                    "w",
                    driver="GTiff",
                    height=data.shape[1],
                    width=data.shape[2],
                    count=data.shape[0],
                    dtype=data.dtype,
                    crs=crs,
                    transform=transform,
                ) as dst:
                    dst.write(data)
                print(f"Saved bbox data to {local_path}")
        except Exception as e:
            print(f"Failed to create bbox GeoTIFF: {e}")

    def _convert_to_cog(self, input_path: str, output_path: str) -> None:
        """
        Convert a GeoTIFF to a Cloud-Optimized GeoTIFF (COG) using deflate compression.

        Parameters:
            input_path (str): Path to the input GeoTIFF file.
            output_path (str): Path to the output COG file.
        """
        try:
            profile = cog_profiles.get("deflate")
            with rasterio.open(input_path) as src:
                cog_translate(src, output_path, profile, in_memory=True)
            print(f"Successfully converted {input_path} to COG: {output_path}")
        except Exception as e:
            print(f"Error converting {input_path} to COG: {e}")
