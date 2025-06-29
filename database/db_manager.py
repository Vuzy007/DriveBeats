import sqlite3

class DatabaseManager:
    def __init__(self, db_name="database/music_library.db"):
        self.connection = sqlite3.connect(db_name)
        self.connection.row_factory = sqlite3.Row # Позволяет обращаться к полям по имени
        print(f"Подключение к базе данных: {db_name}")

    def get_pending_tracks(self):
        """
        Получить треки со статусом 'pending' для скачивания.
        """
        query = "SELECT * FROM downloaded_tracks WHERE status = 'pending'"
        return self.connection.execute(query).fetchall()

    def update_track_status(self, track_id, status, filepath=None):
        """
        Обновить статус трека и путь к файлу (если скачивается).
        """
        query = "UPDATE downloaded_tracks SET status = ?, file_path = ? WHERE id = ?"
        self.connection.execute(query, (status, filepath, track_id))
        self.connection.commit()
        print(f"Обновлён статус трека ID {track_id}: {status}")

    def mark_error(self, track_id, error_message):
        """
        Устанавливает статус ошибки для трека.
        """
        query = "UPDATE downloaded_tracks SET status = 'error', error_message = error_message WHERE id = track_id"
        self.connection.execute(query)  # Порядок соответствует SQL-запросу
        self.connection.commit()
        print(f"Ошибка для трека ID {track_id}: {error_message}")

    def add_track(self, title, artist, download_url, track_id=None):
        """
        Добавляет трек в очередь на скачивание или обновляет существующий
        если файл был удален

        Параметры:
        - title: название трека
        - artist: исполнитель
        - download_url: URL для скачивания
        - track_id: уникальный ID трека из API (если доступен)

        Возвращает:
        - (успех, статус): bool, str
        """
        import datetime
        import os
        current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Проверим наличие нужных полей в таблице
        cursor = self.connection.cursor()
        cursor.execute("PRAGMA table_info(downloaded_tracks)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]

        # Добавляем нужные колонки, если их нет
        for column, column_type in [("url", "TEXT"), ("track_id", "TEXT")]:
            if column not in column_names:
                try:
                    cursor.execute(f"ALTER TABLE downloaded_tracks ADD COLUMN {column} {column_type}")
                    self.connection.commit()
                    print(f"Добавлена колонка {column} в таблицу downloaded_tracks")
                except Exception as e:
                    print(f"Ошибка добавления колонки {column}: {e}")

        # Определяем, какое имя колонки использовать для URL
        url_column = "url" if "url" in column_names else "download_url"

        # Сначала проверяем по track_id (если он есть)
        if track_id:
            cursor.execute(f"SELECT id, file_path, status FROM downloaded_tracks WHERE track_id = ?", (track_id,))
            existing = cursor.fetchone()
            if existing:
                db_id, file_path, status = existing

                # Проверяем, существует ли файл физически
                file_exists = file_path and os.path.exists(file_path)

                if not file_exists and status != "pending":
                    # Файл удален или путь неверный - обновляем статус
                    self.connection.execute(
                        f"UPDATE downloaded_tracks SET status = 'pending', {url_column} = ?, download_date = ? WHERE id = ?",
                        (download_url, current_date, db_id)
                    )
                    self.connection.commit()
                    print(f"Трек '{title}' переведен в статус 'pending' для повторной загрузки")
                    return True, "requeued"
                else:
                    print(f"Трек '{title}' уже существует в базе (ID: {db_id})")
                    return False, "duplicate"

        # Проверка по URL и названию (если track_id не предоставлен или не найден)
        if download_url:
            cursor.execute(
                f"SELECT id, file_path, status FROM downloaded_tracks WHERE {url_column} = ? OR (track_title = ? AND artist = ?)",
                (download_url, title, artist),
            )
        else:
            cursor.execute(
                "SELECT id, file_path, status FROM downloaded_tracks WHERE track_title = ? AND artist = ?",
                (title, artist),
            )
        existing = cursor.fetchone()

        if existing:
            db_id, file_path, status = existing

            # Проверяем, существует ли файл физически
            file_exists = file_path and os.path.exists(file_path)

            if not file_exists and status != "pending":
                # Файл удален или путь неверный - обновляем статус
                self.connection.execute(
                    f"UPDATE downloaded_tracks SET status = 'pending', {url_column} = ?, download_date = ? WHERE id = ?",
                    (download_url, current_date, db_id)
                )
                self.connection.commit()
                print(f"Трек '{title}' переведен в статус 'pending' для повторной загрузки")
                return True, "requeued"
            else:
                print(f"Трек '{title}' уже существует в базе (ID: {db_id})")
                return False, "duplicate"

        # Если трек не найден в базе, добавляем новый
        query = f"""
        INSERT INTO downloaded_tracks 
        (track_title, artist, {url_column}, status, download_date, file_path, track_id) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        try:
            self.connection.execute(query, (
                title,
                artist,
                download_url,
                "pending",
                current_date,
                "",  # Пустой путь, будет заполнен после скачивания
                track_id
            ))
            self.connection.commit()
            print(f"Трек '{title}' добавлен в базу данных")
            return True, "added"
        except Exception as e:
            print(f"Ошибка добавления трека в базу: {e}")
            return False, f"error: {str(e)}"

    def get_new_connection(self):
        """
        Создаёт новое подключение для использования в другом потоке.
        """
        conn = sqlite3.connect("database/music_library.db", check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Позволяет обращаться к полям по имени

        return conn

    def get_download_queue(self):
        """
        Получает все треки из очереди загрузки с их статусами
        """
        query = """
            SELECT id, track_title, artist, status, file_path, url, download_date, track_id
            FROM downloaded_tracks
            ORDER BY
                CASE
                    WHEN status = 'pending' THEN 1
                    WHEN status = 'downloading' THEN 2
                    WHEN status = 'complete' THEN 3
                    WHEN status = 'error' THEN 4
                    ELSE 5
                    END,
                download_date DESC
            """
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка при получении очереди загрузки: {e}")
            return []

    def update_download_url(self, track_id, url):
        with self.lock:
            conn = self.get_new_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE downloaded_tracks SET download_url = ? WHERE id = ?",
                (url, track_id)
            )
            conn.commit()
            conn.close()