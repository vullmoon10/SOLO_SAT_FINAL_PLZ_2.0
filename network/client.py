"""HTTP client used by game stations on the booth LAN."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class BoothClient:
    def __init__(self, base_url=None, timeout=4):
        self.base_url = (base_url or os.environ.get("SOLO_SAT_SERVER", "http://127.0.0.1:8765")).rstrip("/")
        self.timeout = timeout
        self.admin_token = None

    def request(self, method, path, data=None, admin=False):
        headers = {"Content-Type": "application/json"}
        if admin and self.admin_token:
            headers["X-Admin-Token"] = self.admin_token
        body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
        req = Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            with urlopen(req, timeout=self.timeout) as response:
                raw = response.read()
                if "application/json" in response.headers.get("Content-Type", ""):
                    return json.loads(raw.decode("utf-8")) if raw else None
                return raw
        except HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode("utf-8")).get("error", str(exc))
            except (ValueError, AttributeError):
                detail = str(exc)
            raise RuntimeError(detail) from exc
        except (URLError, TimeoutError) as exc:
            raise RuntimeError("서버에 연결할 수 없습니다. 서버 주소와 LAN 연결을 확인하세요.") from exc

    def start_session(self, nickname, subject):
        result = self.request("POST", "/sessions/start", {"nickname": nickname, "subject": subject})
        result["subject"] = subject
        return result

    def questions(self, subject):
        from urllib.parse import quote
        return self.request("GET", "/questions?subject=" + quote(subject))

    def page_image(self, question_id):
        from urllib.parse import quote
        return self.request("GET", "/questions/" + quote(question_id) + "/page")

    def check_answer(self, question_id, choice):
        return self.request("POST", "/questions/answer", {"question_id": question_id, "choice": choice})["correct"]

    def save(self, player_id, state):
        return self.request("POST", "/sessions/save", {"player_id": player_id, "state": state})

    def load(self, player_id):
        return self.request("GET", f"/session/{int(player_id)}").get("state")

    def finish(self, player_id, score, subject):
        return self.request("POST", "/sessions/finish", {"player_id": player_id, "score": score, "subject": subject})

    def leaderboard(self):
        return self.request("GET", "/leaderboard")

    def available_sessions(self):
        return self.request("GET", "/sessions/available")

    def login_admin(self, password):
        self.admin_token = self.request("POST", "/admin/login", {"password": password})["token"]

    def sync_exam(self, year, subject, problem_pdf, answer_pdf):
        return self.request("POST", "/admin/sync", {"year": year, "subject": subject,
                             "problem_pdf": problem_pdf, "answer_pdf": answer_pdf}, admin=True)

    def export_csv(self):
        return self.request("GET", "/admin/export.csv", admin=True)

    def export_saves_csv(self):
        return self.request("GET", "/admin/export/saves.csv", admin=True)

    def pending_cheats(self):
        return self.request("GET", "/admin/cheats", admin=True)

    def review_cheat(self, request_id, approve):
        return self.request("POST", f"/admin/cheats/{int(request_id)}/approve", {"approve": approve}, admin=True)

    def request_cheat(self, player_id, cheat):
        return self.request("POST", "/admin/cheats/request", {"player_id": player_id, "cheat": cheat})

    def cheat_status(self, request_id):
        return self.request("GET", f"/cheats/status/{int(request_id)}")

    def pending_questions(self):
        return self.request("GET", "/admin/questions", admin=True)

    def review_question(self, question_id, approve):
        from urllib.parse import quote
        return self.request("POST", "/admin/questions/" + quote(question_id) + "/review",
                            {"approve": approve}, admin=True)
