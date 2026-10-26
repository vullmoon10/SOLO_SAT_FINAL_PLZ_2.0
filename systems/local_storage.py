"""로컬 프로필, 저장 진행 상태, 랭킹 데이터를 초기화하고 관리한다."""
import json
import re
import time
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "runtime" / "local"
DEFAULT_PROFILE = {"next_player_number": 1}


# 로컬 JSON 파일 세 개의 생성, 정리, 저장과 조회를 담당한다.
class LocalStorage:
    # 저장 디렉터리를 만들고 초기 데이터 파일을 정규화한다.
    def __init__(self, data_dir=DATA_DIR):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.save_path = self.data_dir / "save.json"
        self.profile_path = self.data_dir / "profile.json"
        self.ranking_path = self.data_dir / "ranking.json"
        self._initialize_files()

    @staticmethod
    # JSON을 임시 파일에 쓴 뒤 교체해 저장 중 손상을 줄인다.
    def _write(path, value):
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)

    @staticmethod
    # JSON 파일을 읽고 실패하면 호출자가 지정한 기본값을 돌려준다.
    def _read(path, fallback):
        # 파일을 읽고 JSON으로 해석한다.
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        # 파일이 없거나 형식이 잘못되면 기본값으로 복구한다.
        except (OSError, json.JSONDecodeError):
            return fallback

    @staticmethod
    # 파일 내용이 유효한 JSON인지 확인한다.
    def _has_valid_json(path):
        # 읽기와 JSON 해석이 성공하면 유효한 파일이다.
        try:
            json.loads(path.read_text(encoding="utf-8"))
            return True
        # 파일을 읽을 수 없거나 JSON이 깨졌으면 유효하지 않다.
        except (OSError, json.JSONDecodeError):
            return False

    @staticmethod
    # 랭킹 한 행에 닉네임·과목·점수 필수값이 있는지 검사한다.
    def _valid_score(row):
        return (isinstance(row, dict)
                and isinstance(row.get("nickname"), str) and bool(row["nickname"].strip())
                and isinstance(row.get("subject"), str) and bool(row["subject"].strip())
                and isinstance(row.get("score"), int) and row["score"] >= 0)

    # 잘못된 기록을 거르고 플레이어별 최고 점수만 남긴다.
    def _clean_rankings(self, rows):
        best_by_player = {}
        # 목록인 경우에만 각 랭킹 행을 검증하고 정리한다.
        for row in rows if isinstance(rows, list) else []:
            # 필수 필드가 빠진 기록은 랭킹에서 제외한다.
            if not self._valid_score(row):
                continue
            # 기록 시각이 숫자로 바뀌지 않으면 기본 시각을 적용한다.
            try:
                played_at = float(row.get("played_at", 0) or 0)
            # 시각 값이 숫자가 아니면 0으로 정규화한다.
            except (TypeError, ValueError, OverflowError):
                played_at = 0.0
            normalized = {"nickname": row["nickname"].strip()[:24], "score": row["score"],
                          "subject": row["subject"].strip(), "played_at": played_at}
            key = (normalized["nickname"].casefold(), normalized["subject"].casefold())
            current = best_by_player.get(key)
            # 같은 플레이어의 기존 기록보다 높은 점수만 새 최고 기록으로 저장한다.
            if current is None or (normalized["score"], normalized["played_at"]) > (current["score"], current["played_at"]):
                best_by_player[key] = normalized
        return sorted(best_by_player.values(), key=lambda row: (-row["score"], row["played_at"]))[:100]

    # 프로필·랭킹·저장 파일을 확인하고 누락·손상 데이터를 초기화한다.
    def _initialize_files(self):
        profile = self._read(self.profile_path, DEFAULT_PROFILE.copy())
        profile_valid = self._has_valid_json(self.profile_path) and isinstance(profile, dict)
        # 프로필이 없거나 JSON 객체가 아니면 기본 프로필을 만든다.
        if not profile_valid:
            profile = DEFAULT_PROFILE.copy()
            self._write(self.profile_path, profile)

        raw_rankings = self._read(self.ranking_path, [])
        rankings_valid = self._has_valid_json(self.ranking_path) and isinstance(raw_rankings, list)
        rankings = self._clean_rankings(raw_rankings)
        # 랭킹 파일이 잘못됐거나 정리 결과가 다르면 정규화 데이터를 쓴다.
        if not rankings_valid or rankings != raw_rankings:
            self._write(self.ranking_path, rankings)

        save = self._read(self.save_path, None)
        save_valid = self._has_valid_json(self.save_path)
        # 저장 상태 형식이 잘못됐으면 빈 저장 상태로 초기화한다.
        if not save_valid or (save is not None and not isinstance(save, dict)):
            save = None
            self._write(self.save_path, save)

        # 프로필 번호를 정수로 읽고 비정상 값은 1부터 다시 시작한다.
        try:
            next_number = max(1, int(profile.get("next_player_number", 1)))
        # 잘못된 번호는 기본값으로 복구한다.
        except (TypeError, ValueError):
            next_number = 1
        # 기존 랭킹에 사용된 가장 큰 플레이어 번호를 확인한다.
        for row in rankings:
            match = re.fullmatch(r"player-(\d+)", row["nickname"], re.IGNORECASE)
            # 자동 발급 닉네임이면 다음 번호를 기존 번호보다 크게 맞춘다.
            if match:
                next_number = max(next_number, int(match.group(1)) + 1)
        # 저장 데이터의 닉네임 번호도 다음 자동 번호에 반영한다.
        if isinstance(save, dict):
            match = re.fullmatch(r"player-(\d+)", str(save.get("nickname", "")), re.IGNORECASE)
            # 저장 닉네임 번호도 다음 자동 번호 후보에 반영한다.
            if match:
                next_number = max(next_number, int(match.group(1)) + 1)
        normalized_profile = {**profile, "next_player_number": next_number}
        # 다음 번호가 달라졌거나 프로필 파일이 없으면 갱신한다.
        if normalized_profile != profile or not self.profile_path.exists():
            self._write(self.profile_path, normalized_profile)

    # 중복되지 않는 player-N 형식의 닉네임을 발급하고 번호를 올린다.
    def next_nickname(self):
        profile = self._read(self.profile_path, DEFAULT_PROFILE.copy())
        # 저장된 다음 번호를 읽고 형식 오류면 기본 번호를 쓴다.
        try:
            number = max(1, int(profile.get("next_player_number", 1)))
        # 프로필 형식이 예상과 다르면 첫 번호부터 시작한다.
        except (AttributeError, TypeError, ValueError):
            number = 1
        profile = profile if isinstance(profile, dict) else {}
        profile["next_player_number"] = number + 1
        self._write(self.profile_path, profile)
        return f"player-{number}"

    # 새 진행 상태를 저장 파일에 기록한다.
    def save(self, state):
        # 저장 상태는 JSON 객체로만 허용한다.
        if not isinstance(state, dict):
            raise TypeError("save state must be a dictionary")
        self._write(self.save_path, state)

    # 저장 상태를 읽고 객체 형태인 경우에만 반환한다.
    def load(self):
        state = self._read(self.save_path, None)
        return state if isinstance(state, dict) else None

    # 이어 하기 데이터가 없도록 저장 파일을 비운다.
    def clear_save(self):
        self._write(self.save_path, None)

    # 점수를 플레이어별 최고 기록으로 갱신한다.
    def record_score(self, nickname, score, subject):
        nickname = (nickname or "player-1").strip()[:24] or "player-1"
        subject = (subject or "수학").strip() or "수학"
        played_at = time.time()
        rows = self._clean_rankings(self._read(self.ranking_path, []))
        key = (nickname.casefold(), subject.casefold())
        existing = next((row for row in rows
                         if (row["nickname"].casefold(), row["subject"].casefold()) == key), None)
        score = max(0, int(score))
        # 새 플레이어·과목 기록이면 랭킹에 행을 추가한다.
        if existing is None:
            rows.append({"nickname": nickname, "score": score, "subject": subject, "played_at": played_at})
        # 기존 점수 이상인 경우에만 해당 기록을 갱신한다.
        elif score >= existing["score"]:
            existing.update(nickname=nickname, score=score, subject=subject, played_at=played_at)
        self._write(self.ranking_path, self._clean_rankings(rows))

    # 정리한 랭킹 중 상위 25개 기록을 반환한다.
    def leaderboard(self):
        rows = self._clean_rankings(self._read(self.ranking_path, []))
        return rows[:25]
