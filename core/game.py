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


class Game:
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
        if resume_state:
            player_x = max(0, int(resume_state.get("player_x", 60)))
            while self.world.world_end < player_x + WIDTH + 700:
                self.world.update_generation(player_x)
            enemy_states = resume_state.get("enemy_states", {})
            defeated = set(resume_state.get("defeated_enemies", []))
            for enemy in self.world.enemies:
                saved = enemy_states.get(str(enemy.rect.x))
                if saved:
                    enemy.hp = int(saved.get("hp", enemy.hp))
                    enemy.active = bool(saved.get("active", enemy.active))
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
        self.paused_at = 0
        self.countdown_until = pygame.time.get_ticks() + 5000
        self.damage_cooldown_until = 0
        self.last_saved = pygame.time.get_ticks()
        if self.audio:
            self.audio.play_game_music()

    def show_message(self, text, duration=2500):
        self.message = text
        self.message_until = pygame.time.get_ticks() + duration

    def save_state(self, finished=False, final=False):
        if self.local_storage:
            nickname = self.session.get("nickname", "player-1")
            if finished:
                self.local_storage.record_score(nickname, self.score, self.subject)
                self.local_storage.clear_save()
            else:
                state = {"nickname": nickname, "subject": self.subject, "score": self.score,
                         "hp": self.hp, "world_seed": self.world.seed, "player_x": self.player.rect.x,
                         "player_y": self.player.rect.y, "camera_x": self.camera_x,
                         "enemy_states": {str(enemy.rect.x): {"hp": enemy.hp, "active": enemy.active}
                                          for enemy in self.world.enemies}}
                self.local_storage.save(state)
                if final:
                    self.local_storage.record_score(nickname, self.score, self.subject)
            self.last_saved = pygame.time.get_ticks()
            return
    def apply_quiz_result(self, result):
        if result is None:
            return
        enemy = result.get("enemy")
        if not result["correct"] and enemy and enemy.data["difficulty"] != "easy":
            enemy.wrong_until = pygame.time.get_ticks() + 1800
        self.score = add_score(self.score, result["score"])
        self.hp = apply_damage(self.hp, result["damage"])
        if result["damage"] > 0 and self.audio:
            self.audio.play_effect(result.get("wrong_sound", "damage"))
        self.show_message(result["message"])
        if self.hp <= 0:
            self.set_game_over()

    def set_game_over(self):
        if self.game_over:
            return
        self.game_over = True
        if self.audio:
            self.audio.play_game_over()

    def open_nearby_enemy(self):
        nearby = self.player.rect.inflate(60, 45)
        for enemy in self.world.enemies:
            if enemy.active and nearby.colliderect(enemy.rect):
                self.quiz.open(enemy)
                return

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            self.screen = toggle_fullscreen(self.screen)
            self.renderer.screen = self.screen
            return
        if self.game_over:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            now = pygame.time.get_ticks()
            self.paused = not self.paused
            if self.paused:
                self.paused_at = now
            else:
                paused_duration = now - self.paused_at
                if now < self.countdown_until:
                    self.countdown_until += paused_duration
                if self.quiz.active:
                    self.quiz.started += paused_duration
                self.paused_at = 0
            if self.audio:
                self.audio.set_paused(self.paused)
            return
        if self.paused:
            return
        if pygame.time.get_ticks() < self.countdown_until:
            return
        if self.quiz.active:
            handle_quiz_event(event, self.quiz, self.apply_quiz_result)
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.player.jump()
            elif event.key == pygame.K_e:
                self.open_nearby_enemy()

    def update(self):
        if self.game_over or self.paused or self.quiz.active or pygame.time.get_ticks() < self.countdown_until:
            return
        self.player.update(pygame.key.get_pressed(), self.world)
        now = pygame.time.get_ticks()
        if now >= self.damage_cooldown_until:
            for spike in self.world.spikes:
                spike_rect = pygame.Rect(spike["x"], spike["y"] - 14, spike["count"] * 13, 14)
                if self.player.rect.colliderect(spike_rect):
                    if not self.cheats.get("no_damage"):
                        self.hp = max(0, self.hp - 1)
                        if self.audio:
                            self.audio.play_effect("damage")
                    self.damage_cooldown_until = now + 900
                    self.player.rect.bottom = min(self.player.rect.bottom, 500)
                    self.player.vy = -4
                    break
        target_x = max(0, self.player.rect.x - int(WIDTH * .55))
        self.camera_x = max(self.camera_x, target_x)
        self.world.update_generation(self.player.rect.x)
        for enemy in self.world.enemies:
            if enemy.active and self.player.rect.colliderect(enemy.rect):
                self.quiz.open(enemy)
                break
        if self.player.rect.top > HEIGHT:
            self.player.reset_position()
            self.camera_x = 0
            if not self.cheats.get("no_damage"):
                self.hp = max(0, self.hp - 10)
        if self.hp <= 0:
            self.set_game_over()

    def draw(self):
        self.renderer.draw_background(self.camera_x)
        self.renderer.draw_world(self.world, self.camera_x)
        self.renderer.draw_player(self.player, self.camera_x, rotation=90 if self.game_over else 0)
        message = self.message if pygame.time.get_ticks() < self.message_until else ""
        self.renderer.draw_hud(self.hp, self.score, message)
        self.renderer.draw_quiz(self.quiz)
        if self.game_over:
            self.renderer.draw_game_over(self.score)
        elif self.paused:
            self.renderer.draw_pause_overlay()
        elif pygame.time.get_ticks() < self.countdown_until:
            seconds = max(1, (self.countdown_until - pygame.time.get_ticks() + 999) // 1000)
            self.renderer.draw_start_countdown(seconds)
    def run(self):
        while self.running:
            self.clock.tick(60)
            for event in pygame.event.get():
                if self.audio and self.audio.handle_music_event(event):
                    continue
                self.handle_event(event)
            self.update()
            if not self.paused:
                self.apply_quiz_result(self.quiz.check_timeout())
            if pygame.time.get_ticks() - self.last_saved >= 10_000:
                self.save_state()
            self.draw()
            pygame.display.flip()
        self.save_state(finished=self.game_over, final=True)
