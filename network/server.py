"""Small standard-library HTTP server for a closed booth LAN."""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import os
import secrets
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("SOLO_SAT_DATA_DIR", ROOT / "runtime"))
DB_PATH = DATA_DIR / "solo_sat.sqlite3"
ADMIN_HASH_PATH = DATA_DIR / "admin.hash"


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1).hex()
    return salt.hex(), digest


class BoothDatabase:
    def __init__(self, path: Path = DB_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nickname TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    player_id INTEGER PRIMARY KEY REFERENCES players(id),
                    state_json TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER NOT NULL UNIQUE REFERENCES players(id),
                    nickname TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    finished_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS scores_rank ON scores(score DESC, finished_at ASC);
                CREATE TABLE IF NOT EXISTS cheat_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER NOT NULL REFERENCES players(id),
                    cheat TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    requested_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS questions (
                    id TEXT PRIMARY KEY,
                    year INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    question_no INTEGER NOT NULL,
                    score_value INTEGER NOT NULL,
                    answer INTEGER NOT NULL,
                    page INTEGER NOT NULL,
                    pdf_path TEXT NOT NULL,
                    page_image BLOB,
                    question_text TEXT NOT NULL DEFAULT '',
                    choices_json TEXT NOT NULL DEFAULT '[]',
                    source_url TEXT NOT NULL DEFAULT '',
                    reviewed INTEGER NOT NULL DEFAULT 0
                );
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def new_player(self, nickname: str) -> dict:
        with self.connect() as db:
            base = (nickname or "").strip()[:24]
            if not base:
                n = 1
                while db.execute("SELECT 1 FROM players WHERE nickname=?", (f"player-{n}",)).fetchone():
                    n += 1
                base = f"player-{n}"
            cur = db.execute("INSERT INTO players(nickname, created_at) VALUES(?, ?)", (base, time.time()))
            return {"player_id": cur.lastrowid, "nickname": base}

    def save_session(self, player_id: int, state: dict) -> None:
        with self.connect() as db:
            db.execute("""INSERT INTO sessions(player_id,state_json,updated_at) VALUES(?,?,?)
                ON CONFLICT(player_id) DO UPDATE SET state_json=excluded.state_json, updated_at=excluded.updated_at""",
                (player_id, json.dumps(state, ensure_ascii=False), time.time()))

    def load_session(self, player_id: int):
        with self.connect() as db:
            row = db.execute("SELECT state_json FROM sessions WHERE player_id=?", (player_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def leaderboard(self, limit=25):
        with self.connect() as db:
            rows = db.execute("""SELECT nickname,score,subject,finished_at FROM (
                SELECT nickname,score,subject,finished_at,
                       ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY score DESC,finished_at ASC) rank_no
                FROM scores) WHERE rank_no=1 ORDER BY score DESC,finished_at ASC LIMIT ?""", (limit,)).fetchall()
        return [dict(row) for row in rows]

    def record_score(self, player_id: int, score: int, subject: str, finished: bool = False):
        with self.connect() as db:
            player = db.execute("SELECT nickname FROM players WHERE id=?", (player_id,)).fetchone()
            if not player:
                return
            db.execute("""INSERT INTO scores(player_id,nickname,score,subject,finished_at) VALUES(?,?,?,?,?)
                ON CONFLICT(player_id) DO UPDATE SET nickname=excluded.nickname,
                subject=CASE WHEN excluded.score>=scores.score THEN excluded.subject ELSE scores.subject END,
                finished_at=CASE WHEN excluded.score>=scores.score THEN excluded.finished_at ELSE scores.finished_at END,
                score=MAX(scores.score,excluded.score)""",
                (player_id, player[0], max(0, int(score)), subject, time.time()))
            if finished:
                db.execute("DELETE FROM sessions WHERE player_id=?", (player_id,))


def configure_admin_password(password: str) -> None:
    if len(password) < 8:
        raise ValueError("관리자 암호는 8자 이상이어야 합니다.")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    salt, digest = _hash_password(password)
    ADMIN_HASH_PATH.write_text(f"{salt}:{digest}", encoding="ascii")


def verify_admin_password(password: str) -> bool:
    try:
        salt_hex, expected = ADMIN_HASH_PATH.read_text(encoding="ascii").strip().split(":", 1)
        _, actual = _hash_password(password, bytes.fromhex(salt_hex))
        return hmac.compare_digest(expected, actual)
    except (OSError, ValueError):
        return False


class BoothHandler(BaseHTTPRequestHandler):
    db = BoothDatabase()
    admin_tokens: set[str] = set()
    token_lock = threading.Lock()
    cheat_lock = threading.Lock()
    subject_cache = None

    def log_message(self, *_args):
        return

    def _send(self, status: int, body, content_type="application/json; charset=utf-8"):
        raw = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def _body(self):
        size = min(int(self.headers.get("Content-Length", "0")), 2_000_000)
        return json.loads(self.rfile.read(size) or b"{}")

    def _admin(self):
        token = self.headers.get("X-Admin-Token", "")
        with self.token_lock:
            return token in self.admin_tokens

    def do_GET(self):
        route = urlparse(self.path)
        if route.path == "/health":
            self._send(200, {"ok": True, "version": 1})
        elif route.path == "/leaderboard":
            self._send(200, self.db.leaderboard())
        elif route.path == "/sessions/available":
            with self.db.connect() as db:
                rows = db.execute("SELECT p.id player_id,p.nickname,s.updated_at FROM players p JOIN sessions s ON p.id=s.player_id ORDER BY s.updated_at DESC").fetchall()
            self._send(200, [dict(row) for row in rows])
        elif route.path == "/questions":
            subject = parse_qs(route.query).get("subject", [""])[0]
            with self.db.connect() as db:
                rows = db.execute("SELECT id, year, subject, question_no, page, question_text, choices_json FROM questions WHERE reviewed=1 AND score_value=2 AND (?='' OR subject=?) ORDER BY year DESC, subject, question_no", (subject, subject)).fetchall()
            self._send(200, [{**dict(row), "q": f"{row['year']}년 3월 고1 {row['subject']} {row['question_no']}번 · PDF {row['page'] + 1}쪽",
                              "choices": json.loads(row["choices_json"]),
                              "difficulty": "easy", "time": 30} for row in rows])
        elif route.path.startswith("/questions/") and route.path.endswith("/page"):
            question_id = unquote(route.path[len("/questions/"):-len("/page")].strip("/"))
            with self.db.connect() as db:
                row = db.execute("SELECT page_image FROM questions WHERE id=? AND reviewed=1", (question_id,)).fetchone()
            self._send(200, row[0], "image/png") if row and row[0] else self._send(404, {"error": "문항 이미지를 찾을 수 없습니다."})
        elif route.path.startswith("/session/"):
            try:
                state = self.db.load_session(int(route.path.rsplit("/", 1)[1]))
                self._send(200, {"state": state})
            except ValueError:
                self._send(400, {"error": "잘못된 플레이어 번호입니다."})
        elif route.path == "/admin/cheats":
            if not self._admin():
                self._send(403, {"error": "관리자 인증이 필요합니다."})
                return
            with self.db.connect() as db:
                rows = db.execute("SELECT id, player_id, cheat, requested_at FROM cheat_requests WHERE status='pending' ORDER BY requested_at").fetchall()
            self._send(200, [dict(row) for row in rows])
        elif route.path == "/admin/questions":
            if not self._admin():
                self._send(403, {"error": "관리자 인증이 필요합니다."})
                return
            with self.db.connect() as db:
                rows = db.execute("SELECT id,year,subject,question_no,page,answer,question_text FROM questions WHERE reviewed=0 ORDER BY year DESC,subject,question_no").fetchall()
            self._send(200, [dict(row) for row in rows])
        elif route.path.startswith("/cheats/status/"):
            try:
                request_id = int(route.path.rsplit("/", 1)[1])
                with self.db.connect() as db:
                    row = db.execute("SELECT status,cheat FROM cheat_requests WHERE id=?", (request_id,)).fetchone()
                self._send(200, dict(row) if row else {"status": "missing"})
            except ValueError:
                self._send(400, {"error": "요청 번호가 올바르지 않습니다."})
        elif route.path == "/admin/export.csv":
            if not self._admin():
                self._send(403, {"error": "관리자 인증이 필요합니다."})
                return
            out = io.StringIO(newline="")
            writer = csv.writer(out)
            writer.writerow(["nickname", "score", "subject", "finished_at"])
            with self.db.connect() as db:
                writer.writerows(db.execute("SELECT nickname,score,subject,datetime(finished_at,'unixepoch','localtime') FROM scores ORDER BY score DESC"))
            self._send(200, out.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8")
        elif route.path == "/admin/export/saves.csv":
            if not self._admin():
                self._send(403, {"error": "관리자 인증이 필요합니다."})
                return
            out = io.StringIO(newline="")
            writer = csv.writer(out)
            writer.writerow(["player_id", "nickname", "subject", "score", "hp", "player_x", "updated_at"])
            with self.db.connect() as db:
                rows = db.execute("SELECT p.id,p.nickname,s.state_json,s.updated_at FROM players p JOIN sessions s ON p.id=s.player_id ORDER BY s.updated_at DESC").fetchall()
            for row in rows:
                state = json.loads(row["state_json"])
                writer.writerow([row["id"], row["nickname"], state.get("subject", ""), state.get("score", 0),
                                 state.get("hp", 0), state.get("player_x", 0), row["updated_at"]])
            self._send(200, out.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8")
        else:
            self._send(404, {"error": "요청 경로를 찾을 수 없습니다."})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            data = self._body()
        except (json.JSONDecodeError, ValueError):
            self._send(400, {"error": "요청 형식이 올바르지 않습니다."})
            return
        if path == "/admin/login":
            if not self.client_address[0].startswith("127.") and self.client_address[0] != "::1":
                self._send(403, {"error": "관리자 접속은 서버 컴퓨터에서만 가능합니다."})
                return
            if not verify_admin_password(str(data.get("password", ""))):
                self._send(401, {"error": "관리자 암호가 올바르지 않습니다."})
                return
            token = secrets.token_urlsafe(32)
            with self.token_lock:
                self.admin_tokens.add(token)
            self._send(200, {"token": token})
        elif path == "/questions/answer":
            try:
                question_id, choice = str(data["question_id"]), int(data["choice"])
                with self.db.connect() as db:
                    row = db.execute("SELECT answer FROM questions WHERE id=? AND reviewed=1 AND score_value=2", (question_id,)).fetchone()
                if not row or not 0 <= choice <= 4:
                    self._send(404, {"error": "문항이나 답안이 올바르지 않습니다."})
                else:
                    self._send(200, {"correct": choice == row["answer"]})
            except (KeyError, TypeError, ValueError):
                self._send(400, {"error": "답안 제출 형식이 올바르지 않습니다."})
        elif path == "/sessions/start":
            player = self.db.new_player(str(data.get("nickname", "")))
            player["subject"] = str(data.get("subject", "수학"))[:40]
            self._send(201, player)
        elif path == "/sessions/save":
            try:
                player_id = int(data["player_id"])
                state = data.get("state", {})
                self.db.save_session(player_id, state)
                self.db.record_score(player_id, int(state.get("score", 0)), str(state.get("subject", "")))
                self._send(200, {"saved": True})
            except (KeyError, TypeError, ValueError):
                self._send(400, {"error": "저장 데이터가 올바르지 않습니다."})
        elif path == "/sessions/finish":
            try:
                player_id = int(data["player_id"])
                score = int(data.get("score", 0))
                subject = str(data.get("subject", ""))[:40]
                self.db.record_score(player_id, score, subject, finished=True)
                self._send(200, {"saved": True})
            except (KeyError, TypeError, ValueError):
                self._send(400, {"error": "기록 데이터가 올바르지 않습니다."})
        elif path == "/admin/cheats/request":
            try:
                with self.db.connect() as db:
                    cur = db.execute("INSERT INTO cheat_requests(player_id,cheat,requested_at) VALUES(?,?,?)", (int(data["player_id"]), str(data["cheat"])[:40], time.time()))
                self._send(201, {"request_id": cur.lastrowid})
            except (KeyError, ValueError):
                self._send(400, {"error": "치트 요청이 올바르지 않습니다."})
        elif path.startswith("/admin/cheats/") and path.endswith("/approve"):
            if not self._admin():
                self._send(403, {"error": "관리자 인증이 필요합니다."})
                return
            try:
                request_id = int(path.split("/")[-2])
                with self.db.connect() as db:
                    db.execute("UPDATE cheat_requests SET status=? WHERE id=? AND status='pending'", ("approved" if data.get("approve") else "denied", request_id))
                self._send(200, {"updated": True})
            except ValueError:
                self._send(400, {"error": "치트 요청 번호가 올바르지 않습니다."})
        elif path == "/admin/sync":
            if not self._admin():
                self._send(403, {"error": "관리자 인증이 필요합니다."})
                return
            try:
                from systems.ebsi_importer import sync_exam
                result = sync_exam(int(data["year"]), str(data["subject"]),
                                   str(data["problem_pdf"]), str(data["answer_pdf"]))
                self._send(200, result)
            except Exception as exc:
                self._send(400, {"error": str(exc)[:300]})
        elif path.startswith("/admin/questions/") and path.endswith("/review"):
            if not self._admin():
                self._send(403, {"error": "관리자 인증이 필요합니다."})
                return
            from systems.ebsi_importer import review_question
            qid = unquote(path[len("/admin/questions/"):-len("/review")].strip("/"))
            self._send(200, {"updated": review_question(qid, bool(data.get("approve")))})
        else:
            self._send(404, {"error": "요청 경로를 찾을 수 없습니다."})


def run_server(host="0.0.0.0", port=8765):
    BoothDatabase()
    ThreadingHTTPServer((host, port), BoothHandler).serve_forever()


def start_server(host="0.0.0.0", port=8765):
    BoothDatabase()
    server = ThreadingHTTPServer((host, port), BoothHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


if __name__ == "__main__":
    run_server()
