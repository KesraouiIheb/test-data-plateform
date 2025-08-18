import os
import sys

from pystac_client import Client

from .base import BaseSTACClient

os.environ["AWS_NO_SIGN_REQUEST"] = "YES"


class Element84STACClient(BaseSTACClient):
    def __init__(self, url: str):
        self._client = Client.open(url)

    @property
    def client(self):
        return self._client
