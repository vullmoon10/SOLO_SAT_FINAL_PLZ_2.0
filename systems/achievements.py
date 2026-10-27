"""게임 도전과제와 누적 진행도를 관리한다."""


ACHIEVEMENTS = (
    {"id": "first_coin", "title": "첫 보물", "description": "코인을 하나 획득한다.",
     "metric": "coins", "target": 1},
    {"id": "collector", "title": "아이템 수집가", "description": "아이템을 10개 획득한다.",
     "metric": "items", "target": 10},
    {"id": "full_set", "title": "풀 세트", "description": "서로 다른 아이템 4종을 모은다.",
     "metric": "item_types", "target": 4},
    {"id": "monster_hunter", "title": "몬스터 사냥꾼", "description": "몬스터를 10마리 처치한다.",
     "metric": "defeats", "target": 10},
    {"id": "energy_strike", "title": "에너지 충돌", "description": "역학적 에너지로 문제 몹을 처치한다.",
     "metric": "energy_kills", "target": 1},
    {"id": "high_score", "title": "고득점", "description": "한 판에서 1,000점을 달성한다.",
     "metric": "best_score", "target": 1000},
    {"id": "explorer", "title": "장거리 주행", "description": "누적 이동 거리 5,000px를 달성한다.",
     "metric": "distance", "target": 5000},
    {"id": "course_clear", "title": "코스 완주", "description": "월드의 도착 지점에 도달한다.",
     "metric": "course_clears", "target": 1},
)


def _nonnegative_int(value):
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError, OverflowError):
        return 0


class AchievementTracker:
    """도전과제 통계와 해금 상태를 저장 가능한 형태로 유지한다."""

    def __init__(self, data=None):
        data = data if isinstance(data, dict) else {}
        raw_stats = data.get("stats", {})
        raw_stats = raw_stats if isinstance(raw_stats, dict) else {}
        raw_item_types = raw_stats.get("item_types", [])
        raw_item_types = raw_item_types if isinstance(raw_item_types, (list, tuple, set)) else []
        self.stats = {
            "coins": _nonnegative_int(raw_stats.get("coins", 0)),
            "items": _nonnegative_int(raw_stats.get("items", 0)),
            "item_types": sorted(set(raw_item_types) & {"coin", "heart", "speed", "jump"}),
            "defeats": _nonnegative_int(raw_stats.get("defeats", 0)),
            "energy_kills": _nonnegative_int(raw_stats.get("energy_kills", 0)),
            "best_score": _nonnegative_int(raw_stats.get("best_score", 0)),
            "distance": _nonnegative_int(raw_stats.get("distance", 0)),
            "course_clears": _nonnegative_int(raw_stats.get("course_clears", 0)),
        }
        valid_ids = {item["id"] for item in ACHIEVEMENTS}
        raw_unlocked = data.get("unlocked", [])
        raw_unlocked = raw_unlocked if isinstance(raw_unlocked, (list, tuple, set)) else []
        self.unlocked = set(raw_unlocked) & valid_ids
        self._check()

    def update(self, metric, amount=1):
        if metric == "item_types":
            self.stats[metric] = sorted(set(self.stats[metric]) | {amount})
        elif metric == "best_score":
            self.stats[metric] = max(self.stats[metric], int(amount))
        elif metric in self.stats:
            self.stats[metric] += max(0, int(amount))
        return self._check()

    def _progress(self, achievement):
        value = self.stats[achievement["metric"]]
        return len(value) if isinstance(value, list) else value

    def _check(self):
        newly_unlocked = []
        for achievement in ACHIEVEMENTS:
            if (achievement["id"] not in self.unlocked
                    and self._progress(achievement) >= achievement["target"]):
                self.unlocked.add(achievement["id"])
                newly_unlocked.append(achievement)
        return newly_unlocked

    def export(self):
        return {"stats": self.stats.copy(), "unlocked": sorted(self.unlocked)}
