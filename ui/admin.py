from getpass import getpass
import socket
from network.client import BoothClient
from network.server import ADMIN_HASH_PATH, DATA_DIR, configure_admin_password, start_server
from systems.subjects import SUBJECTS


def _init_password():
    if ADMIN_HASH_PATH.exists():
        return
    print("최초 관리자 암호를 설정합니다. 암호 자체는 저장하지 않고 해시만 보관합니다.")
    while True:
        password = getpass("새 관리자 암호(8자 이상): ")
        again = getpass("암호 확인: ")
        if password != again:
            print("암호가 일치하지 않습니다.")
        elif len(password) < 8:
            print("암호는 8자 이상이어야 합니다.")
        else:
            configure_admin_password(password)
            break


def run_admin():
    DATA_DIR.joinpath("imports").mkdir(parents=True, exist_ok=True)
    DATA_DIR.joinpath("exports").mkdir(parents=True, exist_ok=True)
    try:
        server = start_server()
    except OSError as exc:
        print(f"관리 서버를 시작하지 못했습니다. 8765 포트 사용 여부를 확인하세요: {exc}")
        return
    client = BoothClient("http://127.0.0.1:8765")
    try:
        _init_password()
        client.login_admin(getpass("관리자 암호: "))
    except RuntimeError as exc:
        server.shutdown()
        print(exc)
        return
    print(f"서버가 시작되었습니다. 부스 기기 접속 주소는 이 노트북의 LAN IP:8765 입니다.")
    try:
        addresses = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")]
        if addresses:
            print("서버 접속 주소: " + " / ".join(f"http://{ip}:8765" for ip in addresses))
    except OSError:
        print("서버 노트북에서 ipconfig를 실행해 LAN IPv4 주소를 확인하세요.")
    print(f"PDF 등록 폴더: {DATA_DIR / 'imports'}")
    while True:
        print("\n[관리자 메뉴] 1 문항 PDF 등록  2 문항 검수  3 랭킹/CSV  4 치트 승인  5 암호 변경  0 종료")
        action = input("> ").strip()
        try:
            if action == "1":
                year = int(input("학년도 (예: 2026): ").strip())
                print("과목: " + ", ".join(SUBJECTS))
                subject = input("과목명: ").strip()
                problem = input("문제 PDF 경로(등록 폴더 안): ").strip().strip('"')
                answer = input("정답 PDF 경로(등록 폴더 안): ").strip().strip('"')
                print(client.sync_exam(year, subject, problem, answer))
            elif action == "2":
                questions = client.pending_questions()
                if not questions:
                    print("검수 대기 문항이 없습니다.")
                for question in questions:
                    print(f"{question['id']} · {question['year']}년 {question['subject']} {question['question_no']}번 · PDF {question['page'] + 1}쪽")
                    print(f"정답표 자동 추출값: {question['answer'] + 1}번 (원본 정답 PDF와 확인하세요)")
                    print(question.get("question_text", ""))
                    approve = input("게임에 공개할까요? [y/N] ").strip().lower() == "y"
                    client.review_question(question["id"], approve)
            elif action == "3":
                for rank, row in enumerate(client.leaderboard(), 1):
                    print(f"{rank:>2}. {row['nickname']} · {row['score']}점 · {row['subject']}")
                output = DATA_DIR / "exports" / "leaderboard.csv"
                output.write_bytes(client.export_csv())
                saves_output = DATA_DIR / "exports" / "saves.csv"
                saves_output.write_bytes(client.export_saves_csv())
                print(f"랭킹 CSV 저장: {output}")
                print(f"자동 저장 세이브 CSV 저장: {saves_output}")
            elif action == "4":
                requests = client.pending_cheats()
                if not requests:
                    print("대기 중인 치트 요청이 없습니다.")
                for request in requests:
                    approve = input(f"플레이어 {request['player_id']}의 치트 {request['cheat']} 승인? [y/N] ").strip().lower() == "y"
                    client.review_cheat(request["id"], approve)
            elif action == "5":
                _init_password_force()
            elif action == "0":
                return
            else:
                print("메뉴 번호를 선택하세요.")
        except (RuntimeError, ValueError, OSError) as exc:
            print(f"처리하지 못했습니다: {exc}")
    server.shutdown()


def _init_password_force():
    old = getpass("현재 암호: ")
    check = BoothClient("http://127.0.0.1:8765")
    try:
        check.login_admin(old)
    except RuntimeError as exc:
        print(exc)
        return
    while True:
        new = getpass("새 암호(8자 이상): ")
        again = getpass("암호 확인: ")
        if new != again:
            print("암호가 일치하지 않습니다.")
            continue
        try:
            configure_admin_password(new)
            print("관리자 암호를 변경했습니다.")
        except ValueError as exc:
            print(exc)
            continue
        return
