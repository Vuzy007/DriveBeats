import sqlite3
import os

def initialize_database():
    # Путь к базе данных
    db_folder = "database"
    db_name = "music_library.db"
    db_path = os.path.join(db_folder, db_name)

    # Убедимся, что папка существует
    os.makedirs(db_folder, exist_ok=True)

    # Если база уже существует, просто сообщаем и выходим
    if os.path.exists(db_path):
        print(f"База данных '{db_path}' уже существует. Инициализация не требуется.")
        return

    # Создание новой базы данных
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Создание таблиц
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS downloaded_tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        track_title TEXT NOT NULL,
        artist TEXT,
        album TEXT,
        genre TEXT,
        release_year INTEGER,
        download_date TEXT NOT NULL,
        license_type TEXT,
        file_path TEXT NOT NULL,
        duration INTEGER,
        source TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key TEXT NOT NULL UNIQUE,
        setting_value TEXT
    )
    ''')

    cursor.executemany('''
    INSERT OR IGNORE INTO settings (setting_key, setting_value)
    VALUES 
    ('default_download_path', 'downloads/'),
    ('license_filter', 'none'),
    ('sort_mode', 'flat')
    ''', [])

    conn.commit()
    conn.close()

    print(f"База данных '{db_path}' успешно создана и инициализирована.")
