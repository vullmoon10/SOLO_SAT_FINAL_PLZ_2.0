"""타이틀 메뉴와 저장 불러오기 화면의 입력·표시를 관리한다."""

import pygame
from settings import WIDTH, HEIGHT, SKY, MOUNTAIN, GRASS, WHITE, YELLOW
from core.display import toggle_fullscreen


# 타이틀 화면의 메뉴, 저장 불러오기, 키보드·마우스 조작을 관리한다.
class Menu:
    # 메뉴 화면에 필요한 표시 상태와 입력 상태를 초기화한다.
    def __init__(self, screen, audio=None):
        self.screen = screen
        self.audio = audio
        self.clock = pygame.time.Clock()
        self.page = "main"
        self.selected = 0
        self.buttons = []
        self.running = True
        self.font = pygame.font.SysFont("malgungothic", 22)
        self.small = pygame.font.SysFont("malgungothic", 16)
        self.title_font = pygame.font.SysFont("malgungothic", 52, bold=True)

    # 텍스트를 지정 위치에 가운데 또는 왼쪽 기준으로 그린다.
    def _text(self, text, pos, font, color, center=True):
        surface = font.render(str(text), True, color)
        rect = surface.get_rect(center=pos) if center else surface.get_rect(topleft=pos)
        self.screen.blit(surface, rect)

    # 메뉴 배경의 산, 지면, 반투명 패널을 그린다.
    def _background(self):
        self.screen.fill(SKY)
        # 배경 산을 나열해 메뉴 화면의 풍경을 만든다.
        for i in range(6):
            x = i * 220 - 70
            pygame.draw.polygon(self.screen, MOUNTAIN,
                                [(x, 430), (x + 110, 245 + (i % 3) * 28), (x + 250, 430)])
        pygame.draw.rect(self.screen, (132, 183, 116), (0, 420, WIDTH, HEIGHT - 420))
        pygame.draw.rect(self.screen, (87, 151, 83), (0, 420, WIDTH, 8))
        panel = pygame.Surface((520, 500), pygame.SRCALPHA)
        panel.fill((17, 31, 49, 224))
        self.screen.blit(panel, (240, 45))

    # 선택 상태와 부제에 맞춰 메뉴 버튼을 그리고 클릭 영역을 기록한다.
    def _button(self, label, y, index, subtitle=None):
        rect = pygame.Rect(330, y, 340, 48 if subtitle is None else 56)
        active = index == self.selected
        fill = (255, 220, 70) if active else (238, 242, 247)
        ink = (30, 43, 57) if active else (47, 62, 78)
        pygame.draw.rect(self.screen, fill, rect, border_radius=8)
        # 현재 선택된 버튼은 테두리로 강조한다.
        if active:
            pygame.draw.rect(self.screen, WHITE, rect, 2, border_radius=8)
        # 부제가 있으면 제목과 작은 안내 문구를 함께 표시한다.
        if subtitle:
            self._text(label, (rect.centerx, rect.y + 18), self.font, ink)
            self._text(subtitle, (rect.centerx, rect.y + 40), self.small, ink)
        # 부제가 없으면 버튼 제목만 가운데에 표시한다.
        else:
            self._text(label, rect.center, self.font, ink)
        self.buttons.append((rect, index))

    # 새 게임·불러오기·랭킹·종료 항목이 있는 첫 메뉴를 그린다.
    def _draw_main(self):
        self._text("나 혼자만 1등급", (500, 112), self.title_font, WHITE)
        self._text("SOLO SAT 2.0.3", (500, 163), self.font, YELLOW)
        self._text("STUDY · SURVIVE · RANK UP", (500, 193), self.small, (204, 218, 232))
        self.buttons = []
        self._button("새 게임", 235, 0, "새로운 도전을 시작합니다")
        self._button("불러오기", 305, 1, "저장된 게임 이어 하기")
        self._button("랭킹", 375, 2)
        self._button("종료", 435, 3)
        self._text("↑/↓ 선택 · Enter 실행 · 마우스 클릭", (500, 510), self.small, (211, 220, 230))

    # 자동 저장 불러오기와 뒤로 가기 항목을 그린다.
    def _draw_load(self):
        self._text("게임 불러오기", (500, 112), self.title_font, WHITE)
        self._text("저장 기록을 선택하세요", (500, 166), self.font, (211, 220, 230))
        self.buttons = []
        self._button("LOCAL SAVE", 275, 0, "이 컴퓨터의 자동 저장")
        self._button("뒤로", 440, 1)

    # 현재 메뉴 페이지에 알맞은 화면 요소를 렌더링한다.
    def draw(self):
        self._background()
        # 첫 페이지와 불러오기 페이지에 맞는 메뉴 구성을 선택한다.
        if self.page == "main":
            self._draw_main()
        # 메인 페이지가 아니면 저장 불러오기 화면을 그린다.
        else:
            self._draw_load()

    # 선택된 메뉴 번호를 게임 동작 이름으로 바꾸거나 페이지를 전환한다.
    def _activate(self, index):
        # 첫 페이지에서는 메뉴 항목별 동작을 반환한다.
        if self.page == "main":
            # 새 게임은 즉시 게임 화면으로 넘어가도록 동작 이름을 돌려준다.
            if index == 0:
                return "new_game"
            # 불러오기를 선택하면 저장 선택 페이지로 전환한다.
            if index == 1:
                self.page, self.selected = "load", 0
            # 랭킹은 출력 동작으로 전달한다.
            elif index == 2:
                return "leaderboard"
            # 종료는 메인 루프에서 처리할 동작 이름으로 전달한다.
            elif index == 3:
                return "quit"
            return None
        back_index = 1
        # 뒤로 버튼은 첫 페이지로 돌아간다.
        if index == back_index:
            self.page, self.selected = "main", 0
            return None
        return "load_game"

    # 메뉴를 반복 표시하고 사용자 선택 결과를 호출자에게 반환한다.
    def run(self):
        # 메뉴가 실행 중인 동안 프레임을 그리고 사용자 입력을 받는다.
        while self.running:
            self.clock.tick(60)
            self.draw()
            pygame.display.flip()
            # 현재 프레임에서 발생한 모든 사용자 이벤트를 처리한다.
            for event in pygame.event.get():
                # 음악 전환 이벤트는 오디오 관리자에 맡기고 메뉴 입력과 분리한다.
                if self.audio and self.audio.handle_music_event(event):
                    continue
                # 창 닫기 이벤트는 메뉴 실행 결과를 종료로 반환한다.
                if event.type == pygame.QUIT:
                    return "quit"
                # 키 입력을 페이지 전환, 선택 이동, 항목 실행으로 처리한다.
                if event.type == pygame.KEYDOWN:
                    # F11은 메뉴에서도 전체 화면을 전환한다.
                    if event.key == pygame.K_F11:
                        self.screen = toggle_fullscreen(self.screen)
                    # ESC는 메인 메뉴면 종료하고 하위 페이지면 메인으로 돌아간다.
                    elif event.key == pygame.K_ESCAPE:
                        # 메인 페이지의 ESC 입력은 메뉴를 끝낸다.
                        if self.page == "main":
                            return "quit"
                        self.page, self.selected = "main", 0
                    # 위쪽 키는 현재 선택 위치를 한 항목 위로 이동한다.
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self.selected = max(0, self.selected - 1)
                    # 아래쪽 키는 페이지의 마지막 항목을 넘지 않게 이동한다.
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        max_index = 3 if self.page == "main" else 1
                        self.selected = min(max_index, self.selected + 1)
                    # Enter나 Space는 현재 선택 메뉴를 실행한다.
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        # 항목 실행 시 메뉴 효과음이 준비된 경우 재생한다.
                        if self.audio:
                            self.audio.play_effect("menu")
                        result = self._activate(self.selected)
                        # 실제 화면 전환이나 종료 요청이 반환되면 메뉴 루프를 끝낸다.
                        if result:
                            return result
                # 마우스 위치가 버튼 위에 오면 선택 표시를 옮긴다.
                elif event.type == pygame.MOUSEMOTION:
                    # 현재 페이지에 표시된 버튼마다 포인터 위치를 확인한다.
                    for rect, index in self.buttons:
                        # 버튼 안으로 포인터가 들어오면 그 항목을 선택한다.
                        if rect.collidepoint(event.pos):
                            self.selected = index
                # 왼쪽 클릭으로 버튼 동작을 실행한다.
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # 클릭한 버튼의 활성 영역을 찾는다.
                    for rect, index in self.buttons:
                        # 버튼을 눌렀을 때 소리와 메뉴 동작을 적용한다.
                        if rect.collidepoint(event.pos):
                            # 오디오가 연결된 경우 클릭 피드백을 재생한다.
                            if self.audio:
                                self.audio.play_effect("menu")
                            result = self._activate(index)
                            # 하위 화면으로 이동하거나 종료할 결과가 있으면 반환한다.
                            if result:
                                return result
        return "quit"
