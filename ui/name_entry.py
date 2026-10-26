"""새 게임을 시작하기 전에 플레이어 이름을 게임 창에서 입력받는다."""

import pygame

from settings import WIDTH, HEIGHT, SKY, DARK, WHITE
from core.display import toggle_fullscreen


def get_player_name(screen, audio=None):
    """게임 창에서 이름을 입력받고 Enter로 확정한다."""
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("malgungothic", 28)
    small = pygame.font.SysFont("malgungothic", 18)
    name = ""
    pygame.key.start_text_input()
    try:
        while True:
            clock.tick(60)
            for event in pygame.event.get():
                if audio and audio.handle_music_event(event):
                    continue
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        screen = toggle_fullscreen(screen)
                    elif event.key == pygame.K_ESCAPE:
                        return ""
                    elif event.key == pygame.K_BACKSPACE:
                        name = name[:-1]
                    elif event.key == pygame.K_RETURN:
                        return name.strip()
                elif event.type == pygame.TEXTINPUT:
                    name = (name + event.text)[:24]

            screen.fill(SKY)
            panel = pygame.Rect(WIDTH // 2 - 280, HEIGHT // 2 - 120, 560, 240)
            pygame.draw.rect(screen, (250, 249, 239), panel, border_radius=16)
            pygame.draw.rect(screen, DARK, panel, 3, border_radius=16)
            title = font.render("플레이어 이름", True, DARK)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, panel.y + 52)))
            field = pygame.Rect(panel.x + 55, panel.y + 95, panel.width - 110, 48)
            pygame.draw.rect(screen, WHITE, field, border_radius=6)
            pygame.draw.rect(screen, DARK, field, 2, border_radius=6)
            shown_name = name or "이름을 입력하세요"
            color = DARK if name else (135, 145, 155)
            value = font.render(shown_name, True, color)
            screen.blit(value, value.get_rect(midleft=(field.x + 12, field.centery)))
            help_text = small.render("Enter 시작 · 비우면 자동 이름 · ESC 건너뛰기", True, DARK)
            screen.blit(help_text, help_text.get_rect(center=(WIDTH // 2, panel.y + 180)))
            pygame.display.flip()
    finally:
        pygame.key.stop_text_input()
