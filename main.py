from database.base_init import initialize_database
import customtkinter as ctk
from gui.gui import MusicLoaderApp
from api_clients.suondcloud_client import search_tracks, get_stream_url

initialize_database()

def main():
    root = ctk.CTk()
    app = MusicLoaderApp(root, search_tracks, get_stream_url)
    root.mainloop()

if __name__ == "__main__":
    main()


