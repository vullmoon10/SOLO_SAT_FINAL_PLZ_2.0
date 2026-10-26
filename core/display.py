"""게임 창의 전체 화면 표시 상태를 전환한다."""

import pygame

from settings import WIDTH, HEIGHT


# 현재 창 모드를 반전하고 새 디스플레이 표면을 반환한다.
def toggle_fullscreen(screen):  # 전체 화면 상태를 반전해 화면을 다시 생성
    is_fullscreen = bool(screen.get_flags() & pygame.FULLSCREEN)  # 현재 전체 화면 여부
    # SCALED는 1000×600 논리 해상도를 유지하며 전체 화면 크기에 맞춰 표시한다.
    flags = 0 if is_fullscreen else pygame.FULLSCREEN | pygame.SCALED
    return pygame.display.set_mode((WIDTH, HEIGHT), flags)
