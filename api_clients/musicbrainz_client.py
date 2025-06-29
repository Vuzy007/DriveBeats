# coding: utf-8
"""MusicBrainz API client.

Provides simple wrappers around the MusicBrainz web service for searching
recordings. This module isolates all MusicBrainz related logic from the rest
of the application making it easy to replace or extend in the future.
"""

from typing import List, Dict
import requests

BASE_URL = "https://musicbrainz.org/ws/2"
HEADERS = {
    "User-Agent": "DriveBeats/0.1 ( https://example.com )"
}

def search_recordings(query: str, limit: int = 20) -> List[Dict]:
    """Search for recordings on MusicBrainz.

    Parameters
    ----------
    query : str
        Free text search query.
    limit : int, optional
        Maximum number of results to return, by default 20.

    Returns
    -------
    List[Dict]
        List of recording dictionaries or an empty list on error.
    """
    params = {
        "query": query,
        "fmt": "json",
        "limit": limit,
    }
    url = f"{BASE_URL}/recording"
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("recordings", [])
    except requests.RequestException as exc:
        print(f"MusicBrainz search error: {exc}")
        return []
