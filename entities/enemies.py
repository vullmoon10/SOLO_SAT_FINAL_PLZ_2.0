import pygame
from systems.quiz import get_random_question

ENEMY_TYPES = {  # 적 종류별 외형·난이도·보상 설정
    "basic": {"color": (210, 65, 65), "size": (35, 58), "difficulty": "easy",
              "sprite": "mob11.jpg", "wrong_sound": "mob2_wrong", "hp": 2, "score": 100},
    "advanced": {"color": (130, 90, 65), "size": (29, 58), "difficulty": "medium",
                 "sprite": "mob2.jpg", "wrong_sound": "mob1_wrong", "hp": 4, "score": 200},
    "challenge": {"color": (94, 69, 150), "size": (27, 62), "difficulty": "hard",
                  "sprite": "mob2.jpg", "wrong_sound": "mob1_wrong", "hp": 5, "score": 300},
}


class Enemy:  # 퀴즈로 처치하는 적의 상태를 관리
    def __init__(self, x, ground_y, enemy_type="basic"):  # 위치와 종류에 맞춰 적을 초기화
        self.enemy_type = enemy_type  # 적 종류 식별자
        self.data = ENEMY_TYPES[enemy_type]  # 종류별 적 설정
        width, height = self.data["size"]  # 적의 가로·세로 크기
        self.rect = pygame.Rect(x, ground_y - height, width, height)  # 적의 위치와 충돌 영역
        self.hp = self.data["hp"]  # 적의 남은 체력
        self.active = True
        self.wrong_until = 0  # 적 생존 여부
        self.question = get_random_question(self.data["difficulty"])  # 적 난이도에 맞는 첫 문제

    def defeat(self):  # 정답 처리로 적의 체력을 줄이고 처치 여부를 반환
        self.hp -= 1  # 정답 시 적 체력 1 감소
        if self.hp <= 0:  # 체력이 0 이하이면 적을 비활성화
            self.active = False  # 체력이 소진된 적을 비활성화
            return True
        self.question = get_random_question(self.data["difficulty"])  # 남은 체력에 도전할 새 문제
        return False
