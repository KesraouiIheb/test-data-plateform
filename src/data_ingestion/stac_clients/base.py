from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseSTACClient(ABC):
    @property
    @abstractmethod
    def client(self):
        """Subclasses must implement this property to return a STAC client instance."""
        pass

    def create_aoi_geojson_from_aoi(self, aoi: List[float]) -> Dict[str, Any]:
        """
        Create a GeoJSON Polygon from a bounding box (AOI).

        Args:
            aoi (List[float]): Bounding box as [min_lon, min_lat, max_lon, max_lat].

        Returns:
            Dict[str, Any]: GeoJSON representation of the AOI.
        """
        if len(aoi) != 4:
            raise ValueError(
                "AOI must be a list of four floats: [min_lon, min_lat, max_lon, max_lat]"
            )

        self.aoi_geojson = {
            "type": "Polygon",
            "coordinates": [
                [
                    [aoi[0], aoi[1]],
                    [aoi[2], aoi[1]],
                    [aoi[2], aoi[3]],
                    [aoi[0], aoi[3]],
                    [aoi[0], aoi[1]],
                ]
            ],
        }
        return self.aoi_geojson

    def search(self, aoi, product, datetime_range, filters, max_items):
        """
        Search the STAC API for items intersecting the specified AOI,
        filtered by product, datetime range, and query filters.

        Args:
            aoi (List[float]): Bounding box as [min_lon, min_lat, max_lon, max_lat].
            product (str): Collection or product name.
            datetime_range (str): ISO8601 datetime or range (e.g., "2023-01-01/2023-02-01").
            filters (Dict[str, Any]): Additional query filters.

        Returns:
            List[Any]: List of matching STAC Items (up to max_items=1).
        """
        if aoi:
            self.aoi_geojson = self.create_aoi_geojson_from_aoi(aoi)

        return list(
            self.client.search(
                collections=[product],
                datetime=datetime_range,
                # intersects=self.aoi_geojson,
                bbox=aoi,
                query=filters,
                max_items=max_items,
            ).get_items()
        )

    def get_available_collections(self) -> List[str]:
        try:
            return [collection.id for collection in self.client.get_collections()]
        except Exception as e:
            raise RuntimeError(f"Failed to fetch collections: {e}")
