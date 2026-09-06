import os
from googleapiclient.discovery import build

API_SERVICE_NAME = "youtube"
API_VERSION = "v3"


def get_youtube_api_key():
    return os.environ.get("YOUTUBE_API_KEY")


def youtube_client():
    api_key = get_youtube_api_key()
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY environment variable not set")
    return build(API_SERVICE_NAME, API_VERSION, developerKey=api_key)


def get_video_details(youtube, video_id):
    request = youtube.videos().list(
        part="snippet,contentDetails,statistics",
        id=video_id
    )
    response = request.execute()
    if response.get("items"):
        return response["items"][0]
    return None


def search_videos(youtube, query, max_results=5):
    request = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=max_results
    )
    response = request.execute()
    videos = []
    for item in response.get("items", []):
        videos.append({
            "video_id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "channel_title": item["snippet"]["channelTitle"],
            "published_at": item["snippet"]["publishedAt"],
        })
    return videos


def get_channel_details(youtube, channel_id):
    request = youtube.channels().list(
        part="snippet,statistics,contentDetails",
        id=channel_id
    )
    response = request.execute()
    if response.get("items"):
        return response["items"][0]
    return None


def get_playlist_items(youtube, playlist_id, max_results=5):
    request = youtube.playlistItems().list(
        part="snippet,contentDetails",
        playlistId=playlist_id,
        maxResults=max_results
    )
    response = request.execute()
    items = []
    for item in response.get("items", []):
        items.append({
            "video_id": item["contentDetails"]["videoId"],
            "title": item["snippet"]["title"],
            "published_at": item["snippet"]["publishedAt"],
        })
    return items