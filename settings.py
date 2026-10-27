"""게임 화면, 물리, 색상, 난이도 설정과 공용 폰트를 정의한다."""

import pygame
import os
import random

WIDTH, HEIGHT, FPS = 1000, 600, 60  # 화면 크기와 목표 초당 프레임 수
TITLE = "SOLO SAT"  # 창 제목
MOVE_SPEED, GRAVITY, JUMP_POWER = 5, 0.5, -10  # 이동·중력·점프 물리값


def random_physics():
    """월드 시드와 별개로 한 판에 적용할 제한된 물리값을 고른다."""
    rng = random.SystemRandom()
    return {
        "move_speed": round(rng.uniform(4.5, 5.5), 2),
        "gravity": round(rng.uniform(0.45, 0.55), 2),
        "jump_power": round(rng.uniform(-10.5, -9.5), 2),
    }
PLAYER_WIDTH, PLAYER_HEIGHT = 32, 40  # 플레이어 충돌 상자의 너비와 높이
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
SPAWN_SAFE_END = 700  # 시작 구간에 가시·발판 몬스터를 배치하지 않는 월드 좌표

pygame.font.init()
FONT = pygame.font.SysFont("malgungothic", 22)  # 기본 글꼴
SMALL = pygame.font.SysFont("malgungothic", 16)  # 작은 UI 글꼴
TITLE_FONT = pygame.font.SysFont("malgungothic", 27)  # 제목 글꼴
BIG = pygame.font.SysFont("malgungothic", 34)  # 큰 강조 글꼴


def choose_cheat(cheat_code=None):  # 환경 변수로 지정한 치트 설정을 반환
    """치트는 SOLO_SAT_CHEAT 환경변수로 선택한다. 기본값은 일반 모드."""
    cheats = {  # 번호별 치트 조합
        "1": {"Damage = 0": True},
        "2": {"Hyper ΔX": True},
        "3": {"Hyper ΔY": True},
        "4": {"Hyper Δ√(X²+Y²)": True},
        "5": {"ULTIMATE": True},
    }
    cheat_code = (cheat_code if cheat_code is not None else os.getenv("SOLO_SAT_CHEAT", "")).strip()
    selected = cheats.get(cheat_code, {})
    # 표시 이름은 유지하면서 게임 로직에서 사용하는 내부 키로 변환한다.
    aliases = {
        "Damage = 0": "no_damage",
        "Hyper ΔX": "superspeed",
        "Hyper ΔY": "superjump",
        "Hyper Δ√(X²+Y²)": ("superspeed", "superjump"),
        "ULTIMATE": ("no_damage", "superspeed", "superjump"),
    }
    normalized = {}
    for name, enabled in selected.items():
        internal_names = aliases.get(name, name)
        if isinstance(internal_names, tuple):
            normalized.update({internal_name: enabled for internal_name in internal_names})
        else:
            normalized[internal_names] = enabled
    return normalized  # 유효한 번호의 치트 또는 빈 설정을 반환
