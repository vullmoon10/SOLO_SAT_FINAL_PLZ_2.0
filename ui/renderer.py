"""월드, 캐릭터, 몹, 퀴즈와 게임 상태를 화면에 그린다."""

from pathlib import Path
import math

import pygame
from settings import *
from ui.hud import draw_hud


# 배경, 지형, 캐릭터, HUD와 퀴즈 화면을 그리는 렌더링 담당 객체다.
class Renderer:
    # 화면 표면과 게임에서 사용할 이미지·글꼴을 불러온다.
    def __init__(self, screen):
        self.screen = screen
        self.enemy_sprites = self._load_enemy_sprites()
        self.player_sprite = self._load_image(Path("player") / "player.jpg", colorkey=True)
        self.domain_sprites = self._load_domain_sprites()
        self.alert_font = pygame.font.SysFont("malgungothic", 22, bold=True)
        self.enemy_mark_font = pygame.font.SysFont("malgungothic", 10, bold=True)

    @staticmethod
    # 이미지 형식에 맞춰 투명도를 보존하며 파일을 불러온다.
    def _load_image(relative_path, colorkey=False):
        image_path = Path(__file__).resolve().parents[1] / "assets" / "images" / relative_path
        # 경로가 유효하면 화면 형식에 맞는 이미지 표면을 만든다.
        try:
            loaded = pygame.image.load(str(image_path))
            image = loaded.convert_alpha() if image_path.suffix.lower() == ".png" else loaded.convert()
            # 요청에 따라 배경색 또는 지정 색상을 투명 처리한다.
            if colorkey is True:
                image.set_colorkey(image.get_at((0, 0))[:3])
            # 별도로 지정된 배경색은 투명 키로 설정한다.
            elif colorkey:
                image.set_colorkey(colorkey)
            return image
        # 에셋이 없어도 기본 도형 렌더링으로 게임을 계속할 수 있게 한다.
        except (pygame.error, OSError):
            return None

    @classmethod
    # 난이도별 몹 이미지 경로를 난이도 이름으로 묶어 반환한다.
    def _load_enemy_sprites(cls):
        paths = {
            "easy": Path("difficulty/easy/mob_1.png"),
            "medium": Path("difficulty/normal/mob_2.png"),
            "hard": Path("difficulty/hard/mob_4.png"),
            "expert": Path("difficulty/expert/mob_3.png"),
        }
        return {difficulty: cls._load_image(path)
                for difficulty, path in paths.items()}

    @classmethod
    # 문제 영역을 표시할 유형 아이콘을 파일에서 불러온다.
    def _load_domain_sprites(cls):
        paths = {
            "산술": "algbra.png",
            "분수": "algbra.png",
            "측정·도형": "geometry.png",
            "수와 연산": "algbra.png",
            "문자와 식": "xyz.png",
            "좌표": "coordinate.png",
        }
        return {domain: cls._load_image(Path("type") / filename, colorkey=(255, 255, 255))
                for domain, filename in paths.items()}

    # 지정한 글꼴과 색상으로 텍스트를 화면에 출력한다.
    def draw_text(self, text, x, y, color=DARK, font=FONT):
        self.screen.blit(font.render(str(text), True, color), (x, y))

    # 카메라 위치를 반영한 하늘·산·구름 배경을 그린다.
    def draw_background(self, camera_x, camera_y=0):
        self.screen.fill(SKY)
        # 반복 패턴의 산을 배치해 화면 전체 배경을 채운다.
        for i in range(-1, 7):
            x = i * 260 - int(camera_x) % 260
            y_offset = int(camera_y * 0.12)
            pygame.draw.polygon(self.screen, MOUNTAIN,
                                [(x, 520 + y_offset),
                                 (x + 125, 360 + (i % 3) * 30 + y_offset),
                                 (x + 260, 520 + y_offset)])
        cloud_offset = int(pygame.time.get_ticks() * 0.025)
        # 천천히 이동하는 구름 위치를 계산한다.
        for i in range(6):
            x = (i * 210 - cloud_offset) % (WIDTH + 180) - 80
            y = 90 + (i % 3) * 55 + int(camera_y * 0.05)
            # 여러 원을 겹쳐 구름 한 덩어리를 그린다.
            for cx, cy, radius in [(x, y, 17), (x + 20, y - 8, 20), (x + 40, y, 15)]:
                pygame.draw.circle(self.screen, WHITE, (cx, cy), radius)

    # 화면 안에 보이는 지형, 위험 요소, 몹과 영역 아이콘을 그린다.
    def draw_world(self, world, camera_x, camera_y=0):
        # 지면과 발판을 색상에 맞춰 그리고 화면 밖 요소는 생략한다.
        for collection, fill, accent in ((world.ground_segments, DIRT, GRASS), (world.platforms, PLATFORM_COLOR, GRASS)):
            # 각 지면·발판 조각을 화면 좌표로 옮겨 표시한다.
            for segment in collection:
                rect = segment.move(-camera_x, camera_y)
                # 화면 안에 일부라도 들어오는 조각만 그린다.
                if rect.right >= 0 and rect.left <= WIDTH:
                    pygame.draw.rect(self.screen, fill, rect)
                    pygame.draw.rect(self.screen, accent, (rect.x, rect.y, rect.width, 7))
        # 이동 발판은 청록색으로 구분한다.
        for platform in world.moving_platforms:
            rect = platform.rect.move(-camera_x, camera_y)
            pygame.draw.rect(self.screen, (45, 145, 160), rect, border_radius=3)
            pygame.draw.rect(self.screen, (150, 235, 220), (rect.x, rect.y, rect.width, 5), border_radius=3)
        # 사다리 기둥과 가로대를 그린다.
        for ladder in world.ladders:
            rect = ladder.move(-camera_x, camera_y)
            # 보이지 않는 사다리는 그리기를 생략한다.
            if rect.right < 0 or rect.left > WIDTH:
                continue
            pygame.draw.line(self.screen, (180, 100, 55), rect.topleft, (rect.left, rect.bottom), 3)
            pygame.draw.line(self.screen, (180, 100, 55), (rect.right, rect.top), (rect.right, rect.bottom), 3)
            # 두 기둥 사이에 일정 간격으로 가로대를 추가한다.
            for y in range(rect.top + 8, rect.bottom, 13):
                pygame.draw.line(self.screen, (180, 100, 55), (rect.left, y), (rect.right, y), 3)
        # 배경 장식을 그린다.
        for item in world.decorations:
            rect = item.move(-camera_x, camera_y)
            # 화면 안에 있는 장식만 그린다.
            if rect.right >= 0 and rect.left <= WIDTH:
                pygame.draw.rect(self.screen, DIRT, rect)
                pygame.draw.rect(self.screen, (91, 57, 36), rect, 2)
        # 가시 구간의 삼각형을 화면에 배치한다.
        for spike in world.spikes:
            x, y = spike["x"] - camera_x, spike["y"] + camera_y
            # 가시 개수만큼 삼각형을 나란히 그린다.
            for i in range(spike["count"]):
                sx = x + i * 13
                pygame.draw.polygon(self.screen, (220, 45, 65), [(sx, y), (sx + 7, y - 15), (sx + 13, y)])
        # 미획득 아이템을 색과 글자 표식으로 구분해 그린다.
        item_styles = {
            "coin": ((255, 190, 35), "$"),
            "heart": ((225, 65, 85), "+"),
            "speed": ((55, 150, 225), "S"),
            "jump": ((115, 85, 210), "J"),
        }
        for item in world.items:
            if item["collected"]:
                continue
            rect = item["rect"].move(-camera_x, camera_y)
            if rect.right < 0 or rect.left > WIDTH:
                continue
            color, mark = item_styles[item["type"]]
            bob = int(math.sin(pygame.time.get_ticks() * 0.006 + rect.x) * 3)
            center = (rect.centerx, rect.centery + bob)
            pygame.draw.circle(self.screen, DARK, center, 13)
            pygame.draw.circle(self.screen, color, center, 11)
            label = self.alert_font.render(mark, True, WHITE)
            self.screen.blit(label, label.get_rect(center=center))
        # 잡몹과 잡몹이 발사한 투사체를 그린다.
        for mob in world.trash_mobs:
            if mob.active:
                rect = mob.rect.move(-camera_x, camera_y)
                if rect.right >= 0 and rect.left <= WIDTH:
                    pygame.draw.rect(self.screen, (80, 105, 125), rect, border_radius=7)
                    pygame.draw.rect(self.screen, (35, 48, 62), rect, 2, border_radius=7)
                    pygame.draw.circle(self.screen, (255, 220, 80), (rect.centerx - 6, rect.centery - 3), 3)
                    pygame.draw.circle(self.screen, (255, 220, 80), (rect.centerx + 6, rect.centery - 3), 3)
                    bar = pygame.Rect(rect.x, rect.y - 7, rect.width, 4)
                    pygame.draw.rect(self.screen, (55, 45, 45), bar)
                    pygame.draw.rect(self.screen, (220, 65, 65),
                                     (bar.x, bar.y, round(bar.width * mob.hp / 100), bar.height))
            for shot in mob.projectiles:
                rect = shot.rect.move(-camera_x, camera_y)
                pygame.draw.circle(self.screen, (225, 65, 65), rect.center, rect.width // 2)
                pygame.draw.circle(self.screen, (255, 190, 130), (rect.centerx - 2, rect.centery - 2), 2)
        # 활성 몹을 애니메이션과 영역 아이콘을 포함해 표시한다.
        for enemy in world.enemies:
            # 처치된 몹은 렌더링하지 않는다.
            if not enemy.active:
                continue
            rect = enemy.rect.move(-camera_x, camera_y)
            # 화면 바깥 몹은 그리기를 건너뛴다.
            if rect.right < 0 or rect.left > WIDTH:
                continue
            phase = pygame.time.get_ticks() * 0.004 + enemy.rect.x * 0.035
            bob = math.sin(phase) * 2.5
            stretch = 1.0 + math.sin(phase * 2) * 0.035
            source = self.enemy_sprites.get(enemy.data["difficulty"])
            # 이미지가 있으면 비율에 맞춰 몹을 그리고, 없으면 도형으로 대체한다.
            if source:
                fit = min(rect.width / source.get_width(), rect.height / source.get_height())
                sprite_width = max(1, round(source.get_width() * fit))
                sprite_height = max(1, round(source.get_height() * fit * stretch))
                animated = pygame.transform.scale(source, (sprite_width, sprite_height))
                badge = pygame.Surface((sprite_width, sprite_height), pygame.SRCALPHA)
                badge_y = int(sprite_height * .72)
                domain_icon = self.domain_sprites.get(enemy.data["domain"])
                # 몹의 문제 영역을 작은 아이콘 배지로 표시한다.
                if domain_icon:
                    icon_size = min(18, max(12, min(sprite_width, sprite_height) // 2))
                    pygame.draw.circle(badge, WHITE, (sprite_width // 2, badge_y), icon_size // 2 + 2)
                    pygame.draw.circle(badge, enemy.data["color"],
                                       (sprite_width // 2, badge_y), icon_size // 2 + 2, 1)
                    icon = pygame.transform.smoothscale(domain_icon, (icon_size, icon_size))
                    badge.blit(icon, icon.get_rect(center=(sprite_width // 2, badge_y)))
                # 영역 아이콘이 없으면 글자 표식으로 몹 유형을 구분한다.
                else:
                    pygame.draw.circle(badge, enemy.data["color"], (sprite_width // 2, badge_y), 8)
                    pygame.draw.circle(badge, DARK, (sprite_width // 2, badge_y), 8, 1)
                    mark = self.enemy_mark_font.render(enemy.data["mark"], True, WHITE)
                    badge.blit(mark, mark.get_rect(center=(sprite_width // 2, badge_y)))
                animated.blit(badge, (0, 0))
            # 몹 이미지가 없으면 단색 타원으로 외형을 대신한다.
            else:
                animated = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                pygame.draw.ellipse(animated, enemy.data["color"], animated.get_rect())
                pygame.draw.ellipse(animated, DARK, animated.get_rect(), 2)
            animated = pygame.transform.rotozoom(animated, math.sin(phase) * 3, 1)
            animated_rect = animated.get_rect(center=(rect.centerx, int(rect.centery + bob)))
            self.screen.blit(animated, animated_rect)
            # 오답 상태가 유지되는 동안 몹 위에 경고 표식을 띄운다.
            if enemy.wrong_until > pygame.time.get_ticks():
                alert = self.alert_font.render("!", True, WHITE)
                pygame.draw.circle(self.screen, (220, 45, 65), (rect.centerx, rect.top - 5), 11)
                self.screen.blit(alert, alert.get_rect(center=(rect.centerx, rect.top - 6)))

    # 시작 전 화면을 어둡게 덮고 남은 카운트다운을 보여준다.
    def draw_start_countdown(self, seconds, physics):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 15, 25, 175))
        self.screen.blit(overlay, (0, 0))
        title = TITLE_FONT.render("게임 시작", True, WHITE)
        number = pygame.font.SysFont("malgungothic", 110, bold=True).render(str(seconds), True, YELLOW)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 75)))
        self.screen.blit(number, number.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40)))
        details = pygame.font.SysFont("malgungothic", 19).render(
            f"이동 {physics['move_speed']:.2f} · 중력 {physics['gravity']:.2f} · 점프 {physics['jump_power']:.2f}",
            True, WHITE,
        )
        self.screen.blit(details, details.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 125)))

    # 플레이를 멈춘 동안 재개 안내를 화면 중앙에 표시한다.
    def draw_pause_overlay(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 15, 25, 175))
        self.screen.blit(overlay, (0, 0))
        label = TITLE_FONT.render("PAUSED · ESC로 계속", True, WHITE)
        self.screen.blit(label, label.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

    # 플레이어 이미지가 있으면 사용하고 없으면 기본 사각형으로 표시한다.
    def draw_player(self, player, camera_x, camera_y=0, rotation=0):
        rect = player.rect.move(-camera_x, camera_y)
        # 에셋이 있으면 플레이어 크기에 맞춰 표시한다.
        if self.player_sprite:
            sprite = pygame.transform.scale(self.player_sprite, rect.size)
        # 이미지가 없으면 기본 색상 사각형을 플레이어로 표시한다.
        else:
            sprite = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(sprite, BLUE, sprite.get_rect(), border_radius=3)
            pygame.draw.rect(sprite, (40, 45, 150), sprite.get_rect(), 2, border_radius=3)
        # 게임 오버 연출 등 요청된 회전 값을 적용한다.
        sprite = pygame.transform.flip(sprite, player.facing < 0, False)
        # 요청된 회전이 있을 때만 이미지 방향을 바꾼다.
        if rotation:
            sprite = pygame.transform.rotate(sprite, rotation)
        self.screen.blit(sprite, sprite.get_rect(center=rect.center))

    # HUD 렌더링을 전용 그리기 함수에 넘긴다.
    def draw_hud(self, hp, score, message):
        draw_hud(self.screen, hp, score, message)

    # 활성 중인 시간제 아이템 효과와 남은 시간을 표시한다.
    def draw_item_status(self, player):
        now = pygame.time.get_ticks()
        active = []
        if player.speed_boost_until > now:
            active.append(("속도", player.speed_boost_until - now))
        if player.jump_boost_until > now:
            active.append(("점프", player.jump_boost_until - now))
        for index, (label, remaining) in enumerate(active):
            text = self.alert_font.render(f"{label} 강화 {remaining / 1000:.1f}s", True, WHITE)
            background = text.get_rect(topright=(WIDTH - 18, 18 + index * 30)).inflate(16, 8)
            pygame.draw.rect(self.screen, DARK, background, border_radius=5)
            self.screen.blit(text, text.get_rect(center=background.center))

    # 현재 속도와 게임 물리 기준의 운동·위치 에너지를 표시한다.
    def draw_physics_status(self, player):
        speed = math.hypot(player.horizontal_velocity, player.vy)
        kinetic_energy = 0.5 * speed ** 2
        height = max(0, GROUND_Y - player.rect.bottom)
        potential_energy = height * player.physics["gravity"]
        panel = pygame.Rect(WIDTH - 205, 76, 190, 82)
        pygame.draw.rect(self.screen, (250, 249, 239), panel, border_radius=7)
        pygame.draw.rect(self.screen, DARK, panel, 2, border_radius=7)
        for index, text in enumerate((f"속도  {speed:.1f} px/frame",
                                      f"Ek  {kinetic_energy:.1f}",
                                      f"Ep  {potential_energy:.1f}")):
            label = SMALL.render(text, True, DARK)
            self.screen.blit(label, (panel.x + 12, panel.y + 8 + index * 23))

    # 잡몹 활성 수를 조절하는 화면 슬라이더를 표시한다.
    def draw_trash_mob_slider(self, rate):
        panel = pygame.Rect(WIDTH - 275, HEIGHT - 96, 260, 78)
        pygame.draw.rect(self.screen, CREAM, panel, border_radius=8)
        pygame.draw.rect(self.screen, DARK, panel, 2, border_radius=8)
        title = SMALL.render(f"잡몹 생성 밀도  {rate}%", True, DARK)
        self.screen.blit(title, (panel.x + 14, panel.y + 8))
        track = pygame.Rect(WIDTH - 253, HEIGHT - 53, 216, 8)
        pygame.draw.rect(self.screen, (185, 195, 205), track, border_radius=4)
        ratio = rate / 100
        fill = pygame.Rect(track.x, track.y, round(track.width * ratio), track.height)
        pygame.draw.rect(self.screen, (50, 135, 210), fill, border_radius=4)
        knob_x = track.x + round(track.width * ratio)
        pygame.draw.circle(self.screen, WHITE, (knob_x, track.centery), 9)
        pygame.draw.circle(self.screen, (35, 105, 175), (knob_x, track.centery), 9, 2)
        self.screen.blit(SMALL.render("낮음", True, DARK), (track.left, panel.bottom - 21))
        more = SMALL.render("높음", True, DARK)
        self.screen.blit(more, (track.right - more.get_width(), panel.bottom - 21))

    # 플레이어가 들고 있는 막대기를 손 위치에 맞춰 그리고 휘두름을 표시한다.
    def draw_stick(self, player, camera_x, camera_y=0):
        now = pygame.time.get_ticks()
        rect = player.rect.move(-camera_x, camera_y)
        direction = player.facing
        hand = (rect.centerx + direction * 10, rect.centery + 8)
        swinging = now < player.swing_until
        reach = 78 if swinging and player.stick_mode == "K" else 58 if swinging else 29
        tip = (rect.centerx + direction * reach, rect.centery - (12 if swinging else -13))
        stick_color = (235, 125, 45) if player.stick_mode == "K" else (95, 175, 245) if player.stick_mode == "P" else (92, 55, 30)
        pygame.draw.line(self.screen, (55, 42, 35), hand, tip, 8)
        pygame.draw.line(self.screen, stick_color if swinging else (210, 165, 105), hand, tip, 4)
        if swinging:
            arc_rect = pygame.Rect(rect.centerx - 48, rect.centery - 35, 96, 70)
            start, end = (-1.0, 1.0) if direction > 0 else (2.2, 4.2)
            pygame.draw.arc(self.screen, stick_color, arc_rect, start, end, 4)
        if now < player.special_effect_until and player.stick_mode == "P":
            pygame.draw.circle(self.screen, (120, 205, 255), rect.center, 82, 3)

    # 픽셀 스타일 글자를 확대해 게임 오버 화면용 표면으로 만든다.
    def _pixel_text(self, text, color, scale=2, size=12):
        font = pygame.font.SysFont("monospace", size, bold=True)
        glyphs = font.render(str(text), False, color)
        return pygame.transform.scale(glyphs, (glyphs.get_width() * scale, glyphs.get_height() * scale))

    # 게임 오버 배경과 최종 점수, 타이틀 복귀 안내를 그린다.
    def draw_game_over(self, score):
        tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        tint.fill((205, 15, 25, 120))
        self.screen.blit(tint, (0, 0))

        title = self._pixel_text("GAME OVER", (28, 12, 16), scale=3, size=17)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, int(HEIGHT * 0.28))))

        label = self._pixel_text("Score:", (28, 12, 16), scale=2, size=13)
        value = self._pixel_text(str(score), (255, 224, 55), scale=3, size=16)
        gap = 12
        total_width = label.get_width() + gap + value.get_width()
        left = (WIDTH - total_width) // 2
        y = int(HEIGHT * 0.44)
        self.screen.blit(label, (left, y + (value.get_height() - label.get_height()) // 2))
        self.screen.blit(value, (left + label.get_width() + gap, y))

        instruction = self._pixel_text("ESC: TITLE SCREEN", (35, 10, 12), scale=2, size=9)
        self.screen.blit(instruction, instruction.get_rect(center=(WIDTH // 2, int(HEIGHT * 0.78))))

    # 코스 끝에 체크무늬 깃발을 표시한다.
    def draw_goal(self, world_end, camera_x, camera_y=0):
        x = world_end - 72 - camera_x
        ground_y = GROUND_Y + camera_y
        if x < -40 or x > WIDTH + 40:
            return
        pole_x = int(x)
        pygame.draw.line(self.screen, (45, 48, 54), (pole_x, ground_y), (pole_x, ground_y - 132), 5)
        flag = [(pole_x + 3, ground_y - 130), (pole_x + 54, ground_y - 114),
                (pole_x + 3, ground_y - 98)]
        pygame.draw.polygon(self.screen, (235, 65, 65), flag)
        pygame.draw.polygon(self.screen, WHITE, flag, 2)
        marker = SMALL.render("GOAL", True, DARK)
        self.screen.blit(marker, marker.get_rect(center=(pole_x + 26, ground_y - 78)))

    # 코스 도착 시 클리어 문구와 최종 점수를 표시한다.
    def draw_victory(self, score):
        tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        tint.fill((20, 90, 55, 150))
        self.screen.blit(tint, (0, 0))
        title = TITLE_FONT.render("코스 클리어!", True, WHITE)
        value = BIG.render(f"점수 {score}", True, YELLOW)
        instruction = SMALL.render("ESC: 타이틀 화면", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 55)))
        self.screen.blit(value, value.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 5)))
        self.screen.blit(instruction, instruction.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 65)))

    # 퀴즈 패널, 영역·난이도, 남은 시간과 선택지를 표시한다.
    def draw_quiz(self, quiz):
        # 퀴즈가 열려 있지 않으면 화면을 덮지 않는다.
        if not quiz.active:
            return
        q = quiz.enemy.question
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((20, 30, 45, 205))
        self.screen.blit(overlay, (0, 0))
        panel = pygame.Rect(25, 28, WIDTH - 50, HEIGHT - 56)
        pygame.draw.rect(self.screen, CREAM, panel, border_radius=8)
        level_name = {"easy": "쉬움", "medium": "보통", "hard": "도전", "expert": "최상"}.get(q.get("difficulty"), "수학")
        domain = q.get("domain", "수학")
        domain_icon = self.domain_sprites.get(domain)
        # 사용할 영역 아이콘이 있으면 문제 제목 옆에 표시한다.
        if domain_icon:
            icon = pygame.transform.scale(domain_icon, (24, 24))
            self.screen.blit(icon, (44, 36))
        self.draw_text(f"{quiz.enemy.data['name']} · {domain} · {level_name}",
                       74 if domain_icon else 45, 40, GRASS, SMALL)
        self.draw_text(q.get("q", ""), 45, 65, DARK, FONT)
        remaining = quiz.remaining()
        self.draw_text(f"{remaining:.1f}s", 905, 40, RED if remaining < 10 else DARK, SMALL)
        bar = pygame.Rect(45, 96, WIDTH - 90, 7)
        pygame.draw.rect(self.screen, GRAY, bar)
        ratio = remaining / max(1, quiz.duration)
        pygame.draw.rect(self.screen, GRASS if ratio > .3 else (220, 130, 50), (bar.x, bar.y, int(bar.width * ratio), bar.height))

        choices = q.get("choices", [])
        left, width, top, row_h = 45, WIDTH - 90, 125, min(70, 380 // max(1, len(choices)))
        # 보기 행을 그리고 현재 선택된 보기를 강조한다.
        for i, choice in enumerate(choices):
            option = pygame.Rect(left, top + i * row_h, width, row_h - 8)
            selected = i == quiz.selected
            pygame.draw.rect(self.screen, (190, 220, 255) if selected else GRAY, option, border_radius=5)
            # 선택된 보기에는 테두리를 그려 현재 위치를 강조한다.
            if selected:
                pygame.draw.rect(self.screen, (55, 110, 220), option, 2, border_radius=5)
            label = str(choice)
            self.draw_text(f"{i + 1}. {label}", option.x + 12, option.y + 8, DARK, SMALL)
        self.draw_text("↑/↓ 선택 · 1~4 또는 Enter 제출 · ESC 닫기", 45, 545, DARK, SMALL)
