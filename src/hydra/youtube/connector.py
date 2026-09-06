# -------------------------------------------------------------------------
# YouTube connector – Hydra Google integration.
# Retrieves the API Key from HYDRA Vault and provides a thin wrapper
# around the YouTube Data API v3 for consuming public video/channel data.
# -------------------------------------------------------------------------
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import googleapiclient.discovery
from googleapiclient.errors import HttpError

from hydra.vault import get_vault

# -------------------------------------------------------------------------
# YouTubeService – wrapper ligero con la API key.
# -------------------------------------------------------------------------
class YouTubeService:
    """Wrapper around the YouTube Data API v3 using an API Key."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = googleapiclient.discovery.build(
            "youtube", "v3", developerKey=api_key
        )

    def search_videos(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for videos by query string."""
        try:
            request = self._client.search().list(
                part="snippet",
                q=query,
                type="video",
                maxResults=max_results,
            )
            response = request.execute()
            videos = []
            for item in response.get("items", []):
                videos.append(
                    {
                        "video_id": item["id"]["videoId"],
                        "title": item["snippet"]["title"],
                        "channel_title": item["snippet"]["channelTitle"],
                        "published_at": item["snippet"].get("publishedAt"),
                    }
                )
            return videos
        except HttpError as exc:
            print(f"YouTube search error: {exc}")
            return []

    def get_video_details(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed metadata for a specific video."""
        try:
            request = self._client.videos().list(
                part="snippet,contentDetails,statistics",
                id=video_id,
            )
            response = request.execute()
            if response.get("items"):
                return response["items"][0]
            return None
        except HttpError as exc:
            print(f"YouTube video details error: {exc}")
            return None

    def get_channel_details(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed metadata for a specific channel."""
        try:
            request = self._client.channels().list(
                part="snippet,statistics,contentDetails",
                id=channel_id,
            )
            response = request.execute()
            if response.get("items"):
                return response["items"][0]
            return None
        except HttpError as exc:
            print(f"YouTube channel details error: {exc}")
            return None

    def get_playlist_items(self, playlist_id: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Get items from a playlist."""
        try:
            request = self._client.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=playlist_id,
                maxResults=max_results,
            )
            response = request.execute()
            items = []
            for item in response.get("items", []):
                items.append(
                    {
                        "video_id": item["contentDetails"]["videoId"],
                        "title": item["snippet"]["title"],
                        "published_at": item["snippet"].get("publishedAt"),
                    }
                )
            return items
        except HttpError as exc:
            print(f"YouTube playlist items error: {exc}")
            return []


# -------------------------------------------------------------------------
# YouTubeConnector – main class that the rest of HYDRA will use.
# -------------------------------------------------------------------------
class YouTubeConnector:
    """YouTube connector powered by the HYDRA Vault.

    Responsibilities
    ----------------
    * Retrieve the YouTube API Key from the Vault under the key
      ``youtube/api_key``.
    * Provide high-level methods for the most common YouTube Data API operations.
    * Validate connectivity via a lightweight API call.
    """

    def __init__(self, *,
                 vault: Any | None = None,
                 ):
        self._vault = vault or get_vault()
        self._service: Optional[YouTubeService] = None
        self._last_health_check: Optional[float] = None

    def _ensure_service(self) -> YouTubeService:
        """Ensure we have a valid service instance; load API key from Vault if needed."""
        if self._service is None:
            api_key = self._vault.get_secret("youtube/api_key")
            if not api_key:
                raise ValueError(
                    "YouTube API Key not found in Vault under key 'youtube/api_key'. "
                    "Set it via: vault.set_secret('youtube/api_key', 'YOUR_API_KEY')"
                )
            self._service = YouTubeService(api_key=api_key)
        return self._service

    def health_check(self) -> Dict[str, Any]:
        """Verify that the connector is ready to use YouTube."""
        result: Dict[str, Any] = {"valid": False, "message": ""}
        try:
            service = self._ensure_service()
            # Perform a tiny API call to confirm connectivity (search for 'genesis').
            search = service.search_videos(query="genesis", max_results=1)
            result["valid"] = True
            result["message"] = f"YouTube connector is healthy. API Key loaded from Vault."
            self._service = service
            self._last_health_check = time.time()
        except ValueError as exc:
            result["message"] = f"Configuration error: {exc}"
        except HttpError as exc:
            result["message"] = f"YouTube API error during health check: {exc}"
        except Exception as exc:
            result["message"] = f"Connection problem during health check: {exc}"
        return result

    def search_videos(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for videos by query string."""
        service = self._ensure_service()
        return service.search_videos(query=query, max_results=max_results)

    def get_video_details(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed metadata for a specific video."""
        service = self._ensure_service()
        return service.get_video_details(video_id=video_id)

    def get_channel_details(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed metadata for a specific channel."""
        service = self._ensure_service()
        return service.get_channel_details(channel_id=channel_id)

    def get_playlist_items(self, playlist_id: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Get items from a playlist."""
        service = self._ensure_service()
        return service.get_playlist_items(playlist_id=playlist_id, max_results=max_results)


# -------------------------------------------------------------------------
# Module-level convenience function.
# -------------------------------------------------------------------------
def health_check() -> Dict[str, Any]:
    """Return the health status of the YouTube connector."""
    from hydra.youtube.connector import YouTubeConnector
    conn = YouTubeConnector()
    return conn.health_check()
