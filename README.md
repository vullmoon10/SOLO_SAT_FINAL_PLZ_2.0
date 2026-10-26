# SOLO SAT — 부스 네트워크 게임

Pygame으로 만든 학습·전투 게임 프로토타입이다. 부스 환경에서는 관리자 노트북이 HTTP 서버와 SQLite 데이터베이스를 담당하고, 참가자 기기들은 같은 LAN에서 서버에 접속한다. 서버 없이 한 컴퓨터에서 실행하는 로컬 모드도 제공한다.

## 요구 사항

- Python 3.10 이상
- 패키지: `requirements.txt` 기준
  - `pygame>=2.5.0`
  - `PyMuPDF>=1.23.0`
- 참가자 기기와 관리자 노트북이 같은 로컬 네트워크(LAN)에 연결되어 있어야 한다.

## 실행 방법

프로젝트 루트에서 다음 명령을 실행한다.

```bash
python -m pip install -r requirements.txt
python main.py
```

시작 메뉴에서 모드를 선택한다.

1. **사용자 모드** — 부스 서버에 접속한다. 기본 주소를 확인하고, 연결되지 않으면 관리자 노트북의 LAN 주소를 입력한다.
2. **관리자 모드** — 이 컴퓨터에서 부스 HTTP 서버를 시작하고 관리자 메뉴를 연다. 최초 실행 시 8자 이상의 관리자 암호를 설정한다.
3. **로컬 옵션** — 네트워크 서버 없이 이 컴퓨터의 로컬 저장 데이터로 실행한다.

### 부스 네트워크 연결

1. 관리자 노트북에서 `python main.py`를 실행하고 `2`를 선택한다.
2. 콘솔에 표시된 서버 주소를 확인한다. 기본 포트는 `8765`이다.
3. 참가자 기기에서 `python main.py`를 실행하고 `1`을 선택한다.
4. 자동 연결에 실패하면 관리자 노트북의 LAN 주소를 입력한다. 예: `http://192.168.0.10:8765`
5. 연결이 안 되면 두 기기가 같은 네트워크인지, 운영체제 방화벽에서 TCP 8765 연결을 허용하는지 확인한다.

서버 주소는 `SOLO_SAT_SERVER` 환경변수로 지정할 수도 있다.

PowerShell:
```powershell
$env:SOLO_SAT_SERVER="http://192.168.0.10:8765"
python main.py
```

서버 상태 확인 경로는 `GET /health`이다. 서버는 기본적으로 `0.0.0.0:8765`에 바인딩되어 LAN 접속을 받는다.

## 네트워크 구조

```text
참가자 Pygame 클라이언트
  └─ network/client.py (BoothClient, HTTP/JSON)
       └─ LAN / TCP 8765
            └─ network/server.py (ThreadingHTTPServer)
                 ├─ network 요청 처리 (BoothHandler)
                 ├─ SQLite 데이터베이스
                 └─ runtime/ 데이터 디렉터리
```

- `network/client.py`: 표준 라이브러리 `urllib`로 서버 요청을 보내는 클라이언트. 기본 요청 제한 시간은 4초이며 HTTP/연결 오류를 `RuntimeError`로 전달한다.
- `network/server.py`: Python 표준 라이브러리의 `http.server.ThreadingHTTPServer` 기반 멀티스레드 HTTP 서버.
- `ui/admin.py`: 관리자 모드 진입, 서버 시작, 최초 암호 설정, 문항 등록·검수, CSV 내보내기 및 치트 승인 메뉴.
- `systems/ebsi_importer.py`: 수능·모의고사 문제 PDF와 정답 PDF를 가져와 문항 데이터를 등록·검수하는 기능.
- `systems/local_storage.py`: 네트워크 없이 실행할 때 사용하는 별도 로컬 저장·랭킹 기능.
- `core/game.py`, `systems/quiz.py`: 게임 진행과 원격 문항 사용, 저장·랭킹·치트 요청 연동.

## 서버 기능 및 주요 API

| 메서드 | 경로 | 용도 |
| --- | --- | --- |
| GET | `/health` | 서버 상태 확인 |
| POST | `/sessions/start` | 참가자 세션 생성 |
| GET | `/questions?subject=과목` | 검수 완료된 공개 문항 조회 |
| GET | `/questions/{id}/page` | 문항 PDF 페이지 이미지 조회 |
| POST | `/questions/answer` | 선택 답안 정오 확인 |
| POST | `/sessions/save` | 게임 진행 상태 저장 |
| GET | `/session/{player_id}` | 저장된 진행 상태 조회 |
| GET | `/sessions/available` | 이어하기 가능한 세션 조회 |
| POST | `/sessions/finish` | 게임 결과 기록 및 세션 저장 데이터 정리 |
| GET | `/leaderboard` | 랭킹 조회 |
| POST | `/admin/login` | 관리자 인증 토큰 발급 |
| POST | `/admin/sync` | 문제·정답 PDF 등록 처리 |
| GET | `/admin/questions` | 검수 대기 문항 조회 |
| POST | `/admin/questions/{id}/review` | 문항 공개 여부 검수 |
| GET | `/admin/export.csv` | 랭킹 CSV 내보내기 |
| GET | `/admin/export/saves.csv` | 세이브 데이터 CSV 내보내기 |
| POST | `/admin/cheats/request` | 참가자 치트 승인 요청 |
| GET | `/admin/cheats` | 대기 중인 치트 요청 조회 |
| POST | `/admin/cheats/{id}/approve` | 치트 요청 승인·거절 |
| GET | `/cheats/status/{id}` | 치트 요청 상태 조회 |

