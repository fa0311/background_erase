import os
from tkinter import filedialog

if __name__ == "__main__":
    folder_path = filedialog.askdirectory(title="Select a folder")
    if not folder_path:
        raise SystemExit("No folder selected")

    original_files = [
        os.path.splitext(os.path.basename(os.path.join(folder_path, f)))[0]
        for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f))
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]

    include_files = [
        os.path.splitext(os.path.basename(os.path.join(folder_path, f)))[0]
        for f in os.listdir(os.path.join(folder_path, "include"))
        if os.path.isfile(os.path.join(folder_path, "include", f))
        if f.lower().endswith(".png")
    ]

    exclude_files = [
        os.path.splitext(os.path.basename(os.path.join(folder_path, f)))[0]
        for f in os.listdir(os.path.join(folder_path, "exclude"))
        if os.path.isfile(os.path.join(folder_path, "exclude", f))
        if f.lower().endswith(".png")
    ]

    for files in (set(include_files) | set(exclude_files)) - set(original_files):
        print(f"not found original image: {files}")

    for files in set(original_files) - (set(include_files) | set(exclude_files)):
        print(f"not found include/exclude image: {files}")
