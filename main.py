import os
import tkinter as tk
import traceback
from tkinter import DoubleVar, filedialog, messagebox
from typing import List, Tuple

import cv2
import numpy as np
import pygame
from cv2.typing import MatLike
from rembg import new_session, remove
from rembg.sessions.base import BaseSession
from tqdm import tqdm


class Mode:
    View: int = 0
    Eraser: int = 1
    Pen: int = 2
    RemFill: int = 3
    UndoFill: int = 4
    RemBg: int = 5
    UndoBg: int = 6


class ImageViewer:
    def __init__(self, root: tk.Tk, screen_size: Tuple[int, int], rembg_session: BaseSession) -> None:
        self.root = root
        self.screen_size = screen_size
        self.rembg_session = rembg_session

        self.cv_image: MatLike
        self.cv_image_base: MatLike
        self.selected_mask: MatLike
        root.bind("<KeyPress>", self.key_press_event)
        root.bind("<KeyRelease>", self.key_release_event)

        self.top_frame = tk.Frame(self.root)
        self.top_frame.pack(side=tk.TOP)
        self.fps_label = tk.Label(self.top_frame, text="FPS: 0", width=8)
        self.fps_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.index_label = tk.Label(self.top_frame, text="Index: undefined")
        self.index_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.prev_button = tk.Button(
            self.top_frame,
            text="Previous",
            command=self.previous_image,
        )
        self.prev_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.next_button = tk.Button(
            self.top_frame,
            text="Next",
            command=self.next_image,
        )
        self.next_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.reload_button = tk.Button(
            self.top_frame,
            text="Reload",
            command=lambda: self.reload_image(),
        )
        self.reload_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.clear_button = tk.Button(
            self.top_frame,
            text="Clear",
            command=lambda: self.clear_image(),
        )
        self.clear_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.include_button = tk.Button(
            self.top_frame,
            text="Include",
            command=lambda: self.include_image(),
        )
        self.include_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.exclude_button = tk.Button(
            self.top_frame,
            text="Exclude",
            command=lambda: self.exclude_image(),
        )
        self.exclude_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.background_view_toggle = tk.Button(
            self.top_frame,
            text="Background",
            command=lambda: self.set_background_view(),
        )
        self.background_view_toggle.pack(side=tk.LEFT, padx=5, pady=5)

        self.auto_button = tk.Button(
            self.top_frame,
            text="Auto",
            command=lambda: self.auto(),
        )
        self.auto_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.embed_pygame = tk.Frame(
            self.root,
            width=screen_size[0],
            height=screen_size[1],
        )
        self.embed_pygame.pack(side=tk.TOP)
        os.environ["SDL_WINDOWID"] = str(self.embed_pygame.winfo_id())
        os.environ["SDL_VIDEODRIVER"] = "windib"
        pygame.display.init()
        self.screen = pygame.display.set_mode(screen_size)

        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(side=tk.TOP)

        self.view_button = tk.Button(
            self.button_frame,
            text="View",
            command=lambda: self.set_mode(Mode.View),
        )
        self.view_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.eraser_button = tk.Button(
            self.button_frame,
            text="Eraser",
            command=lambda: self.set_mode(Mode.Eraser),
        )
        self.eraser_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.pen_button = tk.Button(
            self.button_frame,
            text="Pen",
            command=lambda: self.set_mode(Mode.Pen),
        )
        self.pen_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.remfill_button = tk.Button(
            self.button_frame,
            text="RemFill",
            command=lambda: self.set_mode(Mode.RemFill),
        )
        self.remfill_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.undofill_button = tk.Button(
            self.button_frame,
            text="UndoFill",
            command=lambda: self.set_mode(Mode.UndoFill),
        )
        self.undofill_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.rembg_button = tk.Button(
            self.button_frame,
            text="RemBg",
            command=lambda: self.set_mode(Mode.RemBg),
        )
        self.rembg_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.undobg_button = tk.Button(
            self.button_frame,
            text="UndoBg",
            command=lambda: self.set_mode(Mode.UndoBg),
        )
        self.undobg_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.pen_size = DoubleVar()
        self.pen_size.set(30)
        self.pen_size_slider = tk.Scale(
            self.button_frame,
            orient="horizontal",
            showvalue=False,
            from_=1,
            to=50,
            variable=self.pen_size,
            background="gray",
            state="disabled",
        )
        self.pen_size_slider.pack(side=tk.LEFT, padx=5, pady=5)

        self.fill_threshold = DoubleVar()
        self.fill_threshold.set(10)
        self.fill_slider = tk.Scale(
            self.button_frame,
            orient="horizontal",
            showvalue=False,
            from_=1,
            to=50,
            variable=self.fill_threshold,
            background="gray",
            state="disabled",
        )
        self.fill_slider.pack(side=tk.LEFT, padx=5, pady=5)

        self.image_files = self.select_folder()

        root.focus_force()
        self.current_image = 0
        self.update_index_label()
        self.set_mode(Mode.View)
        self.background_view = False

        os.makedirs(os.path.join(self.folder_path, "include"), exist_ok=True)
        os.makedirs(os.path.join(self.folder_path, "exclude"), exist_ok=True)

        self.move_image(self.current_image)
        self.dragging = False
        self.elaser_drag = False
        self.pen_drag = False
        self.selected_box = False
        self.rem_fill_drag = False
        self.undo_fill_drag = False
        self.selected_pre = []
        self.mouse_pointer_size = 0
        self.mouse_border = False
        self.enable_shift = False
        self.clock = pygame.time.Clock()

    def select_folder(self) -> List[str]:
        self.folder_path = filedialog.askdirectory(title="Select a folder")
        if not self.folder_path:
            self.throw_error("No folder selected")

        files = [
            os.path.join(self.folder_path, f)
            for f in os.listdir(self.folder_path)
            if os.path.isfile(os.path.join(self.folder_path, f))
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))
        ]
        if not files:
            self.throw_error("No image files in the folder")
        return files

    def throw_error(self, message: str) -> None:
        messagebox.showerror("Error", message)
        raise ValueError(message)

    def drag_image(self, event: pygame.event.Event) -> None:
        self.image_rect.topleft = (
            event.rel[0] + self.image_rect.x,
            event.rel[1] + self.image_rect.y,
        )

    def zoom_image(self, event: pygame.event.Event) -> None:
        scale_factor = 1.1 if event.y > 0 else 1 / 1.1
        scale_new = self.scale * scale_factor
        mouse_x, mouse_y = pygame.mouse.get_pos()

        offset_x = (mouse_x - self.image_rect.x) * (scale_factor - 1)
        offset_y = (mouse_y - self.image_rect.y) * (scale_factor - 1)
        self.image_rect.x -= int(offset_x)
        self.image_rect.y -= int(offset_y)

        new_width = int(self.image.get_width() * scale_new)
        new_height = int(self.image.get_height() * scale_new)
        self.image_rect.size = (new_width, new_height)
        if (self.scale <= 1) != (scale_new <= 1):
            self.scale = scale_new
            self.render_image()
            self.render_scaled()
        else:
            self.scale = scale_new
            self.render_scaled()

    def trim(self, value: MatLike, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> MatLike:
        x1, x2 = sorted([pos1[0], pos2[0]])
        y1, y2 = sorted([pos1[1], pos2[1]])
        return value[y1:y2, x1:x2]

    def trim_back(self, value: MatLike, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> MatLike:
        x1, x2 = sorted([pos1[0], pos2[0]])
        y1, y2 = sorted([pos1[1], pos2[1]])
        data = np.zeros_like(self.cv_image_base)
        data[y1:y2, x1:x2] = value
        return data

    def get_gray_musk(self, value: MatLike) -> MatLike:
        return np.zeros((value.shape[0], value.shape[1]), dtype=np.uint8)

    def get_to_mask(self, value: MatLike) -> MatLike:
        return value[:, :] == 255

    def remove_bg(self, event: pygame.event.Event) -> None:
        pos1 = self.get_image_pos(event.pos)
        pos2 = self.get_image_pos(self.drag_start)
        trimed = self.trim(self.cv_image, pos1, pos2)
        if trimed.shape[0] > 0 and trimed.shape[1] > 0:
            mask = remove(trimed, session=self.rembg_session)[:, :, 3] < 150  # type: ignore
            trimed[mask] = np.array([0, 0, 0, 0])
            self.cv_image = self.trim_back(trimed, pos1, pos2)
            self.render_image()
            self.render_scaled()

    def undo_bg(self, event: pygame.event.Event) -> None:
        pos1 = self.get_image_pos(event.pos)
        pos2 = self.get_image_pos(self.drag_start)
        trimed = self.trim(self.cv_image_base.copy(), pos1, pos2)
        if trimed.shape[0] > 0 and trimed.shape[1] > 0:
            mask = remove(trimed, session=self.rembg_session)[:, :, 3] < 150  # type: ignore
            trimed[mask] = np.array([0, 0, 0, 0])
            mask = self.trim_back(trimed, pos1, pos2)[:, :, 3] == 255
            self.cv_image[mask] = self.cv_image_base[mask]
            self.render_image()
            self.render_scaled()

    def remove_flood_fill(self, pos: Tuple[int, int]) -> None:
        value = cv2.cvtColor(self.cv_image.copy(), cv2.COLOR_BGRA2BGR)
        h, w = value.shape[:2]
        mask = np.zeros((h + 2, w + 2), np.uint8)
        flag = 8 | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE
        threshold = self.fill_slider.get()
        cv2.floodFill(value, mask, pos, (0, 0, 0), (threshold,) * 3, (threshold,) * 3, flag)
        mask = mask[1:-1, 1:-1]
        self.cv_image[mask == 1] = np.array([0, 0, 0, 0])
        self.render_image()
        self.render_scaled()

    def undo_flood_fill(self, pos: Tuple[int, int]) -> None:
        value = cv2.cvtColor(self.cv_image_base.copy(), cv2.COLOR_BGRA2BGR)
        h, w = value.shape[:2]
        mask = np.zeros((h + 2, w + 2), np.uint8)
        flag = 8 | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE
        threshold = self.fill_slider.get()
        cv2.floodFill(value, mask, pos, (0, 0, 0), (threshold,) * 3, (threshold,) * 3, flag)
        mask = mask[1:-1, 1:-1]
        mask = mask == 1
        mask = np.stack([mask] * 4, axis=2)
        self.cv_image[mask] = self.cv_image_base[mask]
        self.render_image()
        self.render_scaled()

    def add_border(self, value: MatLike) -> MatLike:
        x, y, w, h = cv2.boundingRect(cv2.cvtColor(value, cv2.COLOR_BGRA2GRAY))
        if self.scale <= 1:
            thickness = int(max(2 / self.fit_scale, 1))
        else:
            thickness = 1
        value = cv2.rectangle(value, (x, y), (x + w, y + h), (255, 0, 0, 255), thickness)
        return value

    def add_contour(self, value: MatLike) -> MatLike:
        gray = self.get_gray_musk(value)
        musk = value[:, :, 3] > 0
        gray[musk] = 255
        contours, _ = cv2.findContours(gray, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        if self.scale <= 1:
            thickness = int(max(2 / self.fit_scale, 1))
        else:
            thickness = 1
        value = cv2.drawContours(value, contours, -1, (0, 255, 0, 255), thickness)
        return value

    def next_image(self) -> None:
        if self.enable_shift:
            self.current_image = (self.current_image + 10) % len(self.image_files)
        else:
            self.current_image = (self.current_image + 1) % len(self.image_files)
        self.move_image(self.current_image)
        self.update_index_label()

    def previous_image(self) -> None:
        if self.enable_shift:
            self.current_image = (self.current_image - 10) % len(self.image_files)
        else:
            self.current_image = (self.current_image - 1) % len(self.image_files)
        self.move_image(self.current_image)
        self.update_index_label()

    def update_index_label(self) -> None:
        self.index_label.config(text=f"Index: {self.current_image + 1}/{len(self.image_files)}")

    def clear_image(self) -> None:
        self.cv_image = self.cv_image_base.copy()
        self.render_image()
        self.render_scaled()

    def include_image(self) -> None:
        self.image_dump("include", ["exclude"])
        self.include_button.config(text="Include*")
        self.exclude_button.config(text="Exclude")

    def exclude_image(self) -> None:
        self.image_dump("exclude", ["include"])
        self.include_button.config(text="Include")
        self.exclude_button.config(text="Exclude*")

    def set_background_view(self) -> None:
        if self.background_view:
            self.background_view = False
            self.background_view_toggle.config(relief=tk.RAISED)
        else:
            self.background_view = True
            self.background_view_toggle.config(relief=tk.SUNKEN)
        self.render_image()
        self.render_scaled()

    def auto(self) -> None:
        if self.auto_button.cget("relief") == tk.RAISED:
            self.fps_label.config(text="Processing Auto", width=15)
            self.auto_button.config(relief=tk.SUNKEN)
            for _ in tqdm(self.image_files[self.current_image :]):
                mask = remove(self.cv_image_base, session=self.rembg_session)[:, :, 3] >= 150  # type: ignore
                self.cv_image = np.zeros_like(self.cv_image)
                self.cv_image[mask] = self.cv_image_base[mask]
                self.render_image()
                self.render_scaled()
                self.next_frame()
                self.include_image()
                if self.auto_button.cget("relief") == tk.RAISED:
                    break
                self.next_image()
            self.fps_label.config(text="FPS: 0", width=8)
            self.auto_button.config(relief=tk.RAISED)
        else:
            self.fps_label.config(text="FPS: 0", width=8)
            self.auto_button.config(relief=tk.RAISED)

    def image_dump(self, output: str, remove_path: list[str]) -> None:
        image_path = self.image_files[self.current_image % len(self.image_files)]
        image_name, image_ext = os.path.splitext(os.path.basename(image_path))

        output_dir = os.path.join(os.path.dirname(image_path), output)
        os.makedirs(output_dir, exist_ok=True)

        result, n = cv2.imencode(".png", self.cv_image)
        if not result:
            self.throw_error("Failed to encode image")

        with open(os.path.join(output_dir, f"{image_name}.png"), "wb") as f:
            f.write(n.tobytes())

        for re in remove_path:
            remove_dir = os.path.join(os.path.dirname(image_path), re)
            remove_image = os.path.join(remove_dir, f"{image_name}.png")
            if os.path.exists(remove_image):
                os.remove(remove_image)

    def render_box(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> None:
        surface = pygame.Surface((abs(pos1[0] - pos2[0]), abs(pos1[1] - pos2[1])))
        surface.set_alpha(128)
        surface.fill((255, 255, 255))
        self.screen.blit(surface, (min(pos1[0], pos2[0]), min(pos1[1], pos2[1])))

    def render_mouse_border(self, pos: Tuple[int, int]) -> None:
        surface = pygame.Surface((self.screen_size[0], self.screen_size[1]), pygame.SRCALPHA)
        pygame.draw.line(surface, (255, 255, 255), (pos[0], 0), (pos[0], self.screen_size[1]), 1)
        pygame.draw.line(surface, (255, 255, 255), (0, pos[1]), (self.screen_size[0], pos[1]), 1)
        self.screen.blit(surface, (0, 0))

    def render_pointer(self, pos: Tuple[int, int]) -> None:
        size = self.mouse_pointer_size
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        surface.set_alpha(128)
        pygame.draw.circle(surface, (255, 255, 255), (size / 2, size / 2), size / 2)
        self.screen.blit(surface, (pos[0] - size / 2, pos[1] - size / 2))

    def render_musk(self, pos: list[Tuple[int, int]]) -> None:
        size = max(self.pen_size.get() / self.scale, 0.5) * self.scale * 2
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surface, (255, 255, 255), (size / 2, size / 2), size / 2)
        for p in pos:
            self.screen.blit(surface, (p[0] - size / 2, p[1] - size / 2))

    def pygame_loop(self) -> None:
        try:
            while True:
                self.handle_events()
                self.next_frame()
                self.fps_label.config(text=f"FPS: {self.clock.get_fps():.2f}")
                self.clock.tick(120)
        except Exception as e:
            print(traceback.format_exc())
            print(e)

    def next_frame(self) -> None:
        self.screen.fill((30, 30, 30))
        self.screen.blit(self.scaled_image, self.image_rect)
        self.render_musk(self.selected_pre)
        pos = pygame.mouse.get_pos()
        if self.selected_box:
            self.render_box(self.drag_start, pos)
        if self.mouse_border:
            self.render_mouse_border(pos)
        self.render_pointer(pos)
        pygame.display.flip()

        self.root.update_idletasks()
        self.root.update()

    def load_image(self, image_path: str) -> None:
        image_name, image_ext = os.path.splitext(os.path.basename(image_path))
        self.root.title(f"Background Eraser - {image_name}{image_ext}")
        self.cv_image_base = cv2.imdecode(np.fromfile(image_path, np.uint8), cv2.IMREAD_UNCHANGED)
        if self.cv_image_base.shape[2] == 3:
            self.cv_image_base = cv2.cvtColor(self.cv_image_base, cv2.COLOR_BGR2BGRA)
        files = [
            (self.include_button, "Include"),
            (self.exclude_button, "Exclude"),
        ]
        for button, output in files:
            button.config(text=output)

        for button, output in files:
            path = os.path.join(os.path.dirname(image_path), output.lower(), f"{image_name}.png")
            if os.path.exists(path):
                self.cv_image = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_UNCHANGED)
                if self.cv_image.shape[2] == 3:
                    self.cv_image = cv2.cvtColor(self.cv_image, cv2.COLOR_BGR2BGRA)
                button.config(text=f"{output}*")
                break
        else:
            self.cv_image = self.cv_image_base.copy()

    def move_image(self, index: int):
        self.load_image(self.image_files[index % len(self.image_files)])
        self.fit_to_screen()

    def reload_image(self):
        self.load_image(self.image_files[self.current_image % len(self.image_files)])
        self.render_image()
        self.render_scaled()

    def fit_to_screen(self) -> None:
        screen_w, screen_h = self.screen_size
        img_w, img_h = self.cv_image.shape[1], self.cv_image.shape[0]
        self.fit_scale = min(screen_w / img_w, screen_h / img_h)
        self.scale = self.fit_scale
        self.render_image()
        self.image_rect = self.image.get_rect()

        self.image_rect.width = int(img_w * self.scale)
        self.image_rect.height = int(img_h * self.scale)
        self.image_rect.center = (screen_w // 2, screen_h // 2)
        self.render_scaled()

    def render_image(self) -> None:
        if self.background_view:
            output = self.add_border(self.add_contour(self.cv_image.copy()))
            mask = output[:, :, 3] == 0
            output[mask] = self.cv_image_base[mask]
            output = cv2.cvtColor(output, cv2.COLOR_BGRA2RGB)
        else:
            output = cv2.cvtColor(self.cv_image, cv2.COLOR_BGRA2RGB)
        self.image = pygame.surfarray.make_surface(output.swapaxes(0, 1))

    def render_scaled(self) -> None:
        self.scaled_image = pygame.transform.scale(self.image, self.image_rect.size)

    def get_image_pos(self, pos: Tuple[int, int]) -> Tuple[int, int]:
        x = min(max(int((pos[0] - self.image_rect.x) / self.scale), 0), self.cv_image.shape[1] - 1)
        y = min(max(int((pos[1] - self.image_rect.y) / self.scale), 0), self.cv_image.shape[0] - 1)
        return x, y

    def set_mode(self, mode: int):
        self.mode = mode
        self.button_list = [
            self.view_button,
            self.eraser_button,
            self.pen_button,
            self.remfill_button,
            self.undofill_button,
            self.rembg_button,
            self.undobg_button,
        ]
        self.mouse_border = False
        self.pen_size_slider.config(state="disabled", background="gray")
        self.fill_slider.config(state="disabled", background="gray")
        for button in self.button_list:
            button.config(relief=tk.RAISED)
        if mode == Mode.View:
            self.view_button.config(relief=tk.SUNKEN)
        elif mode == Mode.Eraser:
            self.pen_size_slider.config(state="normal", background="white")
            self.eraser_button.config(relief=tk.SUNKEN)
        elif mode == Mode.Pen:
            self.pen_size_slider.config(state="normal", background="white")
            self.pen_button.config(relief=tk.SUNKEN)
        elif mode == Mode.RemFill:
            self.fill_slider.config(state="normal", background="white")
            self.remfill_button.config(relief=tk.SUNKEN)
        elif mode == Mode.UndoFill:
            self.fill_slider.config(state="normal", background="white")
            self.undofill_button.config(relief=tk.SUNKEN)
        elif mode == Mode.RemBg:
            self.mouse_border = True
            self.rembg_button.config(relief=tk.SUNKEN)
        elif mode == Mode.UndoBg:
            self.mouse_border = True
            self.undobg_button.config(relief=tk.SUNKEN)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                self.root.quit()
            elif self.mode == Mode.View:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.drag_start = event.pos
                    self.dragging = True
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.dragging = False
            elif self.mode == Mode.Eraser:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.elaser_drag = True
                    self.selected_pre = []
                    self.selected_mask = self.get_gray_musk(self.cv_image)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.elaser_drag = False
                    self.selected_pre = []
                    musk = self.get_to_mask(self.selected_mask)
                    self.cv_image[musk] = np.array([0, 0, 0, 0])
                    self.render_image()
                    self.render_scaled()
            elif self.mode == Mode.Pen:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.pen_drag = True
                    self.selected_pre = []
                    self.selected_mask = self.get_gray_musk(self.cv_image)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.pen_drag = False
                    self.selected_pre = []
                    musk = self.get_to_mask(self.selected_mask)
                    self.cv_image[musk] = self.cv_image_base[musk]
                    self.render_image()
                    self.render_scaled()
            elif self.mode == Mode.RemFill:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.rem_fill_drag = True
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.rem_fill_drag = False
                    self.remove_flood_fill(self.get_image_pos(event.pos))
            elif self.mode == Mode.UndoFill:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.undo_fill_drag = True
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.undo_fill_drag = False
                    self.undo_flood_fill(self.get_image_pos(event.pos))
            elif self.mode == Mode.RemBg:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.drag_start = event.pos
                    self.selected_box = True
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.selected_box = False
                    self.remove_bg(event)
            elif self.mode == Mode.UndoBg:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.drag_start = event.pos
                    self.selected_box = True
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.selected_box = False
                    self.undo_bg(event)

            if event.type == pygame.MOUSEMOTION and self.dragging:
                self.drag_image(event)
            size = int(max(self.pen_size.get() / self.scale, 0.5))
            if event.type == pygame.MOUSEMOTION and self.elaser_drag:
                self.selected_pre.append(event.pos)
                pos = self.get_image_pos(event.pos)
                cv2.circle(self.selected_mask, (pos[0], pos[1]), size, (255, 255, 255), -1)
            if self.pen_drag:
                self.selected_pre.append(event.pos)
                pos = self.get_image_pos(event.pos)
                cv2.circle(self.selected_mask, (pos[0], pos[1]), size, (255, 255, 255), -1)
            if self.rem_fill_drag:
                self.remove_flood_fill(self.get_image_pos(event.pos))
            if self.undo_fill_drag:
                self.undo_flood_fill(self.get_image_pos(event.pos))
            if event.type == pygame.MOUSEWHEEL and not self.enable_shift:
                self.zoom_image(event)
            if event.type == pygame.MOUSEWHEEL and self.enable_shift:
                if self.mode == Mode.Eraser or self.mode == Mode.Pen:
                    self.pen_size.set(self.pen_size.get() + event.y)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
                self.drag_start = event.pos
                self.dragging = True
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 2:
                self.dragging = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.set_background_view()
        if self.mode == Mode.Eraser or self.mode == Mode.Pen:
            self.mouse_pointer_size = max(self.pen_size.get() / self.scale, 0.5) * self.scale * 2
        else:
            self.mouse_pointer_size = 5

    def key_press_event(self, event: tk.Event) -> None:
        print(event)
        if ["space"].count(event.keysym.lower()):
            self.include_image()
        elif ["d", "right"].count(event.keysym.lower()):
            self.next_image()
        elif ["a", "left"].count(event.keysym.lower()):
            self.previous_image()
        elif ["z"].count(event.keysym.lower()):
            self.reload_image()
        elif ["shift_l"].count(event.keysym.lower()):
            self.enable_shift = True

    def key_release_event(self, event: tk.Event) -> None:
        if ["shift_l"].count(event.keysym.lower()):
            self.enable_shift = False


if __name__ == "__main__":
    rembg_session = new_session()
    root = tk.Tk()
    viewer = ImageViewer(root, screen_size=(800, 600), rembg_session=rembg_session)
    viewer.pygame_loop()
