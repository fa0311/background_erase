import os
import tkinter as tk
from tkinter import filedialog
from typing import List, Tuple

import cv2
import numpy as np
import pygame
from cv2.typing import MatLike
from rembg import remove


class ImageSelector:
    def __init__(self, image_files: List[str]) -> None:
        self.current_index = 0
        self.image_files = image_files

    def index(self) -> int:
        return self.current_index

    def total(self) -> int:
        return len(self.image_files)

    def current(self) -> str:
        return self.image_files[self.current_index]

    def next(self):
        self.current_index = (self.current_index + 1) % len(self.image_files)

    def previous(self):
        self.current_index = (self.current_index - 1) % len(self.image_files)


class Mode:
    View: int = 0
    Erase: int = 1
    Trim: int = 2
    Range: int = 3


class ImageViewer:
    def __init__(self, root: tk.Tk, screen_size: Tuple[int, int]) -> None:
        self.root = root
        self.screen_size = screen_size
        self.mode = Mode.View
        self.cv_image: MatLike

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

        self.erase_button = tk.Button(
            self.button_frame,
            text="View",
            command=lambda: self.set_mode(Mode.View),
        )
        self.erase_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.erase_button = tk.Button(
            self.button_frame,
            text="Erase",
            command=lambda: self.set_mode(Mode.Erase),
        )
        self.erase_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.trim_button = tk.Button(
            self.button_frame,
            text="Trim",
            command=lambda: self.set_mode(Mode.Trim),
        )
        self.trim_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.range_button = tk.Button(
            self.button_frame,
            text="Range",
            command=lambda: self.set_mode(Mode.Range),
        )
        self.range_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.rembg_button = tk.Button(
            self.button_frame,
            text="Rembg",
            command=lambda: self.remove_background(),
        )
        self.rembg_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.image_files = ImageSelector(self.select_folder())
        self.load_image(self.image_files.current())
        self.dragging = False
        self.clock = pygame.time.Clock()

    def select_folder(self) -> List[str]:
        folder_path = filedialog.askdirectory(title="Select a folder")
        if folder_path:
            return [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))
            ]
        return []

    # def load_image(self, image_path: str) -> None:
    #     """指定した画像を読み込み、スケールを画面に合わせる"""
    #     self.image = pygame.image.load(image_path).convert_alpha()
    #     self.image_rect = self.image.get_rect()
    #     self.fit_to_screen()

    # def handle_events(self) -> None:
    #     """Pygameのイベントを処理"""
    #     for event in pygame.event.get():
    #         if event.type == pygame.QUIT:
    #             pygame.quit()
    #             self.root.quit()
    #         elif event.type == pygame.MOUSEBUTTONDOWN:
    #             if event.button == 1:
    #                 self.start_drag(event)
    #         elif event.type == pygame.MOUSEBUTTONUP:
    #             self.stop_drag()
    #         elif event.type == pygame.MOUSEMOTION:
    #             self.drag_image(event)
    #         elif event.type == pygame.MOUSEWHEEL:
    #             self.zoom_image(event)

    def start_drag(self, event: pygame.event.Event) -> None:
        """ドラッグの開始位置を記録"""
        if self.image_rect.collidepoint(event.pos):
            self.dragging = True
            self.drag_start = event.pos
            self.image_start_pos = self.image_rect.topleft

    def stop_drag(self) -> None:
        """ドラッグ終了"""
        self.dragging = False

    def drag_image(self, event: pygame.event.Event) -> None:
        """画像をドラッグ"""
        if self.dragging:
            dx = event.pos[0] - self.drag_start[0]
            dy = event.pos[1] - self.drag_start[1]
            self.image_rect.topleft = (
                self.image_start_pos[0] + dx,
                self.image_start_pos[1] + dy,
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

    def next_image(self) -> None:
        """次の画像をロード"""
        self.image_files.next()
        self.load_image(self.image_files.current())

        index = self.image_files.index()
        total = self.image_files.total()
        self.index_label.config(text=f"Index: {index + 1}/{total}")

    def previous_image(self) -> None:
        """前の画像をロード"""
        self.image_files.previous()
        self.load_image(self.image_files.current())

        index = self.image_files.index()
        total = self.image_files.total()
        self.index_label.config(text=f"Index: {index + 1}/{total}")

    def pygame_loop(self) -> None:
        """Pygameのメインループ"""
        while True:
            self.handle_events()
            self.screen.fill((30, 30, 30))
            scaled_image = pygame.transform.scale(self.image, self.image_rect.size)
            self.screen.blit(scaled_image, self.image_rect)
            pygame.display.flip()

            fps = self.clock.get_fps()
            self.fps_label.config(text=f"FPS: {fps:.2f}")

            self.root.update_idletasks()
            self.root.update()
            self.clock.tick(60)

    def load_image(self, image_path: str) -> None:
        """Load and convert image to pygame surface"""
        self.cv_image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        self.fit_to_screen()

    def fit_to_screen(self) -> None:
        """Scale the image and convert to pygame format"""
        screen_w, screen_h = self.screen_size
        self.image = pygame.surfarray.make_surface(
            cv2.cvtColor(self.cv_image, cv2.COLOR_BGR2RGB).swapaxes(0, 1)
        )
        self.image_rect = self.image.get_rect()
        img_w, img_h = self.image_rect.size
        self.scale = min(screen_w / img_w, screen_h / img_h)
        self.image_rect.width = int(img_w * self.scale)
        self.image_rect.height = int(img_h * self.scale)
        self.image_rect.center = (screen_w // 2, screen_h // 2)

    def render_image(self) -> None:
        """Render cv image to pygame surface"""
        self.image = pygame.surfarray.make_surface(
            cv2.cvtColor(self.cv_image, cv2.COLOR_BGR2RGB).swapaxes(0, 1)
        )

    def get_image_pos(self, pos: Tuple[int, int]) -> Tuple[int, int]:
        """Convert screen position to image position"""
        x = int((pos[0] - self.image_rect.x) / self.scale)
        y = int((pos[1] - self.image_rect.y) / self.scale)
        return x, y

    def erase_mode(self, x, y, radius=10):
        """Apply erase effect at (x, y)"""
        self.cv_image = cv2.circle(
            self.cv_image, (x, y), radius, (255, 255, 255, 0), thickness=-1
        )
        self.render_image()

    def trim(self, start_pos: Tuple[int, int], end_pos: Tuple[int, int]) -> None:
        """Trim portion of image"""
        if None in (start_pos, end_pos):
            return
        x1, y1 = start_pos
        x2, y2 = end_pos
        self.cv_image = self.cv_image[y1:y2, x1:x2]

    def range_mode(self, x, y, radius=50):
        """Draw range markings and erase"""
        overlay = self.cv_image.copy()
        cv2.circle(overlay, (x, y), radius, (255, 255, 255, 0), thickness=-1)
        alpha = 0.25
        self.cv_image = cv2.addWeighted(overlay, alpha, self.cv_image, 1 - alpha, 0)

    def remove_background(self):
        """Remove background using rembg"""
        mask = np.zeros_like(remove(self.cv_image)[:, :, 3] > 150)  # type: ignore
        self.cv_image[mask] = self.cv_image[mask]

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
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.start_drag(event)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.stop_drag()
                elif event.type == pygame.MOUSEMOTION:
                    self.drag_image(event)
                elif event.type == pygame.MOUSEWHEEL:
                    self.zoom_image(event)

            elif self.mode == Mode.Erase:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.start_drag(event)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.stop_drag()
                elif event.type == pygame.MOUSEMOTION:
                    if pygame.mouse.get_pressed()[0]:
                        pos = pygame.mouse.get_pos()
                        x, y = self.get_image_pos(pos)
                        self.erase_mode(x, y)

            elif self.mode == Mode.Trim:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.start_drag(event)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.stop_drag()
                    start_pos = self.get_image_pos(self.drag_start)
                    end_pos = self.get_image_pos(event.pos)
                    self.trim(start_pos, end_pos)

            elif self.mode == Mode.Range:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.start_drag(event)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.stop_drag()
                    pos = pygame.mouse.get_pos()
                    x, y = self.get_image_pos(pos)
                    self.range_mode(x, y)


if __name__ == "__main__":
    root = tk.Tk()
    viewer = ImageViewer(root, screen_size=(800, 600))
    viewer.pygame_loop()
