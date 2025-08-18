import planetary_computer
from pystac_client import Client

from .base import BaseSTACClient


class PlanetarySTACClient(BaseSTACClient):
    def __init__(self, url: str):
        self._client = Client.open(url, modifier=planetary_computer.sign_inplace)

    @property
    def client(self):
        return self._client
