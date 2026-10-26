import json
import random
from io import BytesIO
from pathlib import Path

import pygame
from settings import WRONG_DAMAGE, QUESTION_TIME


_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "questions.json"
try:
    QUESTIONS = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    QUESTIONS = []

_REMOTE_QUESTIONS = []
_QUESTION_CLIENT = None
_SELECTED_SUBJECT = None
_IMAGE_CACHE = {}
_LOCAL_MODE = False
_LOCAL_DECK = []


def set_question_source(subject, client, questions, local_mode=False):
    global _REMOTE_QUESTIONS, _QUESTION_CLIENT, _SELECTED_SUBJECT, _IMAGE_CACHE, _LOCAL_MODE, _LOCAL_DECK
    _SELECTED_SUBJECT = subject
    _QUESTION_CLIENT = client
    _REMOTE_QUESTIONS = list(questions or [])
    _IMAGE_CACHE = {}
    _LOCAL_MODE = local_mode
    _LOCAL_DECK = []


def get_random_question(difficulty=None, subject=None):
    global _LOCAL_DECK
    subject = subject or _SELECTED_SUBJECT
    if _LOCAL_MODE:
        pool = [q for q in QUESTIONS if q.get("subject") == subject]
        if not pool:
            return {"subject": subject or "과목 미설정", "difficulty": "easy",
                    "q": "로컬 문항이 없습니다.", "choices": ["①", "②", "③", "④"],
                    "answer": 0, "time": QUESTION_TIME}
        if not _LOCAL_DECK:
            _LOCAL_DECK = list(pool)
            random.shuffle(_LOCAL_DECK)
        return dict(_LOCAL_DECK.pop())
    pool = [q for q in _REMOTE_QUESTIONS if not subject or q.get("subject") == subject]
    if pool:
        question = dict(random.choice(pool))
        question["time"] = int(question.get("time", QUESTION_TIME))
        question["difficulty"] = difficulty or "easy"
        question["_client"] = _QUESTION_CLIENT
        if _QUESTION_CLIENT and question.get("id"):
            qid = question["id"]
            if qid not in _IMAGE_CACHE:
                try:
                    _IMAGE_CACHE[qid] = _QUESTION_CLIENT.page_image(qid)
                except RuntimeError:
                    _IMAGE_CACHE[qid] = None
            question["page_image_bytes"] = _IMAGE_CACHE[qid]
        return question
    local = [q for q in QUESTIONS if (not subject or q.get("subject") == subject)
             and (difficulty is None or q.get("difficulty") == difficulty)]
    if not local:
        local = [q for q in QUESTIONS if not subject or q.get("subject") == subject]
    if local:
        return random.choice(local)
    return {"subject": subject or "과목 미설정", "difficulty": "easy",
            "q": "관리자 문항 등록을 기다리고 있습니다.", "choices": ["①", "②", "③", "④", "⑤"],
            "answer": 0, "time": QUESTION_TIME}


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
        if "answer" in question:
            correct = index == int(question["answer"])
        else:
            try:
                correct = question["_client"].check_answer(question["id"], index)
            except (KeyError, RuntimeError, AttributeError):
                correct = False
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
                    "enemy": enemy,
                    "defeated": False, "message": "시간 초과!"}
        return None


def image_surface(question):
    raw = question.get("page_image_bytes")
    if not raw:
        return None
    try:
        return pygame.image.load(BytesIO(raw)).convert()
    except (pygame.error, TypeError):
        return None
