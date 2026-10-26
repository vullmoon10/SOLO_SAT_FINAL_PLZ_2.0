"""게임 창의 전체 화면 표시 상태를 전환한다."""

import pygame

from settings import WIDTH, HEIGHT


def toggle_fullscreen(screen):  # 전체 화면 상태를 반전해 화면을 다시 생성
    is_fullscreen = bool(screen.get_flags() & pygame.FULLSCREEN)  # 현재 전체 화면 여부
    flags = 0 if is_fullscreen else pygame.FULLSCREEN  # 전환할 디스플레이 옵션
    return pygame.display.set_mode((WIDTH, HEIGHT), flags)
