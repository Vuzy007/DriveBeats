import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from download import DownloadManager
from utils import normalize_filename, ensure_ffmpeg_installed

import yt_dlp
import threading

class MusicLoaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pankov.it Mp3 Loader for off-line music")
        self.ffmpeg_path = ensure_ffmpeg_installed()

        self.query_var = tk.StringVar()
        self.num_results_var = tk.IntVar(value=10)

        self.search_results = []
        self.queue_items = {}

        self.setup_gui()

        self.download_manager = DownloadManager(self.queue_tree, self.ffmpeg_path)

        # Привязка команд к кнопкам после создания download_manager
        self.pause_button.config(command=self.download_manager.pause_downloads)
        self.resume_button.config(command=self.download_manager.resume_downloads)

    def setup_gui(self):
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        top_frame = tk.Frame(main_frame)
        top_frame.pack(fill=tk.BOTH, expand=True)

        # Результаты поиска
        search_frame = tk.Frame(top_frame)
        search_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(search_frame, text="Результаты поиска:").pack()
        self.search_tree = ttk.Treeview(search_frame, columns=("title",), show="headings")
        self.search_tree.heading("title", text="Название трека")
        self.search_tree.pack(fill=tk.BOTH, expand=True)

        # Очередь загрузки
        queue_frame = tk.Frame(top_frame)
        queue_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(queue_frame, text="Очередь загрузки:").pack()
        self.queue_tree = ttk.Treeview(queue_frame, columns=("title", "status", "progress"), show="headings")
        self.queue_tree.heading("title", text="Название трека")
        self.queue_tree.heading("status", text="Статус")
        self.queue_tree.heading("progress", text="Прогресс")
        self.queue_tree.pack(fill=tk.BOTH, expand=True)

        # Управление
        bottom_frame = tk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X)

        tk.Entry(bottom_frame, textvariable=self.query_var, width=30).pack(side=tk.LEFT, padx=5)
        tk.Entry(bottom_frame, textvariable=self.num_results_var, width=5).pack(side=tk.LEFT)
        tk.Button(bottom_frame, text="Найти", command=self.search_tracks).pack(side=tk.LEFT, padx=5)
        tk.Button(bottom_frame, text="Добавить в очередь", command=self.add_to_queue).pack(side=tk.LEFT, padx=5)
        tk.Button(bottom_frame, text="Прослушать", command=self.preview_track).pack(side=tk.LEFT, padx=5)

        self.pause_button = tk.Button(bottom_frame, text="Пауза")
        self.pause_button.pack(side=tk.LEFT, padx=5)

        self.resume_button = tk.Button(bottom_frame, text="Возобновить")
        self.resume_button.pack(side=tk.LEFT, padx=5)

        self.status_label = tk.Label(main_frame, text="Готов к работе...")
        self.status_label.pack(pady=5)

    def search_tracks(self):
        query = self.query_var.get()
        num_results = self.num_results_var.get()
        if not query:
            messagebox.showerror("Ошибка поиска", "Введите текст запроса.")
            return

        self.status_label.config(text="Идёт поиск треков...")
        self.search_tree.delete(*self.search_tree.get_children())
        self.search_results.clear()

        threading.Thread(target=self._search_thread, args=(query, num_results), daemon=True).start()

    def _search_thread(self, query, num_results):
        opts = {
            'quiet': True,
            'skip_download': True,
            'extract_flat': True,
            'forcejson': True,
            'default_search': 'ytsearch',
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                result = ydl.extract_info(f"ytsearch{num_results}:{query}", download=False)
                entries = result.get('entries', [])
                for entry in entries:
                    title = entry.get('title')
                    url = entry.get('url')
                    if title and url:
                        self.search_results.append({'title': title, 'url': url})
                        self.search_tree.insert("", tk.END, values=(title,))

        except Exception as e:
            messagebox.showerror("Ошибка поиска", str(e))

        self.status_label.config(text="Готово.")

    def add_to_queue(self):
        selected = self.search_tree.selection()
        for item in selected:
            idx = self.search_tree.index(item)
            track = self.search_results[idx]
            if track['url'] not in self.queue_items:
                queue_id = self.queue_tree.insert("", tk.END, values=(track['title'], "Ожидание", "0%"))
                self.queue_items[track['url']] = queue_id
                self.download_manager.add_to_queue(track['title'], track['url'], queue_id)

    def preview_track(self):
        selected = self.search_tree.selection()
        if not selected:
            messagebox.showinfo("Прослушивание", "Выберите трек для предпрослушивания.")
            return

        idx = self.search_tree.index(selected[0])
        track = self.search_results[idx]
        self.download_manager.preview_track(track['url'])


if __name__ == "__main__":
    root = tk.Tk()
    app = MusicLoaderApp(root)
    root.mainloop()
