from PySide6 import QtWidgets, QtGui, QtCore
import subprocess
import os
from database.db_manager import DatabaseManager


# --- Playback management ----------------------------------------------------
# These globals store the currently playing ffplay process and the widget that
# started it. They allow us to stop any playback when another play button is
# pressed or when a stop button is triggered.
current_process = None
current_widget = None


def stop_current_playback():
    """Terminate any running ffplay process."""
    global current_process, current_widget
    if current_process and current_process.poll() is None:
        current_process.terminate()
    if current_widget:
        # ensure widget does not keep stale reference
        if hasattr(current_widget, "ffplay_process"):
            current_widget.ffplay_process = None
    current_process = None
    current_widget = None

class TrackItemWidget(QtWidgets.QWidget):
    def __init__(self, title, artist="Unknown Artist", stream_url=None, track_id=None):
        super().__init__()
        self.title = title
        self.artist = artist
        self.stream_url = stream_url
        self.track_id = track_id
        self.ffplay_process = None

        layout = QtWidgets.QHBoxLayout(self)
        self.checkbox = QtWidgets.QCheckBox()
        layout.addWidget(self.checkbox)

        self.label = QtWidgets.QLabel(f"{artist} — {title}")
        layout.addWidget(self.label, 1)

        self.play_btn = QtWidgets.QToolButton()
        self.play_btn.setIcon(QtGui.QIcon('pic/play-48.png'))
        self.play_btn.clicked.connect(self.listen_track)
        layout.addWidget(self.play_btn)

        self.stop_btn = QtWidgets.QToolButton()
        self.stop_btn.setIcon(QtGui.QIcon('pic/stop-48.png'))
        self.stop_btn.clicked.connect(self.stop_track)
        layout.addWidget(self.stop_btn)

        self.del_btn = QtWidgets.QToolButton()
        self.del_btn.setIcon(QtGui.QIcon('pic/delete-48.png'))
        self.del_btn.clicked.connect(self.delete_self)
        layout.addWidget(self.del_btn)

    def listen_track(self):
        if not self.stream_url:
            return
        # Stop any other track that might be playing
        stop_current_playback()
        try:
            ffplay_path = os.path.abspath('ffmpeg/bin/ffplay.exe')
            self.ffplay_process = subprocess.Popen([
                ffplay_path, '-nodisp', '-autoexit', self.stream_url
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            global current_process, current_widget
            current_process = self.ffplay_process
            current_widget = self
        except FileNotFoundError:
            print('ffplay not found')

    def stop_track(self):
        stop_current_playback()

    def delete_self(self):
        self.stop_track()
        self.setParent(None)

class QueueItemWidget(QtWidgets.QWidget):
    def __init__(self, db_id, title, artist, status, file_path, stream_url, download_date):
        super().__init__()
        self.db_id = db_id
        self.title = title
        self.artist = artist
        self.status = status
        self.file_path = file_path
        self.stream_url = stream_url

        layout = QtWidgets.QHBoxLayout(self)
        self.label = QtWidgets.QLabel(f'{artist} - {title}')
        layout.addWidget(self.label, 1)

        self.progress = QtWidgets.QProgressBar()
        progress_map = {
            'pending': (0, 'Ожидание'),
            'downloading': (50, 'Загрузка'),
            'paused': (25, 'Пауза'),
            'complete': (100, 'Завершено'),
            'error': (0, 'Ошибка')
        }
        value, text = progress_map.get(status, (0, status))
        self.progress.setValue(value)
        layout.addWidget(self.progress)

        self.status_label = QtWidgets.QLabel(text)
        layout.addWidget(self.status_label)

        self.btn_frame = QtWidgets.QWidget()
        btn_layout = QtWidgets.QHBoxLayout(self.btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.btn_frame)

        if status == 'error':
            self.retry_btn = QtWidgets.QToolButton()
            self.retry_btn.setIcon(QtGui.QIcon('pic/retry-48.png'))
            self.retry_btn.clicked.connect(self.retry_download)
            btn_layout.addWidget(self.retry_btn)
        if status == 'complete' and file_path and os.path.exists(file_path):
            self.play_btn = QtWidgets.QToolButton()
            self.play_btn.setIcon(QtGui.QIcon('pic/play-48.png'))
            self.play_btn.clicked.connect(self.play_local_file)
            btn_layout.addWidget(self.play_btn)

        self.del_btn = QtWidgets.QToolButton()
        self.del_btn.setIcon(QtGui.QIcon('pic/delete-48.png'))
        self.del_btn.clicked.connect(self.delete_from_queue)
        btn_layout.addWidget(self.del_btn)

    def retry_download(self):
        db = DatabaseManager()
        db.connection.execute(
            "UPDATE downloaded_tracks SET status = 'pending' WHERE id = ?",
            (self.db_id,)
        )
        db.connection.commit()
        self.setParent(None)

    def play_local_file(self):
        if os.path.exists(self.file_path):
            try:
                ffplay_path = os.path.abspath('ffmpeg/bin/ffplay.exe')
                # Stop any other playback before starting a new one
                stop_current_playback()
                proc = subprocess.Popen([
                    ffplay_path, '-nodisp', '-autoexit', self.file_path
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                global current_process, current_widget
                current_process = proc
                current_widget = None
            except Exception as e:
                print(f'Ошибка воспроизведения: {e}')
        else:
            print('Файл не найден')

    def delete_from_queue(self):
        db = DatabaseManager()
        db.connection.execute('DELETE FROM downloaded_tracks WHERE id = ?', (self.db_id,))
        db.connection.commit()
        if self.status == 'complete' and self.file_path and os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
            except Exception as e:
                print(f'Ошибка удаления файла: {e}')
        self.setParent(None)

class MusicLoaderApp(QtWidgets.QMainWindow):
    def __init__(self, search_tracks, get_stream_url=None):
        super().__init__()
        self.search_tracks = search_tracks
        self.get_stream_url = get_stream_url
        self.setWindowTitle('DriveBeats: mp3 (pankov.it)')
        self.resize(1100, 700)

        central = QtWidgets.QWidget()
        central.setStyleSheet("background: transparent;")
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)

        self.dark_mode = False
        self.downloader = None
        self.downloader_thread = None

        menubar = self.menuBar()
        file_menu = menubar.addMenu('Файл')
        file_menu.addAction('Выход', self.close)
        menubar.addMenu('Настройки')
        menubar.addMenu('О программе')

        self.theme_btn = QtWidgets.QPushButton('Тёмная тема')
        self.theme_btn.clicked.connect(self.toggle_theme)
        menubar.setCornerWidget(self.theme_btn, QtCore.Qt.TopRightCorner)

        top_layout = QtWidgets.QHBoxLayout()
        self.query_entry = QtWidgets.QLineEdit()
        self.query_entry.setPlaceholderText('Введите запрос')
        self.query_entry.returnPressed.connect(self.perform_search)
        search_btn = QtWidgets.QPushButton('Найти')
        search_btn.clicked.connect(self.perform_search)
        top_layout.addWidget(self.query_entry)
        top_layout.addWidget(search_btn)
        main_layout.addLayout(top_layout)

        path_layout = QtWidgets.QHBoxLayout()
        self.path_edit = QtWidgets.QLineEdit('D:/Music')
        browse_btn = QtWidgets.QPushButton('Обзор')
        browse_btn.clicked.connect(self.browse_directory)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(browse_btn)
        main_layout.addLayout(path_layout)

        splitter = QtWidgets.QSplitter()
        main_layout.addWidget(splitter, 1)

        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.addWidget(QtWidgets.QLabel('Результаты поиска:'))
        self.search_list = QtWidgets.QListWidget()
        left_layout.addWidget(self.search_list, 1)
        btn_layout = QtWidgets.QHBoxLayout()
        add_sel_btn = QtWidgets.QPushButton('Добавить выбранные')
        add_sel_btn.clicked.connect(self.add_selected)
        add_all_btn = QtWidgets.QPushButton('Добавить все')
        add_all_btn.clicked.connect(self.add_all)
        btn_layout.addWidget(add_sel_btn)
        btn_layout.addWidget(add_all_btn)
        left_layout.addLayout(btn_layout)
        splitter.addWidget(left_widget)

        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        queue_controls = QtWidgets.QHBoxLayout()
        self.start_queue_btn = QtWidgets.QPushButton('Начать загрузку')
        self.start_queue_btn.clicked.connect(self.start_download_queue)

        self.stop_queue_btn = QtWidgets.QPushButton('Стоп загрузки')
        self.stop_queue_btn.clicked.connect(self.stop_download_queue)

        refresh_btn = QtWidgets.QPushButton('Обновить')
        refresh_btn.clicked.connect(self.refresh_queue)

        clear_btn = QtWidgets.QPushButton('Очистить очередь')
        clear_btn.clicked.connect(self.clear_queue)

        self.concurrent_combo = QtWidgets.QComboBox()
        self.concurrent_combo.addItems([str(i) for i in range(1, 6)])

        queue_controls.addWidget(self.start_queue_btn)
        queue_controls.addWidget(self.stop_queue_btn)
        queue_controls.addWidget(QtWidgets.QLabel('Потоков:'))
        queue_controls.addWidget(self.concurrent_combo)
        queue_controls.addWidget(refresh_btn)
        queue_controls.addWidget(clear_btn)
        right_layout.addLayout(queue_controls)
        right_layout.addWidget(QtWidgets.QLabel('Очередь загрузки:'))
        self.queue_list = QtWidgets.QListWidget()
        right_layout.addWidget(self.queue_list, 1)
        splitter.addWidget(right_widget)
        splitter.setSizes([500, 500])

        self.status_label = QtWidgets.QLabel()
        main_layout.addWidget(self.status_label)

        self.refresh_queue()
        self.apply_light_theme()

    def browse_directory(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, 'Выбор папки', self.path_edit.text())
        if directory:
            self.path_edit.setText(directory)

    def perform_search(self):
        query = self.query_entry.text()
        self.search_list.clear()
        results = self.search_tracks(query)
        if not results:
            item = QtWidgets.QListWidgetItem()
            widget = QtWidgets.QLabel('Нет результатов')
            item.setSizeHint(widget.sizeHint())
            self.search_list.addItem(item)
            self.search_list.setItemWidget(item, widget)
            return
        for track in results:
            title = track.get('title', 'Без названия')
            artist = track.get('user', {}).get('name', 'Unknown Artist')
            track_id = track.get('id', '')
            stream_url = None
            if self.get_stream_url and track_id:
                try:
                    stream_url = self.get_stream_url(track_id)
                except Exception as e:
                    print(f'Ошибка получения ссылки: {e}')
            item = QtWidgets.QListWidgetItem()
            widget = TrackItemWidget(title, artist=artist, stream_url=stream_url, track_id=track_id)
            item.setSizeHint(widget.sizeHint())
            self.search_list.addItem(item)
            self.search_list.setItemWidget(item, widget)

    def add_selected(self):
        db = DatabaseManager()
        added = dup = requeued = err = 0
        for i in range(self.search_list.count()):
            item = self.search_list.item(i)
            widget = self.search_list.itemWidget(item)
            if isinstance(widget, TrackItemWidget) and widget.checkbox.isChecked():
                success, status = db.add_track(
                    widget.title,
                    widget.artist,
                    widget.stream_url or '',
                    widget.track_id
                )
                if success and status == 'added':
                    added += 1
                elif success and status == 'requeued':
                    requeued += 1
                elif status == 'duplicate':
                    dup += 1
                else:
                    err += 1
        msg = f'Добавлено: {added}'
        if requeued:
            msg += f', Восстановлено: {requeued}'
        if dup:
            msg += f', Пропущено: {dup}'
        if err:
            msg += f', Ошибок: {err}'
        self.status_label.setText(msg)
        self.refresh_queue()

    def add_all(self):
        db = DatabaseManager()
        added = dup = requeued = err = 0
        for i in range(self.search_list.count()):
            item = self.search_list.item(i)
            widget = self.search_list.itemWidget(item)
            if isinstance(widget, TrackItemWidget):
                success, status = db.add_track(
                    widget.title,
                    widget.artist,
                    widget.stream_url or '',
                    widget.track_id
                )
                if success and status == 'added':
                    added += 1
                elif success and status == 'requeued':
                    requeued += 1
                elif status == 'duplicate':
                    dup += 1
                else:
                    err += 1
        msg = f'Добавлено: {added}'
        if requeued:
            msg += f', Восстановлено: {requeued}'
        if dup:
            msg += f', Пропущено: {dup}'
        if err:
            msg += f', Ошибок: {err}'
        self.status_label.setText(msg)
        self.refresh_queue()

    def refresh_queue(self):
        self.queue_list.clear()
        db = DatabaseManager()
        tracks = db.get_download_queue()
        if not tracks:
            self.queue_list.addItem('Очередь загрузки пуста')
            return
        for track in tracks:
            item = QtWidgets.QListWidgetItem()
            widget = QueueItemWidget(
                db_id=track['id'],
                title=track['track_title'],
                artist=track['artist'] or 'Unknown Artist',
                status=track['status'],
                file_path=track['file_path'],
                stream_url=track['url'],
                download_date=track['download_date']
            )
            item.setSizeHint(widget.sizeHint())
            self.queue_list.addItem(item)
            self.queue_list.setItemWidget(item, widget)

    def start_download_queue(self):
        from download.downloader import TrackDownloader
        import threading

        if self.downloader_thread and self.downloader_thread.is_alive():
            self.status_label.setText('Загрузка уже запущена')
            return

        download_dir = self.path_edit.text()
        if not download_dir:
            self.status_label.setText('Ошибка: укажите папку для сохранения')
            return

        db = DatabaseManager()
        max_workers = int(self.concurrent_combo.currentText())
        self.downloader = TrackDownloader(db, download_dir=download_dir, max_workers=max_workers)
        self.downloader_thread = threading.Thread(target=self.downloader.process_downloads, daemon=True)
        self.downloader_thread.start()
        self.status_label.setText('Загрузка треков запущена')
        QtCore.QTimer.singleShot(2000, self.refresh_queue)

    def stop_download_queue(self):
        if self.downloader:
            self.downloader.stop()
        if self.downloader_thread:
            self.downloader_thread.join(timeout=0)
        self.status_label.setText('Загрузка остановлена')

    def clear_queue(self):
        db = DatabaseManager()
        db.connection.execute("DELETE FROM downloaded_tracks WHERE status != 'complete'")
        db.connection.commit()
        self.status_label.setText('Очередь загрузки очищена')
        self.refresh_queue()

    def toggle_theme(self):
        if self.dark_mode:
            self.apply_light_theme()
            self.theme_btn.setText('Тёмная тема')
            self.dark_mode = False
        else:
            self.apply_dark_theme()
            self.theme_btn.setText('Светлая тема')
            self.dark_mode = True

    def apply_light_theme(self):
        style = """
        QMainWindow {
            background-image: url(pic/logo.png);
            background-repeat: no-repeat;
            background-position: center;
        }
        """
        self.setStyleSheet(style)

    def apply_dark_theme(self):
        style = """
        QMainWindow {
            background-color: #2b2b2b;
            background-image: url(pic/logo.png);
            background-repeat: no-repeat;
            background-position: center;
        }
        * {color: #dddddd;}
        QLineEdit, QListWidget, QProgressBar, QLabel, QPushButton, QComboBox {
            background-color: #3c3c3c;
        }
        """
        self.setStyleSheet(style)

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    from api_clients.audius_client import search_tracks, get_stream_url
    window = MusicLoaderApp(search_tracks, get_stream_url)
    window.show()
    app.exec()
