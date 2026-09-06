# YouTube Connector - Hydra Module

## Installation

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

Set the required environment variable:

```bash
export YOUTUBE_API_KEY=AIzaSyC0cQ9ObtV5jMlb_1eN0EurSbnT3c7gD6I
```

## Usage

```python
from modules.youtube.connector import (
    youtube_client,
    get_video_details,
    search_videos,
    get_channel_details,
    get_playlist_items,
)

# Create YouTube client
youtube = youtube_client()

# Search videos
results = search_videos(youtube, "hydra", max_results=5)
for r in results:
    print(f"{r['title']} ({r['video_id']})")

# Get video details
video = get_video_details(youtube, "pdjzCWo-pTY")
if video:
    print(f"Title: {video['snippet']['title']}")
    print(f"Views: {video['statistics']['viewCount']}")

# Get channel details
channel = get_channel_details(youtube, "UCX6O7tGPR2eTDoS2UOq8b0g")
if channel:
    print(f"Channel: {channel['snippet']['title']}")
    print(f"Subscribers: {channel['statistics']['subscriberCount']}")

# Get playlist items
playlist = get_playlist_items(youtube, "PLwiy9D4sOs4ZI4JjQCAE1xq0u34JwgXbW", max_results=3)
for item in playlist:
    print(f"{item['title']} - {item['video_id']}")
```

## Available Methods

| Method | Description |
|--------|-------------|
| `youtube_client()` | Creates and returns a YouTube API client using the API Key |
| `search_videos(youtube, query, max_results)` | Searches for videos by query |
| `get_video_details(youtube, video_id)` | Gets metadata for a specific video |
| `get_channel_details(youtube, channel_id)` | Gets metadata for a specific channel |
| `get_playlist_items(youtube, playlist_id, max_results)` | Gets items from a playlist |

## Credentials

- **YOUTUBE_API_KEY**: API Key from Google Cloud Console (YouTube Data API v3)
- Requires YouTube Data API v3 to be enabled in your Google Cloud project
- API Key works for public data access (search, videos, channels)

## Tested

- Connection validated with successful search queries
- All methods return expected data structure
- API Key loaded from `~/.hydra/vault/youtube.env` via symlink `modulos/youtube/.env`