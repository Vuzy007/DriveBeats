import tkinter as tk
from gui.gui import MusicLoaderApp

def main():
    root = tk.Tk()
    app = MusicLoaderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
