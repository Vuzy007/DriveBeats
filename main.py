from database.base_init import initialize_database
from PySide6 import QtWidgets
from gui.gui import MusicLoaderApp
from api_clients.musicbrainz_client import search_recordings
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
    qt_app = QtWidgets.QApplication([])
    window = MusicLoaderApp(search_recordings)
    print("Приложение GUI запущено.")
    window.show()
    qt_app.exec()

if __name__ == "__main__":
    try:
        # Сначала создаём экземпляр db_manager, потом передаём его в main
        db_manager = DatabaseManager("database.music_library.db")
        main(db_manager)
    except Exception as e:
        print(f"Ошибка выполнения приложения: {e}")
