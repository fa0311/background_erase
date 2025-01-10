import os
from tkinter import filedialog

import cv2
import numpy as np
from tqdm import tqdm

AUTO_FIX = False

if __name__ == "__main__":
    folder_path = filedialog.askdirectory(title="Select a folder")
    if not folder_path:
        raise SystemExit("No folder selected")

    original_files = [
        f
        for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f))
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]

    include_files = [
        f
        for f in os.listdir(os.path.join(folder_path, "include"))
        if os.path.isfile(os.path.join(folder_path, "include", f))
        if f.lower().endswith(".png")
    ]

    exclude_files = [
        f
        for f in os.listdir(os.path.join(folder_path, "exclude"))
        if os.path.isfile(os.path.join(folder_path, "exclude", f))
        if f.lower().endswith(".png")
    ]

    original_files_set = set([os.path.splitext(f)[0] for f in original_files])
    include_files_set = set([os.path.splitext(f)[0] for f in include_files])
    exclude_files_set = set([os.path.splitext(f)[0] for f in exclude_files])

    for files in (include_files_set | exclude_files_set) - original_files_set:
        print(f"not found original image: {files}")

    for files in original_files_set - (include_files_set | exclude_files_set):
        print(f"not found include/exclude image: {files}")

    for files in include_files_set & exclude_files_set:
        print(f"found both include/exclude image: {files}")

    for base_path in tqdm(original_files):
        filename = os.path.splitext(base_path)[0]
        if filename in include_files_set:
            dir = "include"
        elif filename in exclude_files_set:
            dir = "exclude"
        else:
            continue

        path = os.path.join(folder_path, dir, f"{filename}.png")

        cv_image = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_UNCHANGED)
        cv_base_image = cv2.imdecode(np.fromfile(os.path.join(folder_path, base_path), np.uint8), cv2.IMREAD_UNCHANGED)

        if cv_image.shape[0] != cv_base_image.shape[0] or cv_image.shape[1] != cv_base_image.shape[1]:
            tqdm.write(f"size mismatch: {base_path}")

            if AUTO_FIX:
                if cv_image.shape[0] == cv_base_image.shape[1] and cv_image.shape[1] == cv_base_image.shape[0]:
                    cv_image = cv2.rotate(cv_image, cv2.ROTATE_90_CLOCKWISE)
                    result, n = cv2.imencode(".png", cv_image)
                    with open(path, "wb") as f:
                        f.write(n.tobytes())
                    tqdm.write(f"fixed: {base_path}")
                else:
                    tqdm.write(f"skip: {base_path}")
