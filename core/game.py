"""게임 상태와 메인 플레이 루프, 충돌·퀴즈 결과 처리를 조정한다."""

import pygame
from settings import WIDTH, HEIGHT, MAX_HP, choose_cheat
from entities.player import Player
from world.generator import World
from systems.quiz import Quiz
from systems.combat import apply_damage
from systems.progression import add_score
from ui.renderer import Renderer
from core.events import handle_quiz_event
from core.display import toggle_fullscreen


# 플레이어, 월드, 퀴즈, 렌더러를 묶어 한 판의 상태를 관리한다.
class Game:
    # 새 게임 또는 저장 상태에서 월드와 플레이 상태를 구성한다.
    def __init__(self, screen, session=None, resume_state=None, local_storage=None, audio=None, cheats=None):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.local_storage = local_storage
        self.audio = audio
        self.session = session or {}
        self.subject = self.session.get("subject", "수학")
        self.cheats = choose_cheat() if cheats is None else cheats
        self.player = Player(cheats=self.cheats)
        seed = (resume_state or {}).get("world_seed")
        self.world = World(seed=seed)
        self.camera_x = 0
        # 저장 상태가 있으면 월드를 플레이어 위치까지 생성하고 진행 정보를 복원한다.
        if resume_state:
            player_x = max(0, int(resume_state.get("player_x", 60)))
            # 이어 할 위치 주변에 필요한 월드 청크를 미리 생성한다.
            while self.world.world_end < player_x + WIDTH + 700:
                self.world.update_generation(player_x)
            enemy_states = resume_state.get("enemy_states", {})
            defeated = set(resume_state.get("defeated_enemies", []))
            # 각 몹의 저장된 체력과 처치 여부를 복구한다.
            for enemy in self.world.enemies:
                saved = enemy_states.get(str(enemy.rect.x))
                # 저장된 상태가 있으면 체력과 활성 여부를 우선 적용한다.
                if saved:
                    enemy.hp = int(saved.get("hp", enemy.hp))
                    enemy.active = bool(saved.get("active", enemy.active))
                # 상세 상태가 없더라도 처치 목록에 있으면 몹을 비활성화한다.
                elif enemy.rect.x in defeated:
                    enemy.active = False
            self.player.rect.x = player_x
            self.player.rect.y = int(resume_state.get("player_y", 450))
            self.camera_x = max(0, int(resume_state.get("camera_x", 0)))
        self.quiz = Quiz(cheats=self.cheats)
        self.renderer = Renderer(screen)
        self.score = int((resume_state or {}).get("score", 0))
        self.hp = int((resume_state or {}).get("hp", MAX_HP))
        self.message = ""
        self.message_until = 0
        self.running = True
        self.game_over = False
        self.paused = False
        self.cheat_menu_open = False
        self.paused_at = 0
        self.countdown_until = pygame.time.get_ticks() + 5000
        self.damage_cooldown_until = 0
        self.last_saved = pygame.time.get_ticks()
        # 오디오가 연결된 실행에서만 게임 음악을 시작한다.
        if self.audio:
            self.audio.play_game_music()

    # 화면 알림 문구와 표시 종료 시각을 설정한다.
    def show_message(self, text, duration=2500):
        self.message = text
        self.message_until = pygame.time.get_ticks() + duration

    # 진행 상태를 저장하거나 게임 종료 기록을 랭킹에 반영한다.
    def save_state(self, finished=False, final=False):
        # 로컬 저장소가 있을 때만 진행 파일과 기록을 갱신한다.
        if self.local_storage:
            nickname = self.session.get("nickname", "player-1")
            # 게임 오버로 끝난 경우 랭킹에 기록하고 자동 저장을 지운다.
            if finished:
                self.local_storage.record_score(nickname, self.score, self.subject)
                self.local_storage.clear_save()
            # 진행 중이면 현재 위치·점수·월드·몹 상태를 저장한다.
            else:
                state = {"nickname": nickname, "subject": self.subject, "score": self.score,
                         "hp": self.hp, "world_seed": self.world.seed, "player_x": self.player.rect.x,
                         "player_y": self.player.rect.y, "camera_x": self.camera_x,
                         "enemy_states": {str(enemy.rect.x): {"hp": enemy.hp, "active": enemy.active}
                                          for enemy in self.world.enemies}}
                self.local_storage.save(state)
                # 게임 화면을 정상 종료한 경우 최종 점수도 기록한다.
                if final:
                    self.local_storage.record_score(nickname, self.score, self.subject)
            self.last_saved = pygame.time.get_ticks()
            return
    # 정답·오답 결과를 점수, 체력, 효과음, 메시지에 반영한다.
    def apply_quiz_result(self, result):
        # 제한 시간 외의 호출 등 결과가 없으면 처리하지 않는다.
        if result is None:
            return
        enemy = result.get("enemy")
        # 쉬운 몹 외의 오답에는 잠시 경고 표시를 설정한다.
        if not result["correct"] and enemy and enemy.data["difficulty"] != "easy":
            enemy.wrong_until = pygame.time.get_ticks() + 1800
        self.score = add_score(self.score, result["score"])
        self.hp = apply_damage(self.hp, result["damage"])
        # 피해가 있고 오디오가 연결된 경우 오답 효과음을 재생한다.
        if result["damage"] > 0 and self.audio:
            self.audio.play_effect(result.get("wrong_sound", "damage"))
        self.show_message(result["message"])
        # 체력이 소진되면 게임 오버 상태로 전환한다.
        if self.hp <= 0:
            self.set_game_over()

    # 게임 오버 상태를 한 번만 설정하고 종료 효과음을 재생한다.
    def set_game_over(self):
        # 이미 게임 오버라면 중복 처리를 막는다.
        if self.game_over:
            return
        self.game_over = True
        # 오디오 기능이 준비되어 있을 때 종료 효과음을 재생한다.
        if self.audio:
            self.audio.play_game_over()

    # 플레이어 근처의 활성 몹 하나를 찾아 퀴즈를 연다.
    def open_nearby_enemy(self):
        nearby = self.player.rect.inflate(60, 45)
        # 월드의 몹을 확인해 상호작용 범위에 들어온 적을 찾는다.
        for enemy in self.world.enemies:
            # 살아 있는 몹의 충돌 범위 안에 들어오면 퀴즈를 연다.
            if enemy.active and nearby.colliderect(enemy.rect):
                self.quiz.open(enemy)
                return

    # 창·키보드 입력을 게임 상태, 이동, 일시 정지 동작에 연결한다.
    def handle_event(self, event):
        # 창 닫기 요청은 게임 반복을 끝낸다.
        if event.type == pygame.QUIT:
            self.running = False
            return
        # F11은 전체 화면을 전환하고 렌더러에 새 화면 표면을 전달한다.
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            self.screen = toggle_fullscreen(self.screen)
            self.renderer.screen = self.screen
            return
        # F9를 눌러 치트 메뉴를 열고 숫자 키로 프리셋을 적용한다.
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F9:
            self.cheat_menu_open = not self.cheat_menu_open
            return
        if self.cheat_menu_open:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_F9):
                    self.cheat_menu_open = False
                elif pygame.K_0 <= event.key <= pygame.K_5:
                    code = "" if event.key == pygame.K_0 else str(event.key - pygame.K_0)
                    self.cheats.clear()
                    self.cheats.update(choose_cheat(code))
                    label = "일반 모드" if not self.cheats else f"치트 {code} 적용"
                    self.show_message(label)
                    self.cheat_menu_open = False
            return
        # 게임 오버 화면에서는 ESC로만 게임을 종료한다.
        if self.game_over:
            # ESC 입력은 게임 루프를 종료한다.
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False
            return
        # ESC는 일시 정지를 토글하고 멈춘 시간만큼 제한 시간을 보정한다.
        # ESC를 누르면 정지 상태를 반전하고 경과 시간을 기록한다.
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            now = pygame.time.get_ticks()
            self.paused = not self.paused
            # 멈추는 순간의 시각을 기록해 재개 때 시간 제한을 조정한다.
            if self.paused:
                self.paused_at = now
            # 재개 시 정지된 시간을 타이머에 더해 남은 시간을 보존한다.
            else:
                paused_duration = now - self.paused_at
                # 카운트다운 중 정지했다면 남은 대기 시간도 뒤로 미룬다.
                if now < self.countdown_until:
                    self.countdown_until += paused_duration
                # 퀴즈 시간 제한도 일시 정지한 시간만큼 연장한다.
                if self.quiz.active:
                    self.quiz.started += paused_duration
                self.paused_at = 0
            # 음악과 효과음도 게임 일시 정지 상태를 따른다.
            if self.audio:
                self.audio.set_paused(self.paused)
            return
        # 일시 정지 중에는 게임 내 입력을 무시한다.
        # 정지 중에는 이동 및 상호작용 입력을 받지 않는다.
        if self.paused:
            return
        # 시작 카운트다운이 끝나기 전에는 플레이 입력을 받지 않는다.
        if pygame.time.get_ticks() < self.countdown_until:
            return
        # 퀴즈가 열린 동안 입력은 퀴즈 이벤트 처리기로 전달한다.
        if self.quiz.active:
            handle_quiz_event(event, self.quiz, self.apply_quiz_result)
            return
        # 플레이 중 키 입력으로 점프나 주변 몹 상호작용을 수행한다.
        if event.type == pygame.KEYDOWN:
            # 스페이스는 점프를 시작한다.
            if event.key == pygame.K_SPACE:
                self.player.jump()
            # E 키는 가까운 몹과 문제를 시작한다.
            elif event.key == pygame.K_e:
                self.open_nearby_enemy()

    # 한 프레임의 이동, 충돌, 월드 생성, 체력 상태를 갱신한다.
    def update(self):
        # 플레이가 멈춰야 하는 상태에서는 월드 갱신을 건너뛴다.
        if self.game_over or self.paused or self.quiz.active or pygame.time.get_ticks() < self.countdown_until:
            return
        self.player.update(pygame.key.get_pressed(), self.world)
        now = pygame.time.get_ticks()
        # 피해 무적 시간이 끝났을 때 가시 충돌을 확인한다.
        if now >= self.damage_cooldown_until:
            # 각 가시 묶음의 충돌 영역을 검사한다.
            for spike in self.world.spikes:
                spike_rect = pygame.Rect(spike["x"], spike["y"] - 14, spike["count"] * 13, 14)
                # 충돌이 있을 때만 피해 판정과 반동을 적용한다.
                if self.player.rect.colliderect(spike_rect):
                    # 무피해 설정이 없으면 가시 피해를 적용한다.
                    if not self.cheats.get("no_damage"):
                        self.hp = max(0, self.hp - 1)
                        # 실제 피해가 반영되면 효과음을 출력한다.
                        if self.audio:
                            self.audio.play_effect("damage")
                    self.damage_cooldown_until = now + 900
                    self.player.rect.bottom = min(self.player.rect.bottom, 500)
                    self.player.vy = -4
                    break
        target_x = max(0, self.player.rect.x - int(WIDTH * .55))
        self.camera_x = max(self.camera_x, target_x)
        self.world.update_generation(self.player.rect.x)
        # 플레이어가 활성 몹과 닿으면 해당 몹의 퀴즈를 연다.
        for enemy in self.world.enemies:
            # 활성 몹과 충돌한 순간 문제를 열고 중복 진입을 막는다.
            if enemy.active and self.player.rect.colliderect(enemy.rect):
                self.quiz.open(enemy)
                break
        # 화면 아래로 떨어진 플레이어를 시작 위치로 되돌린다.
        if self.player.rect.top > HEIGHT:
            self.player.reset_position()
            self.camera_x = 0
            # 무피해 설정이 꺼진 경우에만 추락 피해를 준다.
            if not self.cheats.get("no_damage"):
                self.hp = max(0, self.hp - 10)
        # 낙하나 가시 피해로 체력이 소진되면 게임을 끝낸다.
        if self.hp <= 0:
            self.set_game_over()

    # 현재 월드와 HUD 위에 퀴즈·일시 정지·종료 오버레이를 그린다.
    def draw(self):
        self.renderer.draw_background(self.camera_x)
        self.renderer.draw_world(self.world, self.camera_x)
        self.renderer.draw_player(self.player, self.camera_x, rotation=90 if self.game_over else 0)
        message = self.message if pygame.time.get_ticks() < self.message_until else ""
        self.renderer.draw_hud(self.hp, self.score, message)
        self.renderer.draw_quiz(self.quiz)
        # 우선순위에 따라 한 가지 상태 오버레이를 표시한다.
        if self.game_over:
            self.renderer.draw_game_over(self.score)
        # 일시 정지 상태에는 재개 안내를 표시한다.
        elif self.paused:
            self.renderer.draw_pause_overlay()
        # 시작 대기 중에는 카운트다운 숫자를 표시한다.
        elif pygame.time.get_ticks() < self.countdown_until:
            seconds = max(1, (self.countdown_until - pygame.time.get_ticks() + 999) // 1000)
            self.renderer.draw_start_countdown(seconds)
        if self.cheat_menu_open:
            self._draw_cheat_menu()

    def _draw_cheat_menu(self):
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        self.screen.blit(shade, (0, 0))
        panel = pygame.Rect(WIDTH // 2 - 220, HEIGHT // 2 - 150, 440, 300)
        pygame.draw.rect(self.screen, (250, 249, 239), panel, border_radius=14)
        pygame.draw.rect(self.screen, (39, 54, 67), panel, 3, border_radius=14)
        lines = [
            ("치트 선택", (39, 54, 67), 32),
            ("1 무피해   2 초고속   3 높이 점프", (39, 54, 67), 20),
            ("4 초고속 + 높이 점프", (39, 54, 67), 20),
            ("5 전체 치트   0 치트 끄기", (39, 54, 67), 20),
            ("숫자 키로 적용 · F9 또는 ESC로 닫기", (80, 90, 100), 17),
        ]
        y = panel.y + 30
        for text, color, size in lines:
            font = pygame.font.SysFont("malgungothic", size, bold=size == 32)
            surface = font.render(text, True, color)
            self.screen.blit(surface, surface.get_rect(center=(panel.centerx, y + surface.get_height() // 2)))
            y += surface.get_height() + 20
    # 입력·갱신·저장·렌더링을 반복하고 종료 시 최종 상태를 저장한다.
    def run(self):
        # 실행 상태가 유지되는 동안 매 프레임 게임 작업을 처리한다.
        while self.running:
            self.clock.tick(60)
            # 이번 프레임의 모든 입력 이벤트를 처리한다.
            for event in pygame.event.get():
                # 배경 음악 이벤트는 오디오 관리자에서 먼저 소비한다.
                if self.audio and self.audio.handle_music_event(event):
                    continue
                self.handle_event(event)
            self.update()
            # 정지 중이 아닐 때만 퀴즈 시간 초과를 판정한다.
            if not self.paused:
                self.apply_quiz_result(self.quiz.check_timeout())
            # 10초마다 중간 진행 상태를 자동 저장한다.
            if pygame.time.get_ticks() - self.last_saved >= 10_000:
                self.save_state()
            self.draw()
            pygame.display.flip()
        self.save_state(finished=self.game_over, final=True)
