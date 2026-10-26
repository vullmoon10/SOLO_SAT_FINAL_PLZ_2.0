"""난이도·영역별 몹 정보를 정의하고 몹의 문제와 체력을 관리한다."""

import pygame

from systems.quiz import get_random_question


ENEMY_TYPES = {
    "easy_arithmetic": {"name": "계산 슬라임", "difficulty": "easy", "domain": "산술",
                        "mark": "＋", "sprite_index": 0, "color": (219, 79, 77),
                        "size": (36, 42), "wrong_sound": "mob2_wrong", "hp": 2, "score": 100},
    "easy_fraction": {"name": "분수 유령", "difficulty": "easy", "domain": "분수",
                      "mark": "½", "sprite_index": 1, "color": (87, 156, 220),
                      "size": (36, 48), "wrong_sound": "mob2_wrong", "hp": 2, "score": 100},
    "easy_measurement": {"name": "도형 골렘", "difficulty": "easy", "domain": "측정·도형",
                         "mark": "□", "sprite_index": 2, "color": (77, 164, 111),
                         "size": (40, 44), "wrong_sound": "mob2_wrong", "hp": 2, "score": 100},
    "medium_numbers": {"name": "정수 박쥐", "difficulty": "medium", "domain": "수와 연산",
                       "mark": "±", "sprite_index": 0, "color": (135, 105, 194),
                       "size": (38, 46), "wrong_sound": "mob1_wrong", "hp": 3, "score": 200},
    "medium_algebra": {"name": "문자 마도사", "difficulty": "medium", "domain": "문자와 식",
                       "mark": "x", "sprite_index": 1, "color": (213, 139, 53),
                       "size": (34, 53), "wrong_sound": "mob1_wrong", "hp": 3, "score": 200},
    "medium_coordinate": {"name": "좌표 정찰병", "difficulty": "medium", "domain": "좌표",
                          "mark": "xy", "sprite_index": 3, "color": (48, 163, 166),
                          "size": (38, 48), "wrong_sound": "mob1_wrong", "hp": 3, "score": 200},
    "hard_numbers": {"name": "부호 기사", "difficulty": "hard", "domain": "수와 연산",
                     "mark": "±", "sprite_index": 0, "color": (190, 60, 78),
                     "size": (40, 54), "wrong_sound": "mob1_wrong", "hp": 4, "score": 300},
    "hard_algebra": {"name": "방정식 군주", "difficulty": "hard", "domain": "문자와 식",
                     "mark": "x", "sprite_index": 2, "color": (113, 76, 181),
                     "size": (42, 58), "wrong_sound": "mob1_wrong", "hp": 4, "score": 300},
    "hard_coordinate": {"name": "사분면 수호자", "difficulty": "hard", "domain": "좌표",
                        "mark": "xy", "sprite_index": 3, "color": (43, 134, 177),
                        "size": (42, 56), "wrong_sound": "mob1_wrong", "hp": 4, "score": 300},
    "expert_numbers": {"name": "연산 집행자", "difficulty": "expert", "domain": "수와 연산",
                       "mark": "±", "sprite_index": 1, "color": (174, 53, 81),
                       "size": (46, 60), "wrong_sound": "mob1_wrong", "hp": 5, "score": 400},
    "expert_algebra": {"name": "식의 지배자", "difficulty": "expert", "domain": "문자와 식",
                       "mark": "x", "sprite_index": 2, "color": (105, 64, 164),
                       "size": (46, 62), "wrong_sound": "mob1_wrong", "hp": 5, "score": 400},
    "expert_coordinate": {"name": "좌표 대마도사", "difficulty": "expert", "domain": "좌표",
                          "mark": "xy", "sprite_index": 3, "color": (30, 123, 160),
                          "size": (46, 62), "wrong_sound": "mob1_wrong", "hp": 5, "score": 400},
}

ENEMY_TYPES_BY_DIFFICULTY = {
    level: [key for key, data in ENEMY_TYPES.items() if data["difficulty"] == level]
    for level in ("easy", "medium", "hard", "expert")
}

# mob.jpg is split into four sprites; keep its visual progression aligned
# with the four question difficulty tiers.
DIFFICULTY_SPRITE_INDEX = {
    "easy": 0,
    "medium": 1,
    "hard": 2,
    "expert": 3,
}


class Enemy:
    def __init__(self, x, ground_y, enemy_type="easy_arithmetic"):
        self.enemy_type = enemy_type
        self.data = ENEMY_TYPES[enemy_type].copy()
        self.data["sprite_index"] = DIFFICULTY_SPRITE_INDEX[self.data["difficulty"]]
        width, height = self.data["size"]
        self.rect = pygame.Rect(x, ground_y - height, width, height)
        self.hp = self.data["hp"]
        self.active = True
        self.wrong_until = 0
        self.question = get_random_question(self.data["difficulty"], self.data["domain"])

    def defeat(self):
        self.hp -= 1
        if self.hp <= 0:
            self.active = False
            return True
        self.question = get_random_question(self.data["difficulty"], self.data["domain"])
        return False
