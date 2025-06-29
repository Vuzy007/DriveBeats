# coding: utf-8
"""Utility for applying ID3 tags to MP3 files.

This module uses the ``mutagen`` library to write ID3 tags for downloaded
tracks. It can optionally query MusicBrainz for additional metadata.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Optional

import requests
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TDRC, TCON
from mutagen.mp3 import MP3

from api_clients import musicbrainz_client

logger = logging.getLogger(__name__)


def fetch_metadata(title: str, artist: str) -> Dict[str, str]:
    """Retrieve metadata from MusicBrainz for given track.

    Parameters
    ----------
    title : str
        Track title.
    artist : str
        Artist name.

    Returns
    -------
    Dict[str, str]
        Metadata dictionary with possible keys ``album`` and ``year``.
    """
    query = f"{title} {artist}"
    logger.debug("Searching MusicBrainz for '%s'", query)
    results = musicbrainz_client.search_recordings(query, limit=1)
    if not results:
        return {}

    recording = results[0]
    meta: Dict[str, str] = {}

    releases = recording.get("releases")
    if releases:
        release = releases[0]
        meta["album"] = release.get("title", "")
        date = release.get("date")
        if date:
            meta["year"] = date.split("-")[0]
    return meta


def _download_cover(url: str) -> Optional[bytes]:
    """Download image data from ``url``."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.content
    except requests.RequestException as exc:
        logger.error("Failed to download cover art: %s", exc)
        return None


def apply_tags(filepath: str, tags: Dict[str, Optional[str]]) -> None:
    """Write ID3 tags to ``filepath``.

    Parameters
    ----------
    filepath : str
        Path to MP3 file.
    tags : Dict[str, Optional[str]]
        Tag values with keys: ``title``, ``artist``, ``album``, ``year``,
        ``genre``, ``cover_url``.
    """
    if not os.path.exists(filepath):
        logger.error("File does not exist: %s", filepath)
        return

    audio = MP3(filepath, ID3=ID3)
    if audio.tags is None:
        audio.add_tags()

    title = tags.get("title")
    artist = tags.get("artist")
    album = tags.get("album")
    year = tags.get("year")
    genre = tags.get("genre")
    cover_url = tags.get("cover_url")

    if title:
        audio.tags.add(TIT2(encoding=3, text=title))
    if artist:
        audio.tags.add(TPE1(encoding=3, text=artist))
    if album:
        audio.tags.add(TALB(encoding=3, text=album))
    if year:
        audio.tags.add(TDRC(encoding=3, text=str(year)))
    if genre:
        audio.tags.add(TCON(encoding=3, text=genre))

    if cover_url:
        data = _download_cover(cover_url)
        if data:
            audio.tags.add(
                APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,  # cover front
                    desc="Cover",
                    data=data,
                )
            )

    audio.save()
    logger.info("ID3 tags written for %s", os.path.basename(filepath))

