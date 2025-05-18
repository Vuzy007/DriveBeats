from database.base_init import initialize_database
import customtkinter as ctk
from gui.gui import MusicLoaderApp
from api_clients.soundcloud_client import search_tracks, get_stream_url
from threading import Thread
from database.db_manager import DatabaseManager
from download.downloader import TrackDownloader
from api_clients.z3fmParser import Z3fmParser

def main(db_manager):
    # Инициализация базы данных
    initialize_database()

    # Создание экземпляра парсера и вызов метода
    parser = Z3fmParser(db_manager=db_manager)
    parser.fetch_and_update_download_links(db_manager)

    # Запускаем фоновый процесс для скачивания треков
    downloader = TrackDownloader(db_manager)

    download_thread = Thread(target=downloader.process_downloads, daemon=True)
    download_thread.start()
    print("Фоновый процесс скачивания треков запущен.")

    # Запуск GUI
    root = ctk.CTk()
    app = MusicLoaderApp(root, search_tracks, get_stream_url)
    print("Приложение GUI запущено.")
    root.mainloop()

if __name__ == "__main__":
    try:
        # Сначала создаём экземпляр db_manager, потом передаём его в main
        db_manager = DatabaseManager("database.music_library.db")
        main(db_manager)
    except Exception as e:
        print(f"Ошибка выполнения приложения: {e}")
