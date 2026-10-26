"""게임을 초기화하고 메뉴와 플레이 화면 사이의 실행 흐름을 연결한다."""

import pygame

from settings import WIDTH, HEIGHT, TITLE
from core.game import Game
from systems.local_storage import LocalStorage
from systems.audio import AudioManager
from ui.menu import Menu


# 새 게임용 닉네임과 과목 정보를 만들고 초기 저장 상태를 반환한다.
def _new_session(storage):
    nickname = input("닉네임 (비우면 자동 지정): ").strip() or storage.next_nickname()
    subject = "수학"
    return {"nickname": nickname, "subject": subject}, None


# 자동 저장을 읽어 이어 하기 세션을 만들며 저장 데이터가 없으면 중단한다.
def _load_session(storage):
    state = storage.load()
    # 이어 할 저장 데이터가 없으면 안내 후 메뉴로 돌아간다.
    if not state:
        print("불러올 자동 저장 기록이 없습니다.")
        return None
    subject = "수학"
    return {"nickname": state.get("nickname", "player-1"), "subject": subject}, state


# 랭킹 기록이 없다는 안내 또는 점수 목록을 터미널에 출력한다.
def _print_leaderboard(rows):
    print("\n=== 로컬 랭킹 ===")
    # 기록이 비어 있을 때 사용자에게 현재 상태를 알린다.
    if not rows:
        print("아직 게임 기록이 없습니다.")
    # 순위 번호를 붙여 각 기록을 한 줄씩 표시한다.
    for rank, row in enumerate(rows, 1):
        print(f"{rank:>2}. {row['nickname']} · {row['score']}점 · {row['subject']}")


# 저장소, 오디오, 메뉴를 준비하고 게임 종료까지 화면 흐름을 조정한다.
def main():
    storage = LocalStorage()
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)
    audio = AudioManager()
    audio.play_menu_music()
    # 게임 실행 중 예외가 나더라도 Pygame 자원을 정리한다.
    try:
        # 메뉴에서 선택한 동작에 따라 게임·랭킹·종료 화면을 이어 간다.
        while True:
            action = Menu(screen, audio=audio).run()
            screen = pygame.display.get_surface()
            # 종료 메뉴를 선택하면 메인 반복을 끝낸다.
            if action == "quit":
                break
            # 새 게임은 새 세션을 만들고 게임 화면으로 전환한다.
            if action == "new_game":
                session, state = _new_session(storage)
                Game(screen, session, state, local_storage=storage, audio=audio).run()
                audio.play_menu_music()
            # 불러오기는 저장 상태가 있을 때만 게임을 재개한다.
            elif action == "load_game":
                selected = _load_session(storage)
                # 저장 기록을 찾은 경우 닉네임과 진행 상태를 적용한다.
                if selected:
                    session, state = selected
                    Game(screen, session, state, local_storage=storage, audio=audio).run()
                    audio.play_menu_music()
            # 랭킹 메뉴는 현재 로컬 기록을 출력한다.
            elif action == "leaderboard":
                _print_leaderboard(storage.leaderboard())
    # 종료 경로와 예외 경로에서 Pygame을 함께 정리한다.
    finally:
        pygame.quit()


# 이 파일을 직접 실행할 때만 게임 진입점을 호출한다.
if __name__ == "__main__":
    main()
