import pygame

from settings import WRONG_DAMAGE, QUESTION_TIME
from systems.question_generator import generate_math_question


def get_random_question(difficulty=None):
    return generate_math_question(difficulty)


class Quiz:
    def __init__(self, cheats=None):
        self.enemy = None
        self.started = 0
        self.duration = QUESTION_TIME
        self.selected = 0
        self.feedback = ""
        self.feedback_until = 0
        self.cheats = cheats or {}

    @property
    def active(self):
        return self.enemy is not None

    def open(self, enemy):
        if enemy.active:
            self.enemy = enemy
            self.started = pygame.time.get_ticks()
            self.duration = enemy.question.get("time", QUESTION_TIME)
            self.selected = 0

    def remaining(self):
        return max(0, self.duration - (pygame.time.get_ticks() - self.started) / 1000)

    def submit(self, index):
        if not self.active:
            return None
        question = self.enemy.question
        if not 0 <= index < len(question["choices"]):
            return None
        enemy = self.enemy
        correct = index == int(question["answer"])
        if correct:
            score = enemy.data["score"]
            result = {"correct": True, "damage": 0, "score": score,
                      "defeated": enemy.defeat(), "message": f"정답! +{score}점"}
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
