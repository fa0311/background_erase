import os
import tkinter as tk
from tkinter import filedialog
from typing import List, Tuple

import pygame


class ImageSelector:
    def __init__(self, image_files: List[str]) -> None:
        self.current_index = 0
        self.image_files = image_files

    def current(self) -> str:
        return self.image_files[self.current_index]

    def next(self):
        self.current_index = (self.current_index + 1) % len(self.image_files)

    def previous(self):
        self.current_index = (self.current_index - 1) % len(self.image_files)


class ImageViewer:
    def __init__(self, root: tk.Tk, screen_size: Tuple[int, int]) -> None:
        self.root = root
        self.screen_size = screen_size

        # Tkinterウィジェットの設定
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(side=tk.TOP)

        self.fps_label = tk.Label(self.button_frame, text="FPS: 0")
        self.fps_label.pack(side=tk.LEFT, padx=5, pady=5)

        self.index_label = tk.Label(self.button_frame, text="Index: 0")
        self.index_label.pack(side=tk.LEFT, padx=5, pady=5)

        self.embed_pygame = tk.Frame(
            self.root, width=screen_size[0], height=screen_size[1]
        )
        self.embed_pygame.pack(side=tk.TOP)

        os.environ["SDL_WINDOWID"] = str(self.embed_pygame.winfo_id())
        os.environ["SDL_VIDEODRIVER"] = "windib"

        pygame.display.init()
        self.screen = pygame.display.set_mode(screen_size)
        pygame.display.set_caption("Pygame Image Viewer")

        self.image_files = ImageSelector(self.select_folder())
        self.load_image(self.image_files.current())

        self.next_button = tk.Button(
            self.button_frame,
            text="Next",
            command=self.next_image,
        )
        self.next_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.prev_button = tk.Button(
            self.button_frame,
            text="Previous",
            command=self.previous_image,
        )
        self.prev_button.pack(side=tk.LEFT, padx=5, pady=5)

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

    def load_image(self, image_path: str) -> None:
        """指定した画像を読み込み、スケールを画面に合わせる"""
        self.image = pygame.image.load(image_path).convert_alpha()
        self.image_rect = self.image.get_rect()
        self.fit_to_screen()

    def fit_to_screen(self) -> None:
        """画像を画面に合わせるスケーリングの初期化"""
        screen_w, screen_h = self.screen_size
        img_w, img_h = self.image_rect.size
        self.scale = min(screen_w / img_w, screen_h / img_h)
        self.image_rect.width = int(img_w * self.scale)
        self.image_rect.height = int(img_h * self.scale)
        self.image_rect.center = (screen_w // 2, screen_h // 2)

    def handle_events(self) -> None:
        """Pygameのイベントを処理"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                self.root.quit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.start_drag(event)
            elif event.type == pygame.MOUSEBUTTONUP:
                self.stop_drag()
            elif event.type == pygame.MOUSEMOTION:
                self.drag_image(event)
            elif event.type == pygame.MOUSEWHEEL:
                self.zoom_image(event)

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

        # 新しいスケールの画像位置を計算
        offset_x = (mouse_x - self.image_rect.x) * (scale_factor - 1)
        offset_y = (mouse_y - self.image_rect.y) * (scale_factor - 1)
        self.image_rect.x -= offset_x
        self.image_rect.y -= offset_y

        new_width = int(self.image.get_width() * self.scale)
        new_height = int(self.image.get_height() * self.scale)
        self.image_rect.size = (new_width, new_height)

    def next_image(self) -> None:
        """次の画像をロード"""
        self.image_files.next()
        self.load_image(self.image_files.current())

    def previous_image(self) -> None:
        """前の画像をロード"""
        self.image_files.previous()
        self.load_image(self.image_files.current())

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


if __name__ == "__main__":
    root = tk.Tk()
    viewer = ImageViewer(root, screen_size=(800, 600))
    viewer.pygame_loop()
