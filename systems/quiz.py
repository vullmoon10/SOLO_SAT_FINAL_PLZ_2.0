"""문제를 제공하고 퀴즈 진행, 답안 판정, 제한 시간을 관리한다."""

import pygame

from settings import WRONG_DAMAGE, QUESTION_TIME
from systems.question_generator import generate_math_question


# 요청한 난이도와 영역의 새 문제를 생성기에 요청한다.
def get_random_question(difficulty=None, domain=None):
    return generate_math_question(difficulty, domain)


# 몹과 연결된 한 문제의 선택, 제출, 시간 제한을 관리한다.
class Quiz:
    # 퀴즈의 초기 선택 상태와 치트 설정을 준비한다.
    def __init__(self, cheats=None):
        self.enemy = None
        self.started = 0
        self.duration = QUESTION_TIME
        self.selected = 0
        self.feedback = ""
        self.feedback_until = 0
        self.cheats = cheats or {}

    @property
    # 현재 문제를 풀 몹이 있는지 상태를 반환한다.
    def active(self):
        return self.enemy is not None

    # 살아 있는 몹의 문제와 제한 시간으로 퀴즈를 연다.
    def open(self, enemy):
        if enemy.active:
            self.enemy = enemy
            self.started = pygame.time.get_ticks()
            self.duration = enemy.question.get("time", QUESTION_TIME)
            self.selected = 0

    # 제한 시간에서 경과 시간을 빼 남은 초를 계산한다.
    def remaining(self):
        return max(0, self.duration - (pygame.time.get_ticks() - self.started) / 1000)

    # 선택 답을 채점하고 점수·피해·몹 상태 결과를 반환한다.
    def submit(self, index):
        # 진행 중인 문제가 없으면 답안을 처리하지 않는다.
        if not self.active:
            return None
        question = self.enemy.question
        # 선택 번호가 유효한 보기 범위에 있는지 검사한다.
        if not 0 <= index < len(question["choices"]):
            return None
        enemy = self.enemy
        correct = index == int(question["answer"])
        # 정답이면 점수를 주고 몹 체력을 감소시킨다.
        if correct:
            score = enemy.data["score"]
            result = {"correct": True, "damage": 0, "score": score,
                      "defeated": enemy.defeat(), "message": f"정답! +{score}점"}
        # 오답이면 무피해 치트를 반영해 피해 결과를 만든다.
        else:
            damage = 0 if self.cheats.get("no_damage") else WRONG_DAMAGE
            result = {"correct": False, "damage": damage, "score": 0, "defeated": False,
                      "wrong_sound": enemy.data.get("wrong_sound", "damage"),
                      "enemy": enemy,
                      "message": "오답! 피해 없음" if damage == 0 else f"오답! 체력 -{damage}"}
        self.feedback = result["message"]
        self.feedback_until = pygame.time.get_ticks() + 1000
        self.enemy = None
        return result

    # 시간이 끝난 문제를 오답 처리하고 시간 초과 결과를 반환한다.
    def check_timeout(self):
        if self.active and self.remaining() <= 0:
            enemy = self.enemy
            damage = 0 if self.cheats.get("no_damage") else WRONG_DAMAGE
            self.feedback = "시간 초과!"
            self.feedback_until = pygame.time.get_ticks() + 1000
            self.enemy = None
            return {"correct": False, "damage": damage, "score": 0,
                    "wrong_sound": enemy.data.get("wrong_sound", "damage"),
                    "enemy": enemy, "defeated": False, "message": "시간 초과!"}
        return None
