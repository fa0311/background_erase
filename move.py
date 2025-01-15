import os
import tkinter as tk
from tkinter import filedialog

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class MultiFolderSelectApp:
    def __init__(self, root, folder_paths):
        self.root = root
        self.root.title("Multi File Move")

        self.log_text = tk.Text(self.root, width=50, height=10)
        self.log_text.pack()

        event_handler = FolderEventHandler(self)
        observer = Observer()
        observer.schedule(event_handler, folder_paths, recursive=True)
        observer.start()

    def show_log(self, message: str):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)


class FolderEventHandler(FileSystemEventHandler):
    def __init__(self, app: MultiFolderSelectApp):
        self.app = app
        self.log = False
        self.basename_from: dict[str, str] = {}

    def info(self, message: str):
        if self.log:
            self.app.show_log(message)

    def error(self, message: str):
        self.app.show_log(message)

    def on_created(self, event):
        super().on_created(event)
        assert isinstance(event.src_path, str)
        dir = os.path.dirname(event.src_path)
        if not (dir.endswith("include") or dir.endswith("exclude")):
            assert isinstance(event.src_path, str)
            dir = os.path.dirname(event.src_path)
            filename, ext = os.path.splitext(os.path.basename(event.src_path))
            from_dir = self.basename_from.get(f"{filename}{ext}")
            if from_dir:
                self.move(from_dir, dir, filename)
                self.basename_from.pop(f"{filename}{ext}")
            else:
                self.error(f"Error: {filename} is unknown")

    def on_deleted(self, event):
        super().on_deleted(event)
        assert isinstance(event.src_path, str)
        dir = os.path.dirname(event.src_path)
        if not (dir.endswith("include") or dir.endswith("exclude")):
            filename, ext = os.path.splitext(os.path.basename(event.src_path))
            from_dir = self.basename_from.get(f"{filename}{ext}")
            if from_dir:
                self.error(f"Error: {filename} is unknown")
            else:
                self.basename_from[f"{filename}{ext}"] = dir

    def move(self, from_dir: str, to_dir: str, filename: str):
        include_path = os.path.join(from_dir, "include", f"{filename}.png")
        new_include_path = os.path.join(to_dir, "include", f"{filename}.png")

        exclude_path = os.path.join(from_dir, "exclude", f"{filename}.png")
        new_exclude_path = os.path.join(to_dir, "exclude", f"{filename}.png")

        if os.path.exists(include_path):
            os.rename(include_path, new_include_path)
            self.info(f"Move: {filename} from {from_dir} to {to_dir}")
        elif os.path.exists(exclude_path):
            os.rename(exclude_path, new_exclude_path)
            self.info(f"Move: {filename} from {from_dir} to {to_dir}")
        else:
            self.error(f"Error: {filename} is unknown")


if __name__ == "__main__":
    folder_paths = filedialog.askdirectory(mustexist=True, title="Select folders")

    root = tk.Tk()
    app = MultiFolderSelectApp(root, folder_paths)
    root.mainloop()
