from bs4 import BeautifulSoup
import requests
from urllib.parse import quote_plus
from database import db_manager


class Z3fmParser:
    BASE_SEARCH_URL = "https://z3.fm/mp3/search?keywords="
    BASE_DOWNLOAD_URL = "https://z3.fm"

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def fetch_and_update_download_links(parser, db_manager):
        """
        Получает очередь треков и обновляет их download_url на основе парсинга z3.fm.
        """
        try:
            conn = db_manager.get_new_connection()
            cursor = conn.cursor()

            # Получаем треки со статусом pending и пустым download_url
            cursor.execute(
                "SELECT id, track_title FROM downloaded_tracks WHERE status = 'pending' AND (download_url IS NULL OR download_url = '')"
            )
            tracks = cursor.fetchall()

            for track in tracks:
                track_id, track_title = track
                print(f"Поиск ссылки для трека: {track_title}")
                url = parser.fetch_download_link(track_title)

                if url:
                    db_manager.update_download_url(track_id, url)
                else:
                    print(f"Ссылка не найдена для трека: {track_title}")

            conn.close()
        except Exception as e:
            print(f"Ошибка при обновлении ссылок: {e}")
