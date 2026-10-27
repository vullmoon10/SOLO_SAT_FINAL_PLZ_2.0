"""게임 상태와 메인 플레이 루프, 충돌·퀴즈 결과 처리를 조정한다."""

import pygame
from settings import WIDTH, HEIGHT, MAX_HP, GROUND_Y, choose_cheat, random_physics
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
        self.physics = ((resume_state or {}).get("physics")
                        or self.session.get("physics") or random_physics())
        if self.physics.get("move_speed", 0) < 12:
            self.physics["move_speed"] = random_physics()["move_speed"]
        self.session["physics"] = self.physics
        self.player = Player(cheats=self.cheats, physics=self.physics)
        self.collected_items = set((resume_state or {}).get("collected_items", []))
        now = pygame.time.get_ticks()
        self.player.speed_boost_until = now + int((resume_state or {}).get("speed_boost_remaining", 0))
        self.player.jump_boost_until = now + int((resume_state or {}).get("jump_boost_remaining", 0))
        seed = (resume_state or {}).get("world_seed", self.session.get("world_seed"))
        self.world = World(seed=seed, infinite=self.cheats.get("infinite_map", False))
        self.trash_mob_rate = max(0, min(100, int((resume_state or {}).get("trash_mob_rate", 50))))
        for item in self.world.items:
            if item["id"] in self.collected_items:
                item["collected"] = True
        self.camera_x = 0
        self.camera_y = 0
        # 저장된 생성 범위까지 같은 시드로 재생성해 양쪽 진행 상태를 복원한다.
        if resume_state:
            player_x = int(resume_state.get("player_x", 60))
            if self.world.infinite:
                saved_world_start = int(resume_state.get("world_start", min(0, player_x - 700)))
                saved_world_end = int(resume_state.get("world_end", player_x + WIDTH + 700))
                while self.world.world_start > saved_world_start:
                    self.world.generate_left_chunk()
                while self.world.world_end < saved_world_end:
                    self.world.generate_chunk(self.world.world_end, 5)
                while (player_x + WIDTH + 700 > self.world.world_end
                       or player_x - 700 < self.world.world_start):
                    self.world.update_generation(player_x)
            else:
                player_x = min(player_x, self.world.active_end - self.player.rect.width)
            enemy_states = resume_state.get("enemy_states", {})
            moving_platform_states = resume_state.get("moving_platform_states", {})
            trash_mob_states = resume_state.get("trash_mob_states", {})
            defeated = set(resume_state.get("defeated_enemies", []))
            # 각 몹의 저장된 체력과 처치 여부를 복구한다.
            for enemy in self.world.enemies:
                saved = enemy_states.get(str(enemy.spawn_x), enemy_states.get(str(enemy.rect.x)))
                # 저장된 상태가 있으면 체력과 활성 여부를 우선 적용한다.
                if saved:
                    enemy.hp = int(saved.get("hp", enemy.hp))
                    enemy.active = bool(saved.get("active", enemy.active))
                    enemy.rect.x = int(saved.get("x", enemy.rect.x))
                    enemy.direction = int(saved.get("direction", enemy.direction))
                # 상세 상태가 없더라도 처치 목록에 있으면 몹을 비활성화한다.
                elif enemy.spawn_x in defeated or enemy.rect.x in defeated:
                    enemy.active = False
            for platform in self.world.moving_platforms:
                saved = moving_platform_states.get(str(platform.spawn_x))
                if saved:
                    platform.rect.x = int(saved.get("x", platform.rect.x))
                    platform.direction = int(saved.get("direction", platform.direction))
            for mob in self.world.trash_mobs:
                saved = trash_mob_states.get(mob.mob_id)
                if saved:
                    mob.rect.x = int(saved.get("x", mob.rect.x))
                    mob.direction = int(saved.get("direction", mob.direction))
                    mob.active = bool(saved.get("active", mob.active))
                    mob.hp = int(saved.get("hp", mob.hp))
                    mob.defeated = bool(saved.get("defeated", not mob.active))
            self.player.rect.x = player_x
            self.player.rect.y = int(resume_state.get("player_y", 450))
            self.player.facing = int(resume_state.get("player_facing", 1))
            self.player.horizontal_velocity = float(resume_state.get("player_speed", 0))
            camera_limit = max(self.world.active_start, self.world.active_end - WIDTH)
            self.camera_x = min(camera_limit,
                                max(self.world.active_start, int(resume_state.get("camera_x", 0))))
            self.camera_y = max(0, int(resume_state.get("camera_y", 0)))
        self.update_trash_mob_population()
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
        self.dragging_trash_slider = False
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

    # 잡몹 생성 밀도에 따라 후보별로 결정적으로 활성화한다.
    def update_trash_mob_population(self):
        for mob in self.world.trash_mobs:
            stable_bucket = (int(mob.mob_id) * 2_654_435_761) % 100
            mob.set_enabled(stable_bucket < self.trash_mob_rate)

    # 화면 슬라이더 좌표를 잡몹 생성 밀도로 바꾼다.
    def set_trash_mob_rate_from_x(self, x):
        left = WIDTH - 253
        width = 216
        ratio = max(0.0, min(1.0, (x - left) / width))
        rate = round(ratio * 100)
        if rate != self.trash_mob_rate:
            self.trash_mob_rate = rate
            self.update_trash_mob_population()
            self.show_message(f"잡몹 생성 밀도 {rate}%")

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
                now = pygame.time.get_ticks()
                state = {"nickname": nickname, "subject": self.subject, "score": self.score,
                         "hp": self.hp, "world_seed": self.world.seed, "physics": self.physics,
                         "player_x": self.player.rect.x,
                         "world_start": self.world.world_start, "world_end": self.world.world_end,
                         "player_y": self.player.rect.y, "player_facing": self.player.facing,
                         "player_speed": self.player.horizontal_velocity,
                         "camera_x": self.camera_x, "camera_y": self.camera_y,
                         "collected_items": sorted(self.collected_items),
                         "speed_boost_remaining": max(0, self.player.speed_boost_until - now),
                         "jump_boost_remaining": max(0, self.player.jump_boost_until - now),
                         "trash_mob_rate": self.trash_mob_rate,
                         "enemy_states": {str(enemy.spawn_x): {"hp": enemy.hp, "active": enemy.active,
                                                                "x": enemy.rect.x, "direction": enemy.direction}
                                          for enemy in self.world.enemies},
                         "moving_platform_states": {str(platform.spawn_x): {
                             "x": platform.rect.x, "direction": platform.direction}
                             for platform in self.world.moving_platforms},
                         "trash_mob_states": {mob.mob_id: {
                             "x": mob.rect.x, "direction": mob.direction, "active": mob.active,
                             "hp": mob.hp, "defeated": mob.defeated}
                             for mob in self.world.trash_mobs}}
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

    # HUD와 같은 공식으로 운동에너지와 위치에너지를 계산한다.
    def kinetic_energy(self):
        return 0.5 * (self.player.horizontal_velocity ** 2 + self.player.vy ** 2)

    def potential_energy(self):
        height = max(0, GROUND_Y - self.player.rect.bottom)
        return height * self.physics["gravity"]

    def mechanical_energy(self):
        return self.kinetic_energy() + self.potential_energy()

    # 역학적 에너지가 기준 이상이면 문제 몹을 바로 처치한다.
    def handle_problem_mob_contact(self, enemy, impact_energy=None):
        energy = self.mechanical_energy() if impact_energy is None else impact_energy
        if round(energy, 1) < 100:
            self.quiz.open(enemy)
            return
        enemy.defeat()
        self.score += enemy.data["score"]
        self.show_message(f"역학적 에너지 충돌! 문제몹 처치 · Ek+Ep {energy:.1f}")

    # 플레이어와 닿은 아이템을 획득하고 점수·체력·시간제 강화 효과를 적용한다.
    def collect_items(self):
        now = pygame.time.get_ticks()
        for item in self.world.items:
            if item["collected"] or not self.player.rect.colliderect(item["rect"]):
                continue
            item["collected"] = True
            self.collected_items.add(item["id"])
            if item["type"] == "coin":
                self.score += 50
                message = "코인 +50"
            elif item["type"] == "heart":
                before = self.hp
                self.hp = min(MAX_HP, self.hp + 20)
                message = f"체력 +{self.hp - before}" if self.hp > before else "체력이 이미 가득합니다"
            elif item["type"] == "speed":
                self.player.speed_boost_until = max(now, self.player.speed_boost_until) + 8000
                message = "속도 강화 8초"
            else:
                self.player.jump_boost_until = max(now, self.player.jump_boost_until) + 8000
                message = "점프 강화 8초"
            self.show_message(message)

    # 클릭 공격은 잡몹만 처치하고 문제 몹에는 영향을 주지 않는다.
    def swing_stick(self, mode="normal"):
        now = pygame.time.get_ticks()
        if mode == "normal":
            if now < self.player.attack_cooldown_until:
                return
            self.player.attack_cooldown_until = now + 420
        self.player.swing_until = now + 260
        self.player.stick_mode = mode
        self.player.special_effect_until = now + 300
        if mode == "K":
            damage = round(abs(self.player.horizontal_velocity) * 3)
        elif mode == "P":
            height = max(0, GROUND_Y - self.player.rect.bottom)
            damage = round(height * 1.2)
        else:
            damage = 15
        if damage <= 0:
            return
        if mode == "P":
            hitbox = self.player.rect.inflate(180, 130)
        elif self.player.facing > 0:
            hitbox = pygame.Rect(self.player.rect.right - 2, self.player.rect.top + 5, 72, 32)
        else:
            hitbox = pygame.Rect(self.player.rect.left - 70, self.player.rect.top + 5, 72, 32)
        defeated = 0
        damaged = 0
        for mob in self.world.trash_mobs:
            if mob.active and hitbox.colliderect(mob.rect):
                damaged += 1
                defeated += int(mob.take_damage(damage))
        if defeated:
            self.score += defeated * 25
            self.show_message(f"잡몹 처치 +{defeated * 25} · 피해 {damage}")
        elif damaged:
            self.show_message(f"잡몹 피해 {damage}")

    # 플레이어 근처의 활성 몹 하나를 찾아 퀴즈를 연다.
    def open_nearby_enemy(self):
        nearby = self.player.rect.inflate(60, 45)
        # 월드의 몹을 확인해 상호작용 범위에 들어온 적을 찾는다.
        for enemy in self.world.enemies:
            # 살아 있는 몹의 충돌 범위 안에 들어오면 퀴즈를 연다.
            if enemy.active and nearby.colliderect(enemy.rect):
                self.handle_problem_mob_contact(enemy)
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
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging_trash_slider:
            self.dragging_trash_slider = False
            return
        if self.cheat_menu_open:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_F9):
                    self.cheat_menu_open = False
                elif pygame.K_0 <= event.key <= pygame.K_5:
                    code = "" if event.key == pygame.K_0 else str(event.key - pygame.K_0)
                    self.cheats.clear()
                    self.cheats.update(choose_cheat(code))
                    self.world.infinite = self.cheats.get("infinite_map", False)
                    self.update_trash_mob_population()
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
        slider_panel = pygame.Rect(WIDTH - 275, HEIGHT - 96, 260, 78)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and slider_panel.collidepoint(event.pos):
            self.dragging_trash_slider = True
            self.set_trash_mob_rate_from_x(event.pos[0])
            return
        if event.type == pygame.MOUSEMOTION and self.dragging_trash_slider:
            self.set_trash_mob_rate_from_x(event.pos[0])
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.swing_stick()
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
        # 지면 착지에서 vy가 0으로 초기화되기 전에 접촉 프레임의 에너지를 저장한다.
        energy_before_movement = self.mechanical_energy()
        # 이동 발판을 갱신하고 위에 서 있던 플레이어를 함께 옮긴다.
        for platform in self.world.moving_platforms:
            previous = platform.update()
            standing = (self.player.on_ground and self.player.rect.bottom == previous.top
                        and self.player.rect.right > previous.left
                        and self.player.rect.left < previous.right)
            if standing:
                self.player.rect.x += platform.rect.x - previous.x
        previous_player_rect = self.player.rect.copy()
        keys = pygame.key.get_pressed()
        self.player.update(keys, self.world)
        impact_energy = max(energy_before_movement, self.mechanical_energy())
        # K/P를 누르고 있는 동안 각 공격의 쿨다운 간격마다 반복해서 휘두른다.
        if keys[pygame.K_p]:
            self.swing_stick("P")
        elif keys[pygame.K_k]:
            self.swing_stick("K")
        now = pygame.time.get_ticks()
        self.collect_items()
        # 구멍에 빠지면 고정된 코스 시작점으로 되돌려 안전한 지면에서 재개한다.
        if self.player.rect.top > HEIGHT:
            self.player.reset_position()
            self.camera_x = 0
            self.camera_y = 0
            if not self.cheats.get("no_damage"):
                self.hp = max(0, self.hp - 10)
        # 몹은 각자 배치된 지면이나 발판의 범위 안에서 왕복한다.
        for enemy in self.world.enemies:
            enemy.update()
        # 잡몹은 순찰하며 사거리 안에 플레이어가 있으면 투사체를 발사한다.
        for mob in self.world.trash_mobs:
            mob.update(self.player.rect, now)
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
            # 잡몹의 몸이나 투사체에 닿으면 피해를 주고 투사체를 제거한다.
            if now >= self.damage_cooldown_until:
                for mob in self.world.trash_mobs:
                    if not mob.active:
                        continue
                    hit = self.player.rect.colliderect(mob.rect)
                    for shot in list(mob.projectiles):
                        if shot.rect.colliderect(self.player.rect):
                            mob.projectiles.remove(shot)
                            hit = True
                            break
                    if hit:
                        if not self.cheats.get("no_damage"):
                            self.hp = max(0, self.hp - 8)
                            if self.audio:
                                self.audio.play_effect("damage")
                        self.damage_cooldown_until = now + 800
                        self.player.vy = -4
                        break
        # 플레이어 양쪽의 새 구간을 생성하고 생성된 후보 잡몹에 밀도를 적용한다.
        if self.world.update_generation(self.player.rect.x):
            self.update_trash_mob_population()
        # 무한 코스의 생성 범위 안에서 카메라가 좌우로 플레이어를 따라간다.
        target_x = self.player.rect.centerx - WIDTH // 2
        camera_max = max(self.world.active_start, self.world.active_end - WIDTH)
        self.camera_x = min(camera_max, max(self.world.active_start, target_x))
        # 플레이어가 화면 위쪽 경계를 넘으면 즉시 따라가고, 착지 후에는 천천히 원위치한다.
        screen_top = self.player.rect.top + self.camera_y
        upper_line = int(HEIGHT * 0.36)
        lower_line = int(HEIGHT * 0.72)
        if screen_top < upper_line:
            self.camera_y = max(self.camera_y, upper_line - self.player.rect.top)
        elif self.player.on_ground:
            self.camera_y = max(0, self.camera_y - 8)
        elif screen_top > lower_line:
            target_y = max(0, lower_line - self.player.rect.top)
            self.camera_y = max(target_y, self.camera_y - 8)
        # 플레이어가 활성 몹과 닿으면 해당 몹의 퀴즈를 연다.
        for enemy in self.world.enemies:
            # 활성 몹과 충돌한 순간 문제를 열고 중복 진입을 막는다.
            swept_player_rect = previous_player_rect.union(self.player.rect)
            collided = (self.player.rect.colliderect(enemy.rect)
                        or swept_player_rect.colliderect(enemy.rect))
            if enemy.active and collided:
                self.handle_problem_mob_contact(enemy, impact_energy)
                break
        # 낙하나 가시 피해로 체력이 소진되면 게임을 끝낸다.
        if self.hp <= 0:
            self.set_game_over()

    # 현재 월드와 HUD 위에 퀴즈·일시 정지·종료 오버레이를 그린다.
    def draw(self):
        self.renderer.draw_background(self.camera_x, self.camera_y)
        self.renderer.draw_world(self.world, self.camera_x, self.camera_y)
        self.renderer.draw_player(self.player, self.camera_x, self.camera_y,
                                  rotation=90 if self.game_over else 0)
        self.renderer.draw_stick(self.player, self.camera_x, self.camera_y)
        message = self.message if pygame.time.get_ticks() < self.message_until else ""
        self.renderer.draw_hud(self.hp, self.score, message)
        self.renderer.draw_item_status(self.player)
        self.renderer.draw_physics_status(self.player)
        self.renderer.draw_trash_mob_slider(self.trash_mob_rate)
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
            self.renderer.draw_start_countdown(seconds, self.physics)
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
            ("1 Damage = 0   2 Hyper ΔX   3 Hyper ΔY", (39, 54, 67), 20),
            ("4 Hyper Δ√(X²+Y²)", (39, 54, 67), 20),
            ("5 ULTIMATE   0 치트 끄기", (39, 54, 67), 20),
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
