"""Local-only player saves and rankings for single-computer play."""
import json
import time
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "runtime" / "local"


class LocalStorage:
    def __init__(self, data_dir=DATA_DIR):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.save_path = self.data_dir / "save.json"
        self.profile_path = self.data_dir / "profile.json"
        self.ranking_path = self.data_dir / "ranking.json"

    @staticmethod
    def _read(path, fallback):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return fallback

    def next_nickname(self):
        profile = self._read(self.profile_path, {"next_player_number": 1})
        number = max(1, int(profile.get("next_player_number", 1)))
        profile["next_player_number"] = number + 1
        self.profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        return f"player-{number}"

    def save(self, state):
        self.save_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self):
        return self._read(self.save_path, None)

    def clear_save(self):
        self.save_path.unlink(missing_ok=True)

    def record_score(self, nickname, score, subject):
        rows = self._read(self.ranking_path, [])
        rows.append({"nickname": nickname, "score": max(0, int(score)), "subject": subject, "played_at": time.time()})
        rows.sort(key=lambda row: (-row["score"], row["played_at"]))
        self.ranking_path.write_text(json.dumps(rows[:100], ensure_ascii=False, indent=2), encoding="utf-8")

    def leaderboard(self):
        return self._read(self.ranking_path, [])[:25]
