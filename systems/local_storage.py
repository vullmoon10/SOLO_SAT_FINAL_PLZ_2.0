"""로컬 프로필, 저장 진행 상태, 랭킹 데이터를 초기화하고 관리한다."""
import json
import re
import time
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "runtime" / "local"
DEFAULT_PROFILE = {"next_player_number": 1}


class LocalStorage:
    def __init__(self, data_dir=DATA_DIR):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.save_path = self.data_dir / "save.json"
        self.profile_path = self.data_dir / "profile.json"
        self.ranking_path = self.data_dir / "ranking.json"
        self._initialize_files()

    @staticmethod
    def _write(path, value):
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)

    @staticmethod
    def _read(path, fallback):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return fallback

    @staticmethod
    def _has_valid_json(path):
        try:
            json.loads(path.read_text(encoding="utf-8"))
            return True
        except (OSError, json.JSONDecodeError):
            return False

    @staticmethod
    def _valid_score(row):
        return (isinstance(row, dict)
                and isinstance(row.get("nickname"), str) and bool(row["nickname"].strip())
                and isinstance(row.get("subject"), str) and bool(row["subject"].strip())
                and isinstance(row.get("score"), int) and row["score"] >= 0)

    def _clean_rankings(self, rows):
        best_by_player = {}
        for row in rows if isinstance(rows, list) else []:
            if not self._valid_score(row):
                continue
            try:
                played_at = float(row.get("played_at", 0) or 0)
            except (TypeError, ValueError, OverflowError):
                played_at = 0.0
            normalized = {"nickname": row["nickname"].strip()[:24], "score": row["score"],
                          "subject": row["subject"].strip(), "played_at": played_at}
            key = (normalized["nickname"].casefold(), normalized["subject"].casefold())
            current = best_by_player.get(key)
            if current is None or (normalized["score"], normalized["played_at"]) > (current["score"], current["played_at"]):
                best_by_player[key] = normalized
        return sorted(best_by_player.values(), key=lambda row: (-row["score"], row["played_at"]))[:100]

    def _initialize_files(self):
        profile = self._read(self.profile_path, DEFAULT_PROFILE.copy())
        profile_valid = self._has_valid_json(self.profile_path) and isinstance(profile, dict)
        if not profile_valid:
            profile = DEFAULT_PROFILE.copy()
            self._write(self.profile_path, profile)

        raw_rankings = self._read(self.ranking_path, [])
        rankings_valid = self._has_valid_json(self.ranking_path) and isinstance(raw_rankings, list)
        rankings = self._clean_rankings(raw_rankings)
        if not rankings_valid or rankings != raw_rankings:
            self._write(self.ranking_path, rankings)

        save = self._read(self.save_path, None)
        save_valid = self._has_valid_json(self.save_path)
        if not save_valid or (save is not None and not isinstance(save, dict)):
            save = None
            self._write(self.save_path, save)

        try:
            next_number = max(1, int(profile.get("next_player_number", 1)))
        except (TypeError, ValueError):
            next_number = 1
        for row in rankings:
            match = re.fullmatch(r"player-(\d+)", row["nickname"], re.IGNORECASE)
            if match:
                next_number = max(next_number, int(match.group(1)) + 1)
        if isinstance(save, dict):
            match = re.fullmatch(r"player-(\d+)", str(save.get("nickname", "")), re.IGNORECASE)
            if match:
                next_number = max(next_number, int(match.group(1)) + 1)
        normalized_profile = {**profile, "next_player_number": next_number}
        if normalized_profile != profile or not self.profile_path.exists():
            self._write(self.profile_path, normalized_profile)

    def next_nickname(self):
        profile = self._read(self.profile_path, DEFAULT_PROFILE.copy())
        try:
            number = max(1, int(profile.get("next_player_number", 1)))
        except (AttributeError, TypeError, ValueError):
            number = 1
        profile = profile if isinstance(profile, dict) else {}
        profile["next_player_number"] = number + 1
        self._write(self.profile_path, profile)
        return f"player-{number}"

    def save(self, state):
        if not isinstance(state, dict):
            raise TypeError("save state must be a dictionary")
        self._write(self.save_path, state)

    def load(self):
        state = self._read(self.save_path, None)
        return state if isinstance(state, dict) else None

    def clear_save(self):
        self._write(self.save_path, None)

    def record_score(self, nickname, score, subject):
        nickname = (nickname or "player-1").strip()[:24] or "player-1"
        subject = (subject or "수학").strip() or "수학"
        played_at = time.time()
        rows = self._clean_rankings(self._read(self.ranking_path, []))
        key = (nickname.casefold(), subject.casefold())
        existing = next((row for row in rows
                         if (row["nickname"].casefold(), row["subject"].casefold()) == key), None)
        score = max(0, int(score))
        if existing is None:
            rows.append({"nickname": nickname, "score": score, "subject": subject, "played_at": played_at})
        elif score >= existing["score"]:
            existing.update(nickname=nickname, score=score, subject=subject, played_at=played_at)
        self._write(self.ranking_path, self._clean_rankings(rows))

    def leaderboard(self):
        rows = self._clean_rankings(self._read(self.ranking_path, []))
        return rows[:25]
