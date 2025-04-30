from PIL import Image
import customtkinter as ctk
from tkinter import Menu, filedialog, messagebox
import subprocess
import os
from database.db_manager import DatabaseManager

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class TrackItem(ctk.CTkFrame):
    currently_playing = None
    def __init__(self, master, title, stream_url=None, track_id=None):
        super().__init__(master)
        self.title = title
        self.stream_url = stream_url
        self.track_id = track_id
        self.configure(height=40)
        self.selected = False
        self.ffplay_process = None

        self.label = ctk.CTkLabel(self, text=title, anchor="w")
        self.label.pack(fill="both", expand=True, padx=5)

        # Кнопки — будут размещены поверх текста
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")

        self.img_play = ctk.CTkImage(light_image=Image.open("pic/play-48.png"), size=(20, 20))
        self.img_pause = ctk.CTkImage(light_image=Image.open("pic/pause-48.png"), size=(20, 20))
        self.img_stop = ctk.CTkImage(light_image=Image.open("pic/stop-48.png"), size=(20, 20))
        self.img_delete = ctk.CTkImage(light_image=Image.open("pic/delete-48.png"), size=(20, 20))

        self.listen_button = ctk.CTkButton(
            self.button_frame,
            image=self.img_play,
            text="",
            width=20,
            height=20,
            fg_color="transparent",
            hover_color="#365D1D",
            command=self.listen_track
        )
        self.stop_button = ctk.CTkButton(
            self.button_frame,
            image=self.img_stop,
            text="",
            width=20,
            height=20,
            fg_color="transparent",
            hover_color="#365D1D",
            command=self.stop_track
        )
        self.delete_button = ctk.CTkButton(
            self.button_frame,
            image=self.img_delete,
            text="",
            width=20,
            height=20,
            fg_color="transparent",
            hover_color="#E38445",
            command=self.delete_track
        )

        self.listen_button.pack(side="left", padx=2)
        self.stop_button.pack(side="left", padx=2)
        self.delete_button.pack(side="left", padx=2)

        # Скрытое размещение поверх — по оси Z
        self.button_frame.place(relx=1.0, y=0, anchor="ne")
        self.button_frame.lower()  # скрыть под слоем

        self.bind_events()

    def bind_events(self):
        for widget in (self, self.label):
            widget.bind("<Enter>", self.on_hover, add="+")
            widget.bind("<Leave>", self.on_leave, add="+")
            widget.bind("<Button-1>", self.toggle_selection, add="+")

    def toggle_selection(self, event):
        ctrl = event.state & 0x0004
        if ctrl:
            self.selected = not self.selected
        else:
            for widget in self.master.winfo_children():
                if isinstance(widget, TrackItem):
                    widget.selected = False
                    widget.configure(fg_color="transparent")
            self.selected = True
        self.update_selection_style()

    def update_selection_style(self):
        self.configure(fg_color="#333955" if self.selected else "transparent")

    def on_hover(self, event=None):
        self.button_frame.lift()  # показать
        fade_job = getattr(self, "fade_job", None)
        if fade_job is not None:
            self.after_cancel(fade_job)

    def on_leave(self, event=None):
        self.fade_job = self.after(1000, self.button_frame.lower)

    def listen_track(self):
        if not self.stream_url:
            return
        if TrackItem.currently_playing and TrackItem.currently_playing is not self:
            TrackItem.currently_playing.stop_track()
        if self.ffplay_process and self.ffplay_process.poll() is None:
            self.ffplay_process.terminate()

        try:
            ffplay_path = os.path.abspath("ffmpeg/bin/ffplay.exe")
            self.ffplay_process = subprocess.Popen([
                ffplay_path, "-nodisp", "-autoexit", self.stream_url
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            TrackItem.currently_playing = self
            print(f"▶ Воспроизведение: {self.title}")
        except FileNotFoundError:
            print("❌ ffplay не найден.")

    def stop_track(self):
        if self.ffplay_process and self.ffplay_process.poll() is None:
            self.ffplay_process.terminate()
            print(f"■ Остановлено: {self.title}")
        if TrackItem.currently_playing is self:
            TrackItem.currently_playing = None

    def delete_track(self):
        self.stop_track()
        print(f"✖ Удалено: {self.title}")
        self.destroy()

class MusicLoaderApp:
    def __init__(self, root, search_tracks, get_stream_url):
        self.root = root
        self.search_tracks = search_tracks
        self.get_stream_url = get_stream_url
        self.root.title("DriveBeats: mp3 (pankov.it)")
        self.root.geometry("1100x700")

        self.save_path = ctk.StringVar(value="D:/Music")

        self.create_menu()
        self.build_layout()
        self.refresh_queue()

    def create_menu(self):
        menubar = Menu(self.root)

        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label="Выход", command=self.root.quit)
        menubar.add_cascade(label="Файл", menu=file_menu)

        settings_menu = Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Настройки")
        menubar.add_cascade(label="Настройки", menu=settings_menu)

        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(label="О программе")
        menubar.add_cascade(label="О программе", menu=help_menu)

        self.root.config(menu=menubar)

    def build_layout(self):
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        top_panel = ctk.CTkFrame(main_frame)
        top_panel.pack(fill="x")

        self.query_entry = ctk.CTkEntry(top_panel, placeholder_text="Введите запрос", width=300)
        self.query_entry.pack(side="left", padx=(0, 10))
        self.query_entry.bind("<Return>", lambda event: self.perform_search())

        ctk.CTkButton(top_panel, text="Найти", command=self.perform_search).pack(side="left", padx=5)

        path_panel = ctk.CTkFrame(main_frame)
        path_panel.pack(fill="x", pady=5)

        self.path_entry = ctk.CTkEntry(path_panel, textvariable=self.save_path, width=600)
        self.path_entry.pack(side="left", padx=(0, 5))
        ctk.CTkButton(path_panel, text="Обзор", command=self.browse_directory).pack(side="left")

        middle_frame = ctk.CTkFrame(main_frame)
        middle_frame.pack(fill="both", expand=True, pady=10)

        left_frame = ctk.CTkFrame(middle_frame)
        left_frame.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(left_frame, text="Результаты поиска:").pack(anchor="w")

        self.search_container = ctk.CTkScrollableFrame(left_frame)
        self.search_container.pack(fill="both", expand=True, padx=5)

        center_controls = ctk.CTkFrame(middle_frame, width=80)
        center_controls.pack(side="left", fill="y")
        center_controls.pack_propagate(False)

        self.img_right = ctk.CTkImage(light_image=Image.open("pic/right-48.png"), size=(24, 24))
        self.img_d_right = ctk.CTkImage(light_image=Image.open("pic/double_right-48.png"), size=(24, 24))

        ctk.CTkLabel(center_controls, text="").pack(expand=True)
        ctk.CTkButton(
            center_controls,
            image=self.img_right,
            text="",
            command=self.add_selected,
            fg_color="transparent",
            hover_color="#333333",
        ).pack(pady=5)
        ctk.CTkButton(
            center_controls,
            image=self.img_d_right,
            text="",
            command=self.add_all,
            fg_color="transparent",
            hover_color="#333333",
        ).pack(pady=5)
        ctk.CTkLabel(center_controls, text="").pack(expand=True)

        right_frame = ctk.CTkFrame(middle_frame)
        right_frame.pack(side="left", fill="both", expand=True)

        queue_control = ctk.CTkFrame(right_frame)
        queue_control.pack(fill="x", padx=5, pady=15)
        self.start_queue_btn = ctk.CTkButton(
            queue_control,
            text="Начать загрузку",
            command=self.start_download_queue
        )
        self.start_queue_btn.pack(side="left", padx=2)
        ctk.CTkButton(
            queue_control,
            text="Обновить",
            command=self.refresh_queue
        ).pack(side="left", padx=2)

        ctk.CTkButton(queue_control, text="Стоп").pack(side="left", padx=2)
        ctk.CTkOptionMenu(queue_control, values=["1 поток", "2 потока", "4 потока"]).pack(side="left", padx=2)
        ctk.CTkButton(
            queue_control,
            text="Очистить очередь",
            command=self.clear_queue
        ).pack(side="left", padx=2)

        ctk.CTkLabel(right_frame, text="Очередь загрузки:").pack(anchor="w")
        self.queue_container = ctk.CTkScrollableFrame(right_frame)
        self.queue_container.pack(fill="both", expand=True, padx=5)

        self.status_label = ctk.CTkLabel(main_frame, text="")
        self.status_label.pack(pady=5)

    def browse_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.save_path.set(path)

    def perform_search(self):
        query = self.query_entry.get()
        print(f"Поиск по SoundCloud: {query}")
        for widget in self.search_container.winfo_children():
            widget.destroy()

        results = self.search_tracks(query)
        if not results:
            item = TrackItem(self.search_container, "Нет результатов")
            item.pack(fill="x", pady=2, padx=5)
            return

        for track in results:
            user = track.get("user", {}).get("username", "?")
            title = track.get("title", "Без названия")
            full_title = f"{user} — {title}"
            track_id = str(track.get("id", ""))

            # Инициализация stream_url для каждого трека
            stream_url = None

            for transcoding in track.get("media", {}).get("transcodings", []):
                if "progressive" in transcoding.get("format", {}).get("protocol", ""):
                    try:
                        stream_url = self.get_stream_url(transcoding.get("url"))
                        break
                    except Exception as e:
                        print(f"Ошибка получения ссылки на стрим: {e}")
                        continue

            # Проверим, что stream_url получен
            if stream_url is None:
                print(f"Не удалось получить поток для трека: {full_title}")
                continue

            # Создаем элемент только если поток успешно получен
            item = TrackItem(self.search_container, full_title, stream_url=stream_url, track_id=track_id)
            item.pack(fill="x", pady=2, padx=5)

    def add_selected(self):
        db = DatabaseManager()
        added_count = 0
        duplicate_count = 0
        requeued_count = 0
        error_count = 0

        for widget in self.search_container.winfo_children():
            if isinstance(widget, TrackItem) and widget.selected and widget.stream_url:
                # Добавляем в базу данных как новую запись
                success, status = db.add_track(widget.title, "Unknown Artist", widget.stream_url, widget.track_id)

                if success and status == "added":
                    added_count += 1
                elif success and status == "requeued":
                    requeued_count += 1
                elif status == "duplicate":
                    duplicate_count += 1
                else:
                    error_count += 1

        status_message = f"Добавлено: {added_count}"
        if requeued_count > 0:
            status_message += f", Восстановлено: {requeued_count}"
        if duplicate_count > 0:
            status_message += f", Пропущено: {duplicate_count}"
        if error_count > 0:
            status_message += f", Ошибок: {error_count}"

        print(status_message)
        self.status_label.configure(text=status_message)
        self.refresh_queue()

    def add_all(self):
        print("Добавление всех треков в очередь загрузки")
        db = DatabaseManager()
        added_count = 0
        duplicate_count = 0
        requeued_count = 0
        error_count = 0

        for widget in self.search_container.winfo_children():
            if isinstance(widget, TrackItem) and widget.stream_url:
                # Добавляем в базу данных как новую запись
                success, status = db.add_track(widget.title, "Unknown Artist", widget.stream_url, widget.track_id)

                if success and status == "added":
                    added_count += 1
                elif success and status == "requeued":
                    requeued_count += 1
                elif status == "duplicate":
                    duplicate_count += 1
                else:
                    error_count += 1

        status_message = f"Добавлено: {added_count}"
        if requeued_count > 0:
            status_message += f", Восстановлено: {requeued_count}"
        if duplicate_count > 0:
            status_message += f", Пропущено: {duplicate_count}"
        if error_count > 0:
            status_message += f", Ошибок: {error_count}"

        print(status_message)
        self.status_label.configure(text=status_message)
        self.refresh_queue()

    def refresh_queue(self):
        """Обновляет список треков в очереди загрузки"""
        # Очистка существующих элементов
        for widget in self.queue_container.winfo_children():
            widget.destroy()

        # Получение треков из базы данных
        db = DatabaseManager()
        tracks = db.get_download_queue()

        if not tracks:
            no_tracks_label = ctk.CTkLabel(self.queue_container, text="Очередь загрузки пуста")
            no_tracks_label.pack(pady=10)
            return

        # Создание элементов для каждого трека
        for track in tracks:
            queue_item = QueueItem(
                self.queue_container,
                db_id=track["id"],
                title=track["track_title"],
                artist=track["artist"] or "Unknown Artist",
                status=track["status"],
                file_path=track["file_path"],
                stream_url=track["url"],
                download_date=track["download_date"]
            )
            queue_item.pack(fill="x", pady=2, padx=5)

    def start_download_queue(self):
        """Запускает процесс загрузки треков из очереди"""
        from download.downloader import TrackDownloader
        import threading

        # Получаем путь сохранения из интерфейса
        download_dir = self.save_path.get()
        if not download_dir:
            self.status_label.configure(text="Ошибка: укажите папку для сохранения")
            return

        # Создаем загрузчик и запускаем в отдельном потоке
        db = DatabaseManager()
        downloader = TrackDownloader(db, download_dir=download_dir)

        # Запускаем загрузку в отдельном потоке
        download_thread = threading.Thread(target=downloader.process_downloads)
        download_thread.daemon = True  # Поток завершится при закрытии приложения
        download_thread.start()

        self.status_label.configure(text="Загрузка треков запущена")

        # Обновляем очередь через 2 секунды, чтобы показать прогресс
        self.root.after(2000, self.refresh_queue)

    def clear_queue(self):
        """Очищает очередь загрузки"""
        if messagebox.askyesno("Очистить очередь", "Удалить все треки из очереди загрузки?"):
            db = DatabaseManager()
            db.connection.execute("DELETE FROM downloaded_tracks WHERE status != 'complete'")
            db.connection.commit()
            print("Очередь загрузки очищена")
            self.status_label.configure(text="Очередь загрузки очищена")
            self.refresh_queue()

class QueueItem(ctk.CTkFrame):
    def __init__(self, master, db_id, title, artist, status, file_path, stream_url=None, download_date=None):
        super().__init__(master)
        self.db_id = db_id
        self.title = title
        self.artist = artist
        self.status = status
        self.file_path = file_path
        self.stream_url = stream_url
        self.download_date = download_date
        self.configure(height=40)

        # Создаем цветовую схему для различных статусов
        status_colors = {
            "pending": ("#FFD700", "#333333"),  # Золотой фон, темный текст
            "downloading": ("#4CAF50", "#FFFFFF"),  # Зеленый фон, белый текст
            "complete": ("#333333", "#FFFFFF"),  # Темный фон, белый текст
            "error": ("#F44336", "#FFFFFF")  # Красный фон, белый текст
        }

        # Применяем цвет в зависимости от статуса
        bg_color, text_color = status_colors.get(status, ("#333333", "#FFFFFF"))

        # Рамка для названия трека
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.pack(fill="both", expand=True, side="left")

        # Название трека
        self.label = ctk.CTkLabel(
            self.info_frame,
            text=title,
            anchor="w",
            text_color=text_color
        )
        self.label.pack(fill="x", expand=True, padx=5)

        # Статус
        status_display = {
            "pending": "⌛ Ожидание",
            "downloading": "⬇️ Загрузка...",
            "complete": "✅ Завершено",
            "error": "❌ Ошибка"
        }

        self.status_label = ctk.CTkLabel(
            self,
            text=status_display.get(status, status),
            width=100,
            anchor="e",
            text_color=text_color
        )
        self.status_label.pack(side="right", padx=5)

        # Кнопки действий
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.pack(side="right", padx=5)

        # Значки для кнопок
        self.img_play = ctk.CTkImage(light_image=Image.open("pic/play-48.png"), size=(20, 20))
        self.img_retry = ctk.CTkImage(light_image=Image.open("pic/retry-48.png"), size=(20, 20))
        self.img_delete = ctk.CTkImage(light_image=Image.open("pic/delete-48.png"), size=(20, 20))

        # При ошибке показываем кнопку повтора
        if status == "error":
            self.retry_button = ctk.CTkButton(
                self.button_frame,
                image=self.img_retry,
                text="",
                width=20,
                height=20,
                fg_color="transparent",
                hover_color="#365D1D",
                command=self.retry_download
            )
            self.retry_button.pack(side="left", padx=2)

        # Если файл уже скачан, показываем кнопку воспроизведения
        if status == "complete" and file_path and os.path.exists(file_path):
            self.play_button = ctk.CTkButton(
                self.button_frame,
                image=self.img_play,
                text="",
                width=20,
                height=20,
                fg_color="transparent",
                hover_color="#365D1D",
                command=self.play_local_file
            )
            self.play_button.pack(side="left", padx=2)

        # Кнопка удаления для всех статусов
        self.delete_button = ctk.CTkButton(
            self.button_frame,
            image=self.img_delete,
            text="",
            width=20,
            height=20,
            fg_color="transparent",
            hover_color="#E38445",
            command=self.delete_from_queue
        )
        self.delete_button.pack(side="left", padx=2)

    def retry_download(self):
        """Повторная попытка загрузки трека с ошибкой"""
        db = DatabaseManager()
        db.connection.execute(
            "UPDATE downloaded_tracks SET status = 'pending' WHERE id = ?",
            (self.db_id,)
        )
        db.connection.commit()
        print(f"Трек '{self.title}' возвращен в очередь загрузки")
        # Уведомляем родительское окно о необходимости обновить список
        self.master.master.master.master.refresh_queue()  # Обращение к главному окну через предков

    def play_local_file(self):
        """Воспроизведение локального файла"""
        if os.path.exists(self.file_path):
            try:
                ffplay_path = os.path.abspath("ffmpeg/bin/ffplay.exe")
                subprocess.Popen([
                    ffplay_path, "-nodisp", "-autoexit", self.file_path
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"▶ Воспроизведение локального файла: {self.title}")
            except Exception as e:
                print(f"Ошибка воспроизведения: {e}")
        else:
            print(f"❌ Файл не найден: {self.file_path}")

    def delete_from_queue(self):
        """Удаление трека из очереди загрузки"""
        if messagebox.askyesno("Удаление трека", f"Удалить трек '{self.title}' из очереди загрузки?"):
            db = DatabaseManager()
            db.connection.execute("DELETE FROM downloaded_tracks WHERE id = ?", (self.db_id,))
            db.connection.commit()
            print(f"✖ Удалено из очереди: {self.title}")
            self.destroy()
            # Если файл существует и был скачан, спрашиваем о его удалении
            if self.status == "complete" and self.file_path and os.path.exists(self.file_path):
                if messagebox.askyesno("Удаление файла", "Также удалить файл с диска?"):
                    try:
                        os.remove(self.file_path)
                        print(f"Файл удален: {self.file_path}")
                    except Exception as e:
                        print(f"Ошибка удаления файла: {e}")

if __name__ == "__main__":
    root = ctk.CTk()
    app = MusicLoaderApp(root)
    root.mainloop()