관리자 전용 경로는 `X-Admin-Token` 헤더의 토큰을 확인한다. 관리자 로그인 요청은 서버 컴퓨터의 루프백 주소에서만 허용된다.

## 데이터 저장

기본 서버 데이터 디렉터리는 프로젝트 루트의 `runtime/`이다.

- `runtime/solo_sat.sqlite3`: 참가자, 세션, 점수, 치트 요청 및 문항 데이터
- `runtime/admin.hash`: 관리자 암호의 salt와 scrypt 해시
- `runtime/imports/`: 관리자 문항 등록용 PDF 폴더
- `runtime/exports/`: 관리자 메뉴에서 생성한 CSV 파일

데이터 디렉터리는 `SOLO_SAT_DATA_DIR` 환경변수로 바꿀 수 있다. 로컬 모드 데이터는 `runtime/local/` 아래 JSON 파일로 저장된다.

## 관리자 메뉴

관리자 모드에서 제공하는 기능:

1. 문제·정답 PDF 등록
2. 자동 추출된 문항과 정답 검수 및 공개 여부 결정
3. 랭킹과 저장 기록 CSV 내보내기
4. 참가자의 치트 요청 승인·거절
5. 관리자 암호 변경

PDF에서 자동 추출된 문항과 정답은 원본과 대조해 검수해야 한다. 검수되지 않은 문항은 공개 문항 조회 대상에 포함되지 않는다.

## 게임 조작

- A/D 또는 ←/→: 이동
- Space: 점프
- W/S 또는 ↑/↓: 사다리 오르내리기
- E: 근처 몬스터와 상호작용
- 문제 창: ↑/↓ 선택, Enter 제출, 1~4 즉시 선택, 마우스 클릭
- F11: 전체화면 전환
- ESC: 게임 일시정지/재개 또는 메뉴 동작
- F2: 네트워크 사용자 모드에서 관리자 치트 승인 요청

## 보안 및 운영상 주의

이 구현은 **신뢰할 수 있는 부스 LAN에서 사용하는 프로토타입**이다. 인터넷에 직접 노출하거나 신뢰할 수 없는 네트워크에서 운영하도록 설계된 것으로 간주하면 안 된다.

- HTTP 통신은 TLS로 암호화되지 않는다. 참가자와 서버 사이의 데이터는 같은 네트워크에서 관찰될 수 있다.
- 서버 응답에 `Access-Control-Allow-Origin: *`가 포함된다. 브라우저 기반 접근까지 포함해 운영 환경의 접근 범위를 검토해야 한다.
- 세션 저장·조회, 랭킹 조회, 답안 확인 등 일부 API에는 참가자 인증이나 요청별 권한 검사가 없다. 클라이언트가 보낸 점수·저장 데이터의 신뢰성도 서버 측에서 충분히 보장되지 않는다.
- 관리자 토큰은 서버 프로세스 메모리에 보관되며, 현재 구현에는 만료·폐기 흐름이 없다.
- 서버 포트는 LAN에 열리므로 방화벽에서는 필요한 사설 네트워크에만 허용한다. 공유기 포트 포워딩으로 외부에 공개하지 않는다.
- 관리자 암호를 다른 계정에서 쓰는 암호와 재사용하지 않는다. `runtime/`에는 참가자 기록과 데이터베이스가 있으므로 백업·공유 시 주의한다.

## 프로젝트 구조

- `main.py`: 시작 메뉴와 게임 실행 흐름
- `network/`: 부스 HTTP 서버와 클라이언트
- `core/`: 게임 루프 및 이벤트 처리
- `entities/`: 플레이어와 몬스터
- `world/`: 지형·발판·사다리·장애물 생성
- `systems/`: 문항, 전투, 성장, 저장, 오디오 및 PDF 가져오기
- `ui/`: 게임 메뉴 및 관리자 인터페이스
- `data/questions.json`: 로컬 모드 문제 데이터
- `requirements.txt`: Python 의존성

## 구현 범위

네트워크 부스 모드, 로컬 모드, 자동 저장, 랭킹, 관리자 문항 등록·검수, CSV 내보내기 및 치트 승인 흐름이 구현되어 있다. 다만 이는 프로토타입이며, 인증·권한·입력 검증·전송 보안 측면에서 실제 공개 서비스 수준의 보안이 보장되는 것은 아니다.
