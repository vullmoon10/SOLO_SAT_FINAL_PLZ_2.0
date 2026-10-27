"""새 게임 월드에 사용할 숫자 시드를 입력받는다."""

import pygame

from settings import WIDTH, HEIGHT, SKY, DARK, WHITE
from core.display import toggle_fullscreen


def get_world_seed(screen, audio=None):
    """숫자 시드를 입력받고 Enter로 확정한다. 비우면 무작위 시드를 쓴다."""
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("malgungothic", 28)
    small = pygame.font.SysFont("malgungothic", 18)
    value = ""
    pygame.key.start_text_input()
    try:
        while True:
            clock.tick(60)
            for event in pygame.event.get():
                if audio and audio.handle_music_event(event):
                    continue
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        screen = toggle_fullscreen(screen)
                    elif event.key == pygame.K_ESCAPE:
                        return False
                    elif event.key == pygame.K_BACKSPACE:
                        value = value[:-1]
                    elif event.key == pygame.K_RETURN:
                        return int(value) if value else None
                elif event.type == pygame.TEXTINPUT:
                    digits = "".join(char for char in event.text if char.isdecimal())
                    value = (value + digits)[:20]

            screen.fill(SKY)
            panel = pygame.Rect(WIDTH // 2 - 280, HEIGHT // 2 - 120, 560, 240)
            pygame.draw.rect(screen, (250, 249, 239), panel, border_radius=16)
            pygame.draw.rect(screen, DARK, panel, 3, border_radius=16)
            title = font.render("월드 시드", True, DARK)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, panel.y + 52)))
            field = pygame.Rect(panel.x + 55, panel.y + 95, panel.width - 110, 48)
            pygame.draw.rect(screen, WHITE, field, border_radius=6)
            pygame.draw.rect(screen, DARK, field, 2, border_radius=6)
            shown_value = value or "숫자를 입력하세요"
            color = DARK if value else (135, 145, 155)
            rendered_value = font.render(shown_value, True, color)
            screen.blit(rendered_value, rendered_value.get_rect(midleft=(field.x + 12, field.centery)))
            help_text = small.render("Enter 시작 · 비우면 무작위 시드 · ESC 취소", True, DARK)
            screen.blit(help_text, help_text.get_rect(center=(WIDTH // 2, panel.y + 180)))
            pygame.display.flip()
    finally:
        pygame.key.stop_text_input()
