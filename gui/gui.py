import customtkinter as ctk
from tkinter import Menu, filedialog
import subprocess
import os

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class TrackItem(ctk.CTkFrame):
    currently_playing = None  # глобальная ссылка на активный трек
    selected_items = set()

    def __init__(self, master, title, stream_url=None):
        super().__init__(master)
        self.title = title
        self.stream_url = stream_url
        self.configure(height=40)

        self.hovered = False
        self.fade_job = None
        self.selected = False
        self.ffplay_process = None

        self.label = ctk.CTkLabel(self, text=title, anchor="w")
        self.label.pack(side="left", fill="both", expand=True, padx=5)

        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.listen_button = ctk.CTkButton(self.button_frame, text="Слушать", width=60, height=28, command=self.listen_track)
        self.stop_button = ctk.CTkButton(self.button_frame, text="Стоп", width=60, height=28, command=self.stop_track)
        self.delete_button = ctk.CTkButton(self.button_frame, text="Удалить", width=60, height=28, command=self.delete_track)

        self.listen_button.pack(side="left", padx=2)
        self.stop_button.pack(side="left", padx=2)
        self.delete_button.pack(side="left", padx=2)

        self.bind_events()

    def bind_events(self):
        self.bind("<Enter>", self.on_hover, add="+")
        self.bind("<Leave>", self.on_leave, add="+")
        self.label.bind("<Enter>", self.on_hover, add="+")
        self.label.bind("<Leave>", self.on_leave, add="+")
        self.button_frame.bind("<Enter>", self.on_hover, add="+")
        self.button_frame.bind("<Leave>", self.on_leave, add="+")
        self.label.bind("<Button-1>", self.toggle_selection, add="+")

    def toggle_selection(self, event):
        modifiers = event.state
        ctrl = modifiers & 0x0004

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
        if self.selected:
            self.configure(fg_color="#333955")
        else:
            self.configure(fg_color="transparent")

    def on_hover(self, event=None):
        if self.fade_job:
            self.after_cancel(self.fade_job)
        self.hovered = True
        self.button_frame.pack(side="right", padx=5)

    def on_leave(self, event=None):
        if self.fade_job:
            self.after_cancel(self.fade_job)
        if self.hovered:
            self.fade_job = self.after(1000, self.fade_out_buttons)

    def fade_out_buttons(self):
        if not self.hovered:
            self.button_frame.pack_forget()

    def listen_track(self):
        if not self.stream_url:
            return

        # Остановить воспроизведение предыдущего трека, если был
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
            print("❌ ffplay не найден. Убедитесь, что путь указан верно.")
        except FileNotFoundError:
            print("❌ ffplay не найден. Убедитесь, что путь указан верно.")

    def stop_track(self):
        if self.ffplay_process and self.ffplay_process.poll() is None:
            self.ffplay_process.terminate()
            print(f"■ Остановлено: {self.title}")
        if TrackItem.currently_playing is self:
            TrackItem.currently_playing = None

    def delete_track(self):
        self.stop_track()
        print(f"✖ Удалить: {self.title}")
        self.destroy()




class MusicLoaderApp:
    def __init__(self, root, search_tracks, get_stream_url):
        self.root = root
        self.search_tracks = search_tracks
        self.get_stream_url = get_stream_url
        self.root.title("Pankov.it Mp3 Loader for off-line music")
        self.root.geometry("1100x700")

        self.save_path = ctk.StringVar(value="D:/Music")

        self.create_menu()
        self.build_layout()

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

        ctk.CTkLabel(center_controls, text="").pack(expand=True)
        ctk.CTkButton(center_controls, text=">", command=self.add_selected).pack(pady=5)
        ctk.CTkButton(center_controls, text=">>", command=self.add_all).pack(pady=5)
        ctk.CTkLabel(center_controls, text="").pack(expand=True)

        right_frame = ctk.CTkFrame(middle_frame)
        right_frame.pack(side="left", fill="both", expand=True)

        queue_control = ctk.CTkFrame(right_frame)
        queue_control.pack(fill="x", padx=5, pady=15)
        self.pause_resume_btn = ctk.CTkButton(queue_control, text="Пауза/Старт")
        self.pause_resume_btn.pack(side="left", padx=2)
        ctk.CTkButton(queue_control, text="Стоп").pack(side="left", padx=2)
        ctk.CTkOptionMenu(queue_control, values=["1 поток", "2 потока", "4 потока"]).pack(side="left", padx=2)
        ctk.CTkButton(queue_control, text="Очистить").pack(side="left", padx=2)

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

            # получаем стрим URL
            stream_url = None
            for transcoding in track.get("media", {}).get("transcodings", []):
                if "progressive" in transcoding.get("format", {}).get("protocol", ""):
                    stream_url = self.get_stream_url(transcoding.get("url"))
                    break

            item = TrackItem(self.search_container, full_title, stream_url=stream_url)
            item.pack(fill="x", pady=2, padx=5)

    def add_selected(self):
        print("Добавить выделенный трек")

    def add_all(self):
        print("Добавить все треки")


if __name__ == "__main__":
    root = ctk.CTk()
    app = MusicLoaderApp(root)
    root.mainloop()
