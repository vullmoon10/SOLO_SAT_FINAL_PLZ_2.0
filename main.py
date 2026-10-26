import pygame

from settings import WIDTH, HEIGHT, TITLE
from core.game import Game
from systems.local_storage import LocalStorage
from systems.audio import AudioManager
from ui.menu import Menu


def _new_session(storage):
    nickname = input("닉네임 (비우면 자동 지정): ").strip() or storage.next_nickname()
    subject = "수학"
    return {"nickname": nickname, "subject": subject}, None


def _load_session(storage):
    state = storage.load()
    if not state:
        print("불러올 자동 저장 기록이 없습니다.")
        return None
    subject = "수학"
    return {"nickname": state.get("nickname", "player-1"), "subject": subject}, state


def _print_leaderboard(rows):
    print("\n=== 로컬 랭킹 ===")
    if not rows:
        print("아직 게임 기록이 없습니다.")
    for rank, row in enumerate(rows, 1):
        print(f"{rank:>2}. {row['nickname']} · {row['score']}점 · {row['subject']}")


def main():
    storage = LocalStorage()
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)
    audio = AudioManager()
    audio.play_menu_music()
    try:
        while True:
            action = Menu(screen, audio=audio).run()
            screen = pygame.display.get_surface()
            if action == "quit":
                break
            if action == "new_game":
                session, state = _new_session(storage)
                Game(screen, session, state, local_storage=storage, audio=audio).run()
                audio.play_menu_music()
            elif action == "load_game":
                selected = _load_session(storage)
                if selected:
                    session, state = selected
                    Game(screen, session, state, local_storage=storage, audio=audio).run()
                    audio.play_menu_music()
            elif action == "leaderboard":
                _print_leaderboard(storage.leaderboard())
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
