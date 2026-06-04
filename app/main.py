from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui.main_window import MainWindow


def create_app() -> tk.Tk:
    root = tk.Tk()
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    MainWindow(root)
    return root


def main() -> None:
    app = create_app()
    app.mainloop()


if __name__ == "__main__":
    main()
