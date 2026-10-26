import pygame
from settings import WIDTH, HEIGHT, SKY, MOUNTAIN, GRASS, WHITE, YELLOW
from core.display import toggle_fullscreen


class Menu:
    def __init__(self, screen, local_mode=False, audio=None):
        self.screen = screen
        self.local_mode = local_mode
        self.audio = audio
        self.clock = pygame.time.Clock()
        self.page = "main"
        self.selected = 0
        self.buttons = []
        self.running = True
        self.font = pygame.font.SysFont("malgungothic", 22)
        self.small = pygame.font.SysFont("malgungothic", 16)
        self.title_font = pygame.font.SysFont("malgungothic", 52, bold=True)

    def _text(self, text, pos, font, color, center=True):
        surface = font.render(str(text), True, color)
        rect = surface.get_rect(center=pos) if center else surface.get_rect(topleft=pos)
        self.screen.blit(surface, rect)

    def _background(self):
        self.screen.fill(SKY)
        for i in range(6):
            x = i * 220 - 70
            pygame.draw.polygon(self.screen, MOUNTAIN,
                                [(x, 430), (x + 110, 245 + (i % 3) * 28), (x + 250, 430)])
        pygame.draw.rect(self.screen, (132, 183, 116), (0, 420, WIDTH, HEIGHT - 420))
        pygame.draw.rect(self.screen, (87, 151, 83), (0, 420, WIDTH, 8))
        panel = pygame.Surface((520, 500), pygame.SRCALPHA)
        panel.fill((17, 31, 49, 224))
        self.screen.blit(panel, (240, 45))

    def _button(self, label, y, index, subtitle=None):
        rect = pygame.Rect(330, y, 340, 48 if subtitle is None else 56)
        active = index == self.selected
        fill = (255, 220, 70) if active else (238, 242, 247)
        ink = (30, 43, 57) if active else (47, 62, 78)
        pygame.draw.rect(self.screen, fill, rect, border_radius=8)
        if active:
            pygame.draw.rect(self.screen, WHITE, rect, 2, border_radius=8)
        if subtitle:
            self._text(label, (rect.centerx, rect.y + 18), self.font, ink)
            self._text(subtitle, (rect.centerx, rect.y + 40), self.small, ink)
        else:
            self._text(label, rect.center, self.font, ink)
        self.buttons.append((rect, index))

    def _draw_main(self):
        self._text("나 혼자만 1등급", (500, 112), self.title_font, WHITE)
        self._text("SOLO SAT", (500, 163), self.font, YELLOW)
        self._text("STUDY · SURVIVE · RANK UP", (500, 193), self.small, (204, 218, 232))
        self.buttons = []
        self._button("새 게임", 235, 0, "새로운 도전을 시작합니다")
        self._button("불러오기", 305, 1, "저장된 게임 이어 하기")
        self._button("랭킹", 375, 2)
        self._button("종료", 435, 3)
        self._text("↑/↓ 선택 · Enter 실행 · 마우스 클릭", (500, 510), self.small, (211, 220, 230))

    def _draw_load(self):
        self._text("게임 불러오기", (500, 112), self.title_font, WHITE)
        self._text("저장 기록을 선택하세요", (500, 166), self.font, (211, 220, 230))
        self.buttons = []
        if self.local_mode:
            self._button("LOCAL SAVE", 275, 0, "이 컴퓨터의 자동 저장")
            self._button("뒤로", 440, 1)
        else:
            for i, slot in enumerate(("SLOT 1", "SLOT 2", "SLOT 3")):
                self._button(slot, 230 + i * 75, i, "서버의 저장 기록")
            self._button("뒤로", 465, 3)

    def draw(self):
        self._background()
        if self.page == "main":
            self._draw_main()
        else:
            self._draw_load()

    def _activate(self, index):
        if self.page == "main":
            if index == 0:
                return "new_game"
            if index == 1:
                self.page, self.selected = "load", 0
            elif index == 2:
                return "leaderboard"
            elif index == 3:
                return "quit"
            return None
        back_index = 1 if self.local_mode else 3
        if index == back_index:
            self.page, self.selected = "main", 0
            return None
        return "load_game"

    def run(self):
        while self.running:
            self.clock.tick(60)
            self.draw()
            pygame.display.flip()
            for event in pygame.event.get():
                if self.audio and self.audio.handle_music_event(event):
                    continue
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        self.screen = toggle_fullscreen(self.screen)
                    elif event.key == pygame.K_ESCAPE:
                        if self.page == "main":
                            return "quit"
                        self.page, self.selected = "main", 0
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self.selected = max(0, self.selected - 1)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        max_index = 3 if self.page == "main" else (1 if self.local_mode else 3)
                        self.selected = min(max_index, self.selected + 1)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.audio:
                            self.audio.play_effect("menu")
                        result = self._activate(self.selected)
                        if result:
                            return result
                elif event.type == pygame.MOUSEMOTION:
                    for rect, index in self.buttons:
                        if rect.collidepoint(event.pos):
                            self.selected = index
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, index in self.buttons:
                        if rect.collidepoint(event.pos):
                            if self.audio:
                                self.audio.play_effect("menu")
                            result = self._activate(index)
                            if result:
                                return result
        return "quit"
