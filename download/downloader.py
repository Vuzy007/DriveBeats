import os
import requests
import sqlite3
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class TrackDownloader:
    def __init__(self, db_manager, download_dir="downloads"):
        self.db_manager = db_manager
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    def download_track(self, track_id, title, artist, download_url):
        try:
            response = requests.get(download_url, stream=True)
            response.raise_for_status()

            filename = f"{artist} - {title}.mp3".replace("/", "-")
            filepath = os.path.join(self.download_dir, filename)

            with open(filepath, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            self.db_manager.update_track_status(track_id, "complete", filepath)
            logging.info(f"Трек '{title}' успешно скачан в {filepath}")
        except Exception as e:
            error_message = str(e)
            self.db_manager.mark_error(track_id, error_message)
            logging.error(f"Ошибка при скачивании трека {title}: {error_message}")

    def _process_single_track(self, conn, cursor, track_dict, url_column):
        track_id = track_dict["id"]
        title = track_dict["track_title"]
        artist = track_dict["artist"] or "Unknown Artist"
        url = track_dict[url_column]

        logging.info(f"Начинаем скачивание: {title}")
        try:
            cursor.execute("UPDATE downloaded_tracks SET status = 'downloading' WHERE id = ?", (track_id,))
            conn.commit()
            self.download_track(track_id, title, artist, url)
        except Exception as e:
            logging.error(f"Ошибка при обновлении или загрузке трека {title}: {e}")

    def process_downloads(self):
        while True:
            conn = self.db_manager.get_new_connection()
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(downloaded_tracks)")
            columns = cursor.fetchall()
            column_names = [column[1] for column in columns]
            url_column = "url" if "url" in column_names else "download_url"

            has_row_factory = hasattr(conn, 'row_factory') and conn.row_factory == sqlite3.Row
            cursor.execute("SELECT * FROM downloaded_tracks WHERE status = 'pending' LIMIT 5")
            pending_tracks = cursor.fetchall()

            if not pending_tracks:
                logging.info("Очередь пуста. Ждём новых треков...")
                conn.close()
                time.sleep(5)
                continue

            for track in pending_tracks:
                if has_row_factory:
                    track_dict = track
                else:
                    track_dict = dict(zip(column_names, track))
                self._process_single_track(conn, cursor, track_dict, url_column)

            conn.close()
            time.sleep(2)
