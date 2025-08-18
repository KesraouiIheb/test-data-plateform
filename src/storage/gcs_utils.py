import os
from urllib.parse import urlparse

from google.cloud import storage



class GCSStorage:
    def __init__(self):
        key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if not key_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS env var not set")
        self.client = storage.Client.from_service_account_json(key_path)

    def save_file(self, local_path: str, gcs_url: str) -> str:
        parsed = urlparse(gcs_url)
        bucket = self.client.bucket(parsed.netloc)
        blob = bucket.blob(parsed.path.lstrip("/"))
        blob.upload_from_filename(local_path)
        print(f"Uploaded to GCS: {gcs_url}")
        try:
            os.remove(local_path)
            print(f"Local file '{local_path}' deleted after upload.")
        except OSError as e:
            print(f"Warning: Failed to delete local file '{local_path}': {e}")
        return gcs_url
