"""게임 중 체력, 점수, 상태 메시지를 HUD로 표시한다."""

import pygame
from settings import HEIGHT, MAX_HP, RED, DARK, SMALL


def draw_hud(screen, hp, score, message):  # 화면에 체력·점수·조작 안내를 그리기
    pygame.draw.rect(screen, (75, 65, 65), (15, 14, 170, 14))
    pygame.draw.rect(screen, RED, (15, 14, int(170 * max(0, hp) / max(1, MAX_HP)), 14))
    screen.blit(SMALL.render(f"HP {hp}", True, DARK), (15, 32))
    screen.blit(SMALL.render(f"SCORE {score}", True, DARK), (15, 52))
    screen.blit(SMALL.render("A/D 이동  SPACE 점프  W/S 사다리", True, DARK), (15, HEIGHT - 25))
    # 알림 문구가 있을 때만 점수 옆에 추가 메시지를 표시한다.
    if message:  # 표시할 알림이 있으면 화면에 출력
        screen.blit(SMALL.render(message, True, DARK), (250, 25))
