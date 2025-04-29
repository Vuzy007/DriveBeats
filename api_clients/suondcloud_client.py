import requests

SOUNDCLOUD_CLIENT_ID = "JtwkMxXKQNqDFvsQ3pUayFVgt4j9dS87"
BASE_URL = "https://api-v2.soundcloud.com"


def search_tracks(query: str, limit: int = 20):
    url = f"{BASE_URL}/search/tracks"
    params = {
        "q": query,
        "client_id": SOUNDCLOUD_CLIENT_ID,
        "limit": limit
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get("collection", [])
    except requests.RequestException as e:
        print(f"Ошибка при поиске треков: {e}")
        return []


def get_stream_url(transcoding_url: str):
    params = {"client_id": SOUNDCLOUD_CLIENT_ID}
    try:
        response = requests.get(transcoding_url, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("url")
    except requests.RequestException as e:
        print(f"Ошибка получения ссылки на стрим: {e}")
        return None
