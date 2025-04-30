from database.base_init import initialize_database
import customtkinter as ctk
from gui.gui import MusicLoaderApp
from api_clients.soundcloud_client import search_tracks, get_stream_url  # Исправлен импорт
from threading import Thread
from database.db_manager import DatabaseManager
from download.downloader import TrackDownloader


def main():
    # Инициализация базы данных
    initialize_database()

    # Запускаем фоновый процесс для скачивания треков
    db = DatabaseManager()
    downloader = TrackDownloader(db)

    download_thread = Thread(target=downloader.process_downloads, daemon=True)
    download_thread.start()
    print("Фоновый процесс скачивания треков запущен.")

    # Запуск GUI
    root = ctk.CTk()  # Создаём окно
    app = MusicLoaderApp(root, search_tracks, get_stream_url)
    print("Приложение GUI запущено.")
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Ошибка выполнения приложения: {e}")