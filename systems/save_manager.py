import json
from pathlib import Path


class SaveManager:  # 진행 데이터를 JSON 파일로 저장하고 불러오기
    """플레이어 진행 상황을 JSON 파일로 저장/불러오기."""
    def __init__(self, path="solosat_save.json"):  # 저장 파일 위치를 설정
        self.path = Path(path)  # 저장 경로 객체

    def save(self, data):  # 전달받은 데이터를 JSON 파일에 기록
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self):  # 저장 파일을 읽어 데이터로 반환
        if not self.path.exists():  # 저장 파일이 없으면 불러올 데이터가 없음
            return None
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):  # 파일 읽기 또는 JSON 해석 실패를 처리
            return None
