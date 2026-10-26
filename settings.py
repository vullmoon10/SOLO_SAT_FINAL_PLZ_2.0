import pygame
import os

WIDTH, HEIGHT, FPS = 1000, 600, 60  # 화면 크기와 목표 초당 프레임 수
TITLE = "SOLO SAT"  # 창 제목
MOVE_SPEED, GRAVITY, JUMP_POWER, MAX_FALL_SPEED = 5, 0.5, -10, 10  # 이동·중력·점프 물리값
MAX_HP, CORRECT_SCORE, WRONG_DAMAGE, QUESTION_TIME = 100, 100, 10, 30  # 체력·점수·피해·문제 제한 시간
SKY = (126, 196, 235)  # 하늘색
MOUNTAIN = (150, 176, 196)  # 산 배경색
GRASS = (81, 170, 89)  # 풀 색상
PLATFORM_COLOR = (112, 133, 92)  # 발판 색상
DIRT = (132, 86, 53)  # 흙 색상
BLUE = (65, 75, 225)  # 플레이어 색상
RED = (210, 65, 65)  # 위험·체력 UI 색상
WHITE = (255, 255, 255)  # 기본 흰색
DARK = (39, 54, 67)  # 기본 어두운 글자색
CREAM = (250, 249, 239)  # 퀴즈 패널 배경색
GRAY = (232, 232, 240)  # 선택지 기본 배경색
YELLOW = (255, 220, 70)  # 강조 색상
GROUND_Y = 520  # 지면의 화면 세로 좌표

pygame.font.init()
FONT = pygame.font.SysFont("malgungothic", 22)  # 기본 글꼴
SMALL = pygame.font.SysFont("malgungothic", 16)  # 작은 UI 글꼴
TITLE_FONT = pygame.font.SysFont("malgungothic", 27)  # 제목 글꼴
BIG = pygame.font.SysFont("malgungothic", 34)  # 큰 강조 글꼴


def choose_cheat(cheat_code=None):  # 환경 변수로 지정한 치트 설정을 반환
    """치트는 SOLO_SAT_CHEAT 환경변수로 선택한다. 기본값은 일반 모드."""
    cheats = {  # 번호별 치트 조합
        "1": {"no_damage": True},
        "2": {"superspeed": True},
        "3": {"superjump": True},
        "4": {"superspeed": True, "superjump": True},
        "5": {"no_damage": True, "superspeed": True, "superjump": True},
    }
    cheat_code = (cheat_code if cheat_code is not None else os.getenv("SOLO_SAT_CHEAT", "")).strip()
    return cheats.get(cheat_code, {})  # 유효한 번호의 치트 또는 빈 설정을 반환
