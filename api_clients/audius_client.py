"""Audius API client module.

This module wraps the public Audius API to provide
basic search and streaming URL retrieval functionality.
"""

from typing import List, Dict, Optional
import requests
import logging

BASE_URL = "https://discoveryprovider.audius.co/v1"
HEADERS = {"User-Agent": "DriveBeats/0.1"}
APP_NAME = "DriveBeats"

logger = logging.getLogger(__name__)


def _request(endpoint: str, params: Optional[dict] = None) -> dict:
    """Helper to perform GET requests to Audius.

    Returns an empty dict if request fails.
    """
    params = params or {}
    params.setdefault("app_name", APP_NAME)
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        logger.error("Audius request error: %s", exc)
        return {}


def search_tracks(query: str, limit: int = 20) -> List[Dict]:
    """Search for tracks on Audius by query string."""
    data = _request("/tracks/search", {"query": query, "limit": limit})
    return data.get("data", [])


def get_user(user_id: str) -> Optional[Dict]:
    """Retrieve user profile by ID."""
    data = _request(f"/users/{user_id}")
    return data.get("data")


def get_user_tracks(user_id: str, limit: int = 50) -> List[Dict]:
    """Retrieve tracks uploaded by a specific user."""
    data = _request(f"/users/{user_id}/tracks", {"limit": limit})
    return data.get("data", [])


def get_stream_url(track_id: str) -> Optional[str]:
    """Return direct streaming URL for a track."""
    url = f"{BASE_URL}/tracks/{track_id}/stream"
    try:
        response = requests.get(
            url,
            params={"app_name": APP_NAME},
            headers=HEADERS,
            allow_redirects=False,
            timeout=10,
        )
        if response.is_redirect:
            return response.headers.get("Location")
        # Some nodes may return JSON with `data` field
        if response.headers.get("Content-Type", "").startswith("application/json"):
            return response.json().get("data")
        return None
    except requests.RequestException as exc:
        logger.error("Failed to get stream url: %s", exc)
        return None

