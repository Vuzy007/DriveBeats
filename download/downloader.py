import os
import requests
import sqlite3
import time


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
            cursor = conn.cursor()

            # Получаем список полей таблицы для проверки структуры
            cursor.execute("PRAGMA table_info(downloaded_tracks)")
            columns = cursor.fetchall()

            # Проверяем, установлен ли row_factory
            has_row_factory = hasattr(conn, 'row_factory') and conn.row_factory == sqlite3.Row

            # Если row_factory не установлен, получаем имена колонок вручную
            if has_row_factory:
                column_names = [column[1] for column in columns]
            else:
                column_names = [column[1] for column in columns]

            # Определяем, какое имя колонки используется для URL
            url_column = "url" if "url" in column_names else "download_url"

            # Загружаем список ожидающих треков
            cursor.execute(f"SELECT * FROM downloaded_tracks WHERE status = 'pending' LIMIT 5")
            pending_tracks = cursor.fetchall()

            if not pending_tracks:
                print("Очередь пуста. Ждём новых треков...")
                time.sleep(5)  # Пауза перед повторной проверкой
                continue  # Продолжаем цикл вместо выхода

            for track in pending_tracks:
                # Получаем данные либо по индексу, либо по имени колонки
                if has_row_factory:
                    track_id = track["id"]
                    title = track["track_title"]
                    artist = track["artist"] or "Unknown Artist"
                    url = track[url_column]
                else:
                    # Получаем индексы колонок
                    id_index = column_names.index("id")
                    title_index = column_names.index("track_title")
                    artist_index = column_names.index("artist")
                    url_index = column_names.index(url_column)

                    track_id = track[id_index]
                    title = track[title_index]
                    artist = track[artist_index] or "Unknown Artist"
                    url = track[url_index]

                print(f"Начинаем скачивание: {title}")

                # Устанавливаем статус "downloading"
                cursor.execute("UPDATE downloaded_tracks SET status = 'downloading' WHERE id = ?", (track_id,))
                conn.commit()

                # Скачиваем трек
                self.download_track(track_id, title, artist, url)

            conn.close()  # Закрываем соединение после обработки
            time.sleep(2)  # Небольшая пауза между циклами обработки