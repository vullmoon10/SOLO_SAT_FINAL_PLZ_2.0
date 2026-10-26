from pathlib import Path
import math

import pygame
from settings import *
from ui.hud import draw_hud


class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.enemy_sprites = self._load_enemy_sprites()
        self.alert_font = pygame.font.SysFont("malgungothic", 22, bold=True)
        self.enemy_mark_font = pygame.font.SysFont("malgungothic", 10, bold=True)

    @staticmethod
    def _load_enemy_sprites():
        image_dir = Path(__file__).resolve().parents[1] / "assets" / "images"
        sprites = []
        for index in range(1, 5):
            image_path = image_dir / f"mob_{index}.png"
            try:
                sprites.append(pygame.image.load(str(image_path)).convert_alpha())
            except (pygame.error, OSError):
                break
        return sprites

    def draw_text(self, text, x, y, color=DARK, font=FONT):
        self.screen.blit(font.render(str(text), True, color), (x, y))

    def draw_background(self, camera_x):
        self.screen.fill(SKY)
        for i in range(-1, 7):
            x = i * 260 - int(camera_x) % 260
            pygame.draw.polygon(self.screen, MOUNTAIN, [(x, 520), (x + 125, 360 + (i % 3) * 30), (x + 260, 520)])
        cloud_offset = int(pygame.time.get_ticks() * 0.025)
        for i in range(6):
            x = (i * 210 - cloud_offset) % (WIDTH + 180) - 80
            y = 90 + (i % 3) * 55
            for cx, cy, radius in [(x, y, 17), (x + 20, y - 8, 20), (x + 40, y, 15)]:
                pygame.draw.circle(self.screen, WHITE, (cx, cy), radius)

    def draw_world(self, world, camera_x):
        for collection, fill, accent in ((world.ground_segments, DIRT, GRASS), (world.platforms, PLATFORM_COLOR, GRASS)):
            for segment in collection:
                rect = segment.move(-camera_x, 0)
                if rect.right >= 0 and rect.left <= WIDTH:
                    pygame.draw.rect(self.screen, fill, rect)
                    pygame.draw.rect(self.screen, accent, (rect.x, rect.y, rect.width, 7))
        for ladder in world.ladders:
            rect = ladder.move(-camera_x, 0)
            if rect.right < 0 or rect.left > WIDTH:
                continue
            pygame.draw.line(self.screen, (180, 100, 55), rect.topleft, (rect.left, rect.bottom), 3)
            pygame.draw.line(self.screen, (180, 100, 55), (rect.right, rect.top), (rect.right, rect.bottom), 3)
            for y in range(rect.top + 8, rect.bottom, 13):
                pygame.draw.line(self.screen, (180, 100, 55), (rect.left, y), (rect.right, y), 3)
        for item in world.decorations:
            rect = item.move(-camera_x, 0)
            if rect.right >= 0 and rect.left <= WIDTH:
                pygame.draw.rect(self.screen, DIRT, rect)
                pygame.draw.rect(self.screen, (91, 57, 36), rect, 2)
        for spike in world.spikes:
            x, y = spike["x"] - camera_x, spike["y"]
            for i in range(spike["count"]):
                sx = x + i * 13
                pygame.draw.polygon(self.screen, (220, 45, 65), [(sx, y), (sx + 7, y - 15), (sx + 13, y)])
        for enemy in world.enemies:
            if not enemy.active:
                continue
            rect = enemy.rect.move(-camera_x, 0)
            if rect.right < 0 or rect.left > WIDTH:
                continue
            phase = pygame.time.get_ticks() * 0.004 + enemy.rect.x * 0.035
            bob = math.sin(phase) * 2.5
            stretch = 1.0 + math.sin(phase * 2) * 0.035
            sprite_index = enemy.data["sprite_index"]
            if sprite_index < len(self.enemy_sprites):
                source = self.enemy_sprites[sprite_index]
                fit = min(rect.width / source.get_width(), rect.height / source.get_height())
                sprite_width = max(1, round(source.get_width() * fit))
                sprite_height = max(1, round(source.get_height() * fit * stretch))
                animated = pygame.transform.scale(source, (sprite_width, sprite_height))
                badge = pygame.Surface((sprite_width, sprite_height), pygame.SRCALPHA)
                badge_y = int(sprite_height * .72)
                pygame.draw.circle(badge, enemy.data["color"], (sprite_width // 2, badge_y), 8)
                pygame.draw.circle(badge, DARK, (sprite_width // 2, badge_y), 8, 1)
                mark = self.enemy_mark_font.render(enemy.data["mark"], True, WHITE)
                badge.blit(mark, mark.get_rect(center=(sprite_width // 2, badge_y)))
                animated.blit(badge, (0, 0))
            else:
                animated = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                pygame.draw.ellipse(animated, enemy.data["color"], animated.get_rect())
                pygame.draw.ellipse(animated, DARK, animated.get_rect(), 2)
            animated = pygame.transform.rotozoom(animated, math.sin(phase) * 3, 1)
            animated_rect = animated.get_rect(center=(rect.centerx, int(rect.centery + bob)))
            self.screen.blit(animated, animated_rect)
            if enemy.wrong_until > pygame.time.get_ticks():
                alert = self.alert_font.render("!", True, WHITE)
                pygame.draw.circle(self.screen, (220, 45, 65), (rect.centerx, rect.top - 5), 11)
                self.screen.blit(alert, alert.get_rect(center=(rect.centerx, rect.top - 6)))

    def draw_start_countdown(self, seconds):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 15, 25, 175))
        self.screen.blit(overlay, (0, 0))
        title = TITLE_FONT.render("게임 시작", True, WHITE)
        number = pygame.font.SysFont("malgungothic", 110, bold=True).render(str(seconds), True, YELLOW)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 75)))
        self.screen.blit(number, number.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40)))

    def draw_pause_overlay(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 15, 25, 175))
        self.screen.blit(overlay, (0, 0))
        label = TITLE_FONT.render("PAUSED · ESC로 계속", True, WHITE)
        self.screen.blit(label, label.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

    def draw_player(self, player, camera_x, rotation=0):
        rect = player.rect.move(-camera_x, 0)
        sprite = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(sprite, BLUE, sprite.get_rect(), border_radius=3)
        pygame.draw.rect(sprite, (40, 45, 150), sprite.get_rect(), 2, border_radius=3)
        if rotation:
            sprite = pygame.transform.rotate(sprite, rotation)
        self.screen.blit(sprite, sprite.get_rect(center=rect.center))

    def draw_hud(self, hp, score, message):
        draw_hud(self.screen, hp, score, message)

    def _pixel_text(self, text, color, scale=2, size=12):
        font = pygame.font.SysFont("monospace", size, bold=True)
        glyphs = font.render(str(text), False, color)
        return pygame.transform.scale(glyphs, (glyphs.get_width() * scale, glyphs.get_height() * scale))

    def draw_game_over(self, score):
        tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        tint.fill((205, 15, 25, 120))
        self.screen.blit(tint, (0, 0))

        title = self._pixel_text("GAME OVER", (28, 12, 16), scale=3, size=17)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, int(HEIGHT * 0.28))))

        label = self._pixel_text("Score:", (28, 12, 16), scale=2, size=13)
        value = self._pixel_text(str(score), (255, 224, 55), scale=3, size=16)
        gap = 12
        total_width = label.get_width() + gap + value.get_width()
        left = (WIDTH - total_width) // 2
        y = int(HEIGHT * 0.44)
        self.screen.blit(label, (left, y + (value.get_height() - label.get_height()) // 2))
        self.screen.blit(value, (left + label.get_width() + gap, y))

        instruction = self._pixel_text("ESC: TITLE SCREEN", (35, 10, 12), scale=2, size=9)
        self.screen.blit(instruction, instruction.get_rect(center=(WIDTH // 2, int(HEIGHT * 0.78))))

    def draw_quiz(self, quiz):
        if not quiz.active:
            return
        q = quiz.enemy.question
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((20, 30, 45, 205))
        self.screen.blit(overlay, (0, 0))
        panel = pygame.Rect(25, 28, WIDTH - 50, HEIGHT - 56)
        pygame.draw.rect(self.screen, CREAM, panel, border_radius=8)
        level_name = {"easy": "쉬움", "medium": "보통", "hard": "도전", "expert": "최상"}.get(q.get("difficulty"), "수학")
        self.draw_text(f"{quiz.enemy.data['name']} · {q.get('domain', '수학')} · {level_name}",
                       45, 40, GRASS, SMALL)
        self.draw_text(q.get("q", ""), 45, 65, DARK, FONT)
        remaining = quiz.remaining()
        self.draw_text(f"{remaining:.1f}s", 905, 40, RED if remaining < 10 else DARK, SMALL)
        bar = pygame.Rect(45, 96, WIDTH - 90, 7)
        pygame.draw.rect(self.screen, GRAY, bar)
        ratio = remaining / max(1, quiz.duration)
        pygame.draw.rect(self.screen, GRASS if ratio > .3 else (220, 130, 50), (bar.x, bar.y, int(bar.width * ratio), bar.height))

        choices = q.get("choices", [])
        left, width, top, row_h = 45, WIDTH - 90, 125, min(70, 380 // max(1, len(choices)))
        for i, choice in enumerate(choices):
            option = pygame.Rect(left, top + i * row_h, width, row_h - 8)
            selected = i == quiz.selected
            pygame.draw.rect(self.screen, (190, 220, 255) if selected else GRAY, option, border_radius=5)
            if selected:
                pygame.draw.rect(self.screen, (55, 110, 220), option, 2, border_radius=5)
            label = str(choice)
            self.draw_text(f"{i + 1}. {label}", option.x + 12, option.y + 8, DARK, SMALL)
        self.draw_text("↑/↓ 선택 · 1~4 또는 Enter 제출 · ESC 닫기", 45, 545, DARK, SMALL)
