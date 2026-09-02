import html
import math
import re
from urllib.parse import unquote


class InvalidLocationError(ValueError):
    pass


_COORDINATE_PATTERNS = (
    re.compile(
        r"!2d(?P<longitude>-?\d+(?:\.\d+)?)"
        r"!3d(?P<latitude>-?\d+(?:\.\d+)?)"
    ),
    re.compile(
        r"!3d(?P<latitude>-?\d+(?:\.\d+)?)"
        r"!4d(?P<longitude>-?\d+(?:\.\d+)?)"
    ),
)


def extract_coordinates(location: str) -> tuple[float, float]:
    """
    Extract (latitude, longitude) from a Google Maps iframe string.
    """

    if not location or not location.strip():
        raise InvalidLocationError(
            "Google Maps location is required."
        )

    normalized_location = unquote(
        html.unescape(location)
    )

    for pattern in _COORDINATE_PATTERNS:
        match = pattern.search(normalized_location)

        if match:
            latitude = float(match.group("latitude"))
            longitude = float(match.group("longitude"))

            if not -90 <= latitude <= 90:
                raise InvalidLocationError(
                    "Invalid latitude in Google Maps location."
                )

            if not -180 <= longitude <= 180:
                raise InvalidLocationError(
                    "Invalid longitude in Google Maps location."
                )

            return latitude, longitude

    raise InvalidLocationError(
        "Latitude and longitude were not found in the Google Maps location."
    )


def calculate_distance_km(
    origin_latitude: float,
    origin_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
) -> float:
    """
    Calculate straight-line distance between two coordinates.
    """

    earth_radius_km = 6371.0088

    latitude_difference = math.radians(
        destination_latitude - origin_latitude
    )

    longitude_difference = math.radians(
        destination_longitude - origin_longitude
    )

    origin_latitude_radians = math.radians(
        origin_latitude
    )

    destination_latitude_radians = math.radians(
        destination_latitude
    )

    haversine_value = (
        math.sin(latitude_difference / 2) ** 2
        + math.cos(origin_latitude_radians)
        * math.cos(destination_latitude_radians)
        * math.sin(longitude_difference / 2) ** 2
    )

    angular_distance = 2 * math.atan2(
        math.sqrt(haversine_value),
        math.sqrt(1 - haversine_value),
    )

    return round(
        earth_radius_km * angular_distance,
        2,
    )