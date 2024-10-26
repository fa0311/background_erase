import os
import tkinter as tk
from tkinter import filedialog
from typing import List, Tuple

import cv2
import numpy as np
import pygame
from cv2.typing import MatLike
from rembg import remove


class Mode:
    View: int = 0
    Eraser: int = 1
    RemBg: int = 2
    UndoBg: int = 3


class ImageViewer:
    def __init__(self, root: tk.Tk, screen_size: Tuple[int, int]) -> None:
        self.root = root
        self.screen_size = screen_size
        self.mode = Mode.View
        self.cv_image: MatLike
        self.cv_image_base: MatLike

        # Tkinterウィジェットの設定
        self.top_frame = tk.Frame(self.root)
        self.top_frame.pack(side=tk.TOP)
        self.fps_label = tk.Label(self.top_frame, text="FPS: 0")
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
        pygame.display.set_caption("Pygame Image Viewer")

        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(side=tk.TOP)

        self.view_button = tk.Button(
            self.button_frame,
            text="View",
            command=lambda: self.set_mode(Mode.View),
        )
        self.view_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.rembg_button = tk.Button(
            self.button_frame,
            text="Rembg",
            command=lambda: self.set_mode(Mode.RemBg),
        )
        self.rembg_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.undobg_button = tk.Button(
            self.button_frame,
            text="Undobg",
            command=lambda: self.set_mode(Mode.UndoBg),
        )
        self.undobg_button.pack(side=tk.LEFT, padx=5, pady=5)

        os.makedirs("include", exist_ok=True)
        os.makedirs("exclude", exist_ok=True)
        self.image_files, self.output_dir = self.select_folder()

        self.current_image = 0
        self.load_image(self.image_files[self.current_image % len(self.image_files)])
        self.dragging = False
        self.draw_box = False
        self.clock = pygame.time.Clock()

    def select_folder(self) -> tuple[List[str], List[str]]:
        folder_path = filedialog.askdirectory(title="Select a folder")
        return (
            [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, f))
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))
            ],
            [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if os.path.isdir(os.path.join(folder_path, f))
            ],
        )

    def start_drag(self, event: pygame.event.Event, box: bool = False) -> None:
        """ドラッグの開始位置を記録"""
        if self.image_rect.collidepoint(event.pos):
            self.dragging = True
            self.draw_box = box
            self.drag_start = event.pos

    def stop_drag(self) -> None:
        """ドラッグ終了"""
        self.dragging = False
        self.draw_box = False

    def drag_image(self, event: pygame.event.Event) -> None:
        """画像をドラッグ"""
        self.image_rect.topleft = (
            event.rel[0] + self.image_rect.x,
            event.rel[1] + self.image_rect.y,
        )

    def zoom_image(self, event: pygame.event.Event) -> None:
        """マウスポインタ基準で拡大縮小"""
        scale_factor = 1.1 if event.y > 0 else 1 / 1.1
        self.scale *= scale_factor
        mouse_x, mouse_y = pygame.mouse.get_pos()

        offset_x = (mouse_x - self.image_rect.x) * (scale_factor - 1)
        offset_y = (mouse_y - self.image_rect.y) * (scale_factor - 1)
        self.image_rect.x -= int(offset_x)
        self.image_rect.y -= int(offset_y)

        new_width = int(self.image.get_width() * self.scale)
        new_height = int(self.image.get_height() * self.scale)
        self.image_rect.size = (new_width, new_height)
        self.render_scaled()

    def trim(
        self, value: MatLike, pos1: Tuple[int, int], pos2: Tuple[int, int]
    ) -> MatLike:
        x1, x2 = sorted([pos1[0], pos2[0]])
        y1, y2 = sorted([pos1[1], pos2[1]])
        return value[y1:y2, x1:x2]

    def trim_back(
        self, value: MatLike, pos1: Tuple[int, int], pos2: Tuple[int, int]
    ) -> MatLike:
        x1, x2 = sorted([pos1[0], pos2[0]])
        y1, y2 = sorted([pos1[1], pos2[1]])
        data = np.zeros_like(self.cv_image_base)
        data[y1:y2, x1:x2] = value
        return data

    def remove_bg(self, event: pygame.event.Event) -> None:
        """背景を除去"""
        pos1 = self.get_image_pos(event.pos)
        pos2 = self.get_image_pos(self.drag_start)
        trimed = self.trim(self.cv_image, pos1, pos2)
        mask = remove(trimed)[:, :, 3] >= 150  # type: ignore
        data = np.zeros_like(trimed)
        data[mask] = trimed[mask]
        self.cv_image = self.trim_back(data, pos1, pos2)
        self.render_image()
        self.render_scaled()

    def undo_bg(self, event: pygame.event.Event) -> None:
        """背景除去を取り消す"""
        pos1 = self.get_image_pos(event.pos)
        pos2 = self.get_image_pos(self.drag_start)
        trimed = self.trim(self.cv_image_base, pos1, pos2)
        mask = remove(trimed)[:, :, 3] >= 150  # type: ignore
        data = np.zeros_like(trimed)
        data[mask] = trimed[mask]
        mask = self.trim_back(data, pos1, pos2) > 0
        self.cv_image[mask] = self.cv_image_base[mask]
        self.render_image()
        self.render_scaled()

    def next_image(self) -> None:
        """次の画像をロード"""
        self.current_image += 1
        self.load_image(self.image_files[self.current_image % len(self.image_files)])
        self.index_label.config(
            text=f"Index: {self.current_image + 1}/{len(self.image_files)}"
        )

    def previous_image(self) -> None:
        """前の画像をロード"""
        self.current_image -= 1
        self.load_image(self.image_files[self.current_image % len(self.image_files)])
        self.index_label.config(
            text=f"Index: {self.current_image + 1}/{len(self.image_files)}"
        )

    def include_image(self) -> None:
        """画像を含める"""
        self.image_dump("include", ["exclude"])
        self.next_image()

    def exclude_image(self) -> None:
        """画像を除外"""
        self.image_dump("exclude", ["include"])
        self.next_image()

    def image_dump(self, output: str, remove_path: list[str]) -> None:
        image_path = self.image_files[self.current_image % len(self.image_files)]
        image_name, image_ext = os.path.splitext(os.path.basename(image_path))

        output_dir = os.path.join(os.path.dirname(image_path), output)
        os.makedirs(output_dir, exist_ok=True)
        cv2.imwrite(os.path.join(output_dir, f"{image_name}.png"), self.cv_image)

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

    def pygame_loop(self) -> None:
        """Pygameのメインループ"""
        while True:
            self.handle_events()
            self.screen.fill((30, 30, 30))
            self.screen.blit(self.scaled_image, self.image_rect)

            if self.draw_box:
                self.render_box(self.drag_start, pygame.mouse.get_pos())

            pygame.display.flip()

            fps = self.clock.get_fps()
            self.fps_label.config(text=f"FPS: {fps:.2f}")

            self.root.update_idletasks()
            self.root.update()
            self.clock.tick(60)

    def load_image(self, image_path: str) -> None:
        """Load and convert image to pygame surface"""
        image_name, image_ext = os.path.splitext(os.path.basename(image_path))
        self.cv_image_base = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if self.cv_image_base.shape[2] == 3:
            self.cv_image_base = cv2.cvtColor(self.cv_image_base, cv2.COLOR_BGR2BGRA)

        for output in self.output_dir:
            path = os.path.join(output, f"{image_name}.png")
            if os.path.exists(path):
                self.cv_image = cv2.imread(path, cv2.IMREAD_UNCHANGED)
                if self.cv_image.shape[2] == 3:
                    self.cv_image = cv2.cvtColor(self.cv_image, cv2.COLOR_BGR2BGRA)
                break
        else:
            self.cv_image = self.cv_image_base.copy()
        self.fit_to_screen()

    def fit_to_screen(self) -> None:
        """Scale the image and convert to pygame format"""
        screen_w, screen_h = self.screen_size
        self.render_image()
        self.image_rect = self.image.get_rect()
        self.old_size = self.image_rect.size
        img_w, img_h = self.image_rect.size
        self.scale = min(screen_w / img_w, screen_h / img_h)
        self.image_rect.width = int(img_w * self.scale)
        self.image_rect.height = int(img_h * self.scale)
        self.image_rect.center = (screen_w // 2, screen_h // 2)
        self.render_scaled()

    def render_image(self) -> None:
        """Render cv image to pygame surface"""
        self.image = pygame.surfarray.make_surface(
            cv2.cvtColor(self.cv_image, cv2.COLOR_BGRA2RGB).swapaxes(0, 1)
        )

    def render_scaled(self) -> None:
        self.scaled_image = pygame.transform.scale(self.image, self.image_rect.size)

    def get_image_pos(self, pos: Tuple[int, int]) -> Tuple[int, int]:
        """Convert screen position to image position"""
        x = int((pos[0] - self.image_rect.x) / self.scale)
        y = int((pos[1] - self.image_rect.y) / self.scale)
        return x, y

    def set_mode(self, new_mode: int):
        """Change mode"""
        self.mode = new_mode

    # Enable the event handlers in handle_events function
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                self.root.quit()
            if self.mode == Mode.View:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.start_drag(event)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.stop_drag()
                elif event.type == pygame.MOUSEMOTION and self.dragging:
                    self.drag_image(event)
                elif event.type == pygame.MOUSEWHEEL:
                    self.zoom_image(event)
            elif self.mode == Mode.RemBg:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.start_drag(event, box=True)
                elif event.type == pygame.MOUSEBUTTONUP and self.dragging:
                    self.stop_drag()
                    self.remove_bg(event)
            elif self.mode == Mode.UndoBg:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.start_drag(event, box=True)
                elif event.type == pygame.MOUSEBUTTONUP and self.dragging:
                    self.stop_drag()
                    self.undo_bg(event)


if __name__ == "__main__":
    root = tk.Tk()
    viewer = ImageViewer(root, screen_size=(800, 600))
    viewer.pygame_loop()
