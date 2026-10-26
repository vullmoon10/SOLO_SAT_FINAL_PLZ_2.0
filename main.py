import os
import pygame

from settings import WIDTH, HEIGHT, TITLE
from core.game import Game
from systems.local_storage import LocalStorage
from systems.audio import AudioManager
from systems.quiz import QUESTIONS, set_question_source
from systems.subjects import SUBJECTS
from ui.menu import Menu


def _select_subject(subjects):
    print("\n출제 과목을 선택하세요.")
    for index, subject in enumerate(subjects, 1):
        print(f"{index}. {subject}")
    while True:
        value = input("과목 번호: ").strip()
        if value.isdigit() and 1 <= int(value) <= len(subjects):
            return subjects[int(value) - 1]
        print("목록에 있는 번호를 입력하세요.")


def _new_session(client):
    nickname = input("닉네임 (비우면 player-n으로 지정): ").strip()
    subject = _select_subject(SUBJECTS)
    session = client.start_session(nickname, subject)
    questions = client.questions(subject)
    if not questions:
        print(f"{subject} 과목의 공개된 2점 문항이 없습니다. 관리자 모드에서 PDF 등록과 검수를 진행하세요.")
        return None
    set_question_source(subject, client, questions)
    return session, None


def _load_session(client):
    available = client.available_sessions()
    if not available:
        print("불러올 자동 저장 기록이 없습니다.")
        return None
    print("\n자동 저장 목록")
    for index, entry in enumerate(available, 1):
        print(f"{index}. {entry['nickname']} (기록 번호 {entry['player_id']})")
    while True:
        value = input("불러올 번호 (Enter 취소): ").strip()
        if not value:
            return None
        if value.isdigit() and 1 <= int(value) <= len(available):
            entry = available[int(value) - 1]
            state = client.load(entry["player_id"])
            if not state:
                print("저장 기록을 읽지 못했습니다.")
                return None
            subject = state.get("subject", "수학")
            questions = client.questions(subject)
            if not questions:
                print(f"{subject} 과목에 공개된 문항이 없습니다.")
                return None
            set_question_source(subject, client, questions)
            return {"player_id": entry["player_id"], "nickname": entry["nickname"], "subject": subject}, state
        print("목록 번호를 입력하세요.")


def _new_local_session(local_storage):
    nickname = input("닉네임 (비우면 player-n으로 지정): ").strip()
    if not nickname:
        nickname = local_storage.next_nickname()
    local_subjects = sorted({question.get("subject", "수학") for question in QUESTIONS})
    if not local_subjects:
        print("data/questions.json에 등록된 로컬 문항이 없습니다.")
        return None
    subject = _select_subject(local_subjects)
    set_question_source(subject, None, [], local_mode=True)
    return {"nickname": nickname, "subject": subject}, None


def _load_local_session(local_storage):
    state = local_storage.load()
    if not state:
        print("불러올 로컬 자동 저장 기록이 없습니다.")
        return None
    subject = state.get("subject", "수학")
    set_question_source(subject, None, [], local_mode=True)
    return {"nickname": state.get("nickname", "player-1"), "subject": subject}, state


def _print_leaderboard(rows, title):
    print(f"\n=== {title} ===")
    if not rows:
        print("아직 게임 기록이 없습니다.")
    for rank, row in enumerate(rows, 1):
        print(f"{rank:>2}. {row['nickname']} · {row['score']}점 · {row['subject']}")


def main():
    print("SOLO SAT 시작 메뉴")
    print("1. 사용자 모드 (부스 서버 연결)")
    print("2. 관리자 모드 (서버 노트북에서 실행)")
    print("3. 로컬 옵션 (서버 없이 이 컴퓨터에서 실행)")
    mode = input("선택: ").strip()
    if mode == "2":
        from ui.admin import run_admin
        run_admin()
        return
    if mode not in ("1", "3"):
        print("실행을 취소했습니다.")
        return

    local_mode = mode == "3"
    local_storage = LocalStorage() if local_mode else None
    client = None
    if not local_mode:
        from network.client import BoothClient
        client = BoothClient(os.environ.get("SOLO_SAT_SERVER"))
        try:
            client.request("GET", "/health")
        except RuntimeError as exc:
            print(exc)
            address = input("관리자 노트북 주소 입력 (예: http://192.168.0.10:8765, Enter=이 컴퓨터): ").strip()
            client = BoothClient(address or "http://127.0.0.1:8765")
            try:
                client.request("GET", "/health")
            except RuntimeError as retry_exc:
                print(retry_exc)
                return

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)
    audio = AudioManager()
    audio.play_menu_music()
    try:
        while True:
            action = Menu(screen, local_mode=local_mode, audio=audio).run()
            screen = pygame.display.get_surface()
            if action == "quit":
                break
            if action == "new_game":
                try:
                    selected = _new_local_session(local_storage) if local_mode else _new_session(client)
                except RuntimeError as exc:
                    print(exc)
                    continue
                if selected:
                    session, state = selected
                    Game(screen, client, session, state, local_storage=local_storage, audio=audio).run()
                    audio.play_menu_music()
            elif action == "load_game":
                try:
                    selected = _load_local_session(local_storage) if local_mode else _load_session(client)
                except RuntimeError as exc:
                    print(exc)
                    continue
                if selected:
                    session, state = selected
                    Game(screen, client, session, state, local_storage=local_storage, audio=audio).run()
                    audio.play_menu_music()
            elif action == "leaderboard":
                if local_mode:
                    _print_leaderboard(local_storage.leaderboard(), "로컬 랭킹")
                else:
                    try:
                        _print_leaderboard(client.leaderboard(), "부스 랭킹")
                    except RuntimeError as exc:
                        print(exc)
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
