import os
import requests
import sqlite3


class TrackDownloader:
    def __init__(self, db_manager, download_dir="downloads"):
        self.db_manager = db_manager
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)  # Создаём папку, если её нет

    def download_track(self, track_id, title, artist, download_url):
        """
        Скачивание трека и обновление информации в БД.
        """
        try:
            # Скачиваем файл
            response = requests.get(download_url, stream=True)
            response.raise_for_status()

            filename = f"{artist} - {title}.mp3".replace("/", "-")
            filepath = os.path.join(self.download_dir, filename)

            with open(filepath, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            # Обновляем статус трека в базе
            self.db_manager.update_track_status(track_id, "complete", filepath)
            print(f"Трек '{title}' успешно скачан в {filepath}")
        except Exception as e:
            error_message = str(e)
            self.db_manager.mark_error(track_id, error_message)
            print(f"Ошибка при скачивании трека {title}: {error_message}")

    def process_downloads(self):
        """
        Обработка треков в статусе 'pending' в фоновом режиме.
        """
        while True:
            conn = self.db_manager.get_new_connection()
            conn.row_factory = sqlite3.Row  # Позволяет обращаться к колонкам по имени
            cursor = conn.cursor()

            # Получаем список полей таблицы для проверки структуры
            cursor.execute("PRAGMA table_info(downloaded_tracks)")
            columns = cursor.fetchall()
            column_names = [column[1] for column in columns]

            # Определяем, какое имя колонки используется для URL
            url_column = "url" if "url" in column_names else "download_url"

            # Загружаем список ожидающих треков
            cursor.execute(f"SELECT * FROM downloaded_tracks WHERE status = 'pending' LIMIT 5")
            pending_tracks = cursor.fetchall()

            if not pending_tracks:
                print("Очередь пуста. Ждём новых треков...")
                break

            for track in pending_tracks:
                track_id = track["id"]
                title = track["track_title"]
                artist = track["artist"] or "Unknown Artist"
                url = track[url_column]

                print(f"Начинаем скачивание: {title}")

                # Устанавливаем статус "downloading"
                cursor.execute("UPDATE downloaded_tracks SET status = 'downloading' WHERE id = ?", (track_id,))
                conn.commit()

                # Скачиваем трек
                self.download_track(track_id, title, artist, url)

            conn.close()  # Закрываем соединение после обработки