"""시드 기반으로 지형과 난이도별 몹을 생성하고 월드를 확장한다."""

import random
import pygame
from settings import HEIGHT, GROUND_Y, SPAWN_SAFE_END
from world.terrain import Terrain
from entities.enemies import Enemy, ENEMY_TYPES_BY_DIFFICULTY
from entities.moving_platform import MovingPlatform
from entities.trash_mob import TrashMob


# 지형과 난이도별 몹을 시드 기반으로 생성하는 월드 객체다.
class World(Terrain):
    # 시드 난수 생성기를 만들고 첫 구간을 생성한다.
    def __init__(self, seed=None, infinite=False):
        super().__init__()
        self.seed = seed if seed is not None else random.randrange(1, 2**31)
        self.rng = random.Random(self.seed)
        self.infinite = infinite
        self.world_start = 0
        self.generate_chunk(0, 12)
        self.base_world_end = self.world_end
        self.left_batch_index = 0

    @property
    def active_start(self):
        return self.world_start if self.infinite else 0

    @property
    def active_end(self):
        return self.world_end if self.infinite else self.base_world_end

    # 지정한 위치부터 지면과 무작위 지형·몹 청크를 덧붙인다.
    def generate_chunk(self, start_x, count=5, widths=None):
        x = start_x
        # 일정 수의 구간을 하나씩 만들며 월드 끝 좌표를 갱신한다.
        for index in range(count):
            # 지면 구간 길이를 바꿔 진행 리듬을 다양하게 만든다.
            width = widths[index] if widths is not None else self.rng.randint(290, 500)
            self.ground_segments.append(pygame.Rect(x, GROUND_Y, width, HEIGHT - GROUND_Y))
            # 확률에 따라 배경 장식을 추가한다.
            if self.rng.random() < 0.45:
                bw, bh = self.rng.choice([28, 36, 48]), self.rng.choice([35, 50, 65])
                bx = x + self.rng.randint(40, max(41, width - bw))
                self.decorations.append(pygame.Rect(bx, GROUND_Y - bh, bw, bh))
            # 확률적으로 가시를 배치하되 시작 안전 구간은 건너뛴다.
            if self.rng.random() < 0.35:
                spike_x = x + self.rng.randint(40, max(41, width - 70))
                # 안전 구간 뒤에 있는 경우에만 실제 가시를 추가한다.
                if not self.is_spawn_safe(spike_x):
                    self.spikes.append({"x": spike_x, "y": GROUND_Y, "count": self.rng.randint(3, 5)})
            # 구간별 구조를 골라 발판 개수와 높이 흐름을 바꾼다.
            layout = self.rng.choices(
                ("sparse", "pair", "stairs", "cluster"), weights=(18, 30, 34, 18), k=1
            )[0]
            platform_count = {"sparse": 1, "pair": 2, "stairs": 3, "cluster": 4}[layout]
            base_height = self.rng.randint(385, 455)
            stair_direction = self.rng.choice((-1, 1))
            stair_step = self.rng.randint(15, 25)
            for lane in range(platform_count):
                lane_width = width / platform_count
                max_platform_width = max(76, min(135, int(lane_width) - 18))
                pw = self.rng.randint(75, max_platform_width)
                cell_start = x + int(lane * lane_width)
                cell_end = x + int((lane + 1) * lane_width)
                px = cell_start + max(0, (cell_end - cell_start - pw) // 2)
                if layout == "stairs":
                    py = base_height - stair_direction * lane * stair_step
                elif layout == "cluster":
                    py = base_height + self.rng.randint(-55, 55)
                else:
                    py = base_height + self.rng.randint(-25, 25)
                py = max(365, min(460, py))
                # 시작 위치 주변에는 발판과 그 부속 오브젝트를 만들지 않는다.
                if not self.is_spawn_safe(px):
                    self.platforms.append(pygame.Rect(px, py, pw, 12))
                    # 일부 발판 위에 점수·회복·강화 아이템을 둔다.
                    if self.rng.random() < 0.55:
                        self.add_item(px + pw // 2, py - 22)
                    # 대부분의 발판은 지면 사다리로 접근할 수 있게 한다.
                    if self.rng.random() < 0.8:
                        self.ladders.append(pygame.Rect(px + pw // 2 - 11, py, 22, GROUND_Y - py + 2))
                    # 발판 위 몹은 일부 구간에만 배치해 혼잡을 줄인다.
                    if self.rng.random() < 0.3:
                        self.add_enemy(px + self.rng.randint(15, max(16, pw - 35)), py,
                                       (px, px + pw))
            # 지면에도 확률적으로 몹을 생성하되 시작 구간은 안전하게 둔다.
            if self.rng.random() < 0.4:
                enemy_x = x + self.rng.randint(40, max(41, width - 35))
                # 시작 안전 구간을 넘은 지면 좌표에만 몹을 둔다.
                if not self.is_spawn_safe(enemy_x):
                    self.add_enemy(enemy_x, GROUND_Y, (x, x + width))
            # 각 구간에 지상 아이템이 추가로 놓일 수 있다.
            if not self.is_spawn_safe(x + width // 2) and self.rng.random() < 0.3:
                self.add_item(x + width // 2, GROUND_Y - 24)
            # 안전 시작 구간 뒤에 슬라이더가 활성화할 잡몹 후보를 한 마리 둔다.
            if not self.is_spawn_safe(x + width // 2):
                mob_x = x + width // 2
                self.trash_mobs.append(TrashMob(mob_x, GROUND_Y, (x, x + width), mob_id=mob_x))
            # 구간 일부에 좌우로 왕복하는 발판을 추가한다.
            if not self.is_spawn_safe(x + width // 2) and self.rng.random() < 0.38:
                platform_x = x + width // 2 - 50
                platform_y = self.rng.randint(425, 465)
                self.moving_platforms.append(MovingPlatform(platform_x, platform_y))
            x += width
        self.world_start = min(self.world_start, start_x)
        self.world_end = max(self.world_end, x)

    @staticmethod
    def is_spawn_safe(x):
        return -SPAWN_SAFE_END <= x < SPAWN_SAFE_END

    # 플레이어가 왼쪽 경계에 다가오면 고유 시드로 이전 구간을 생성한다.
    def generate_left_chunk(self):
        self.left_batch_index += 1
        batch_seed = (self.seed ^ (0x9E3779B9 * self.left_batch_index)) & 0xFFFFFFFF
        width_rng = random.Random(batch_seed)
        widths = [width_rng.randint(330, 400) for _ in range(12)]
        start_x = self.world_start - sum(widths)
        previous_rng = self.rng
        self.rng = random.Random(batch_seed ^ 0xA5A5A5A5)
        try:
            self.generate_chunk(start_x, len(widths), widths=widths)
        finally:
            self.rng = previous_rng

    # 월드 진행 거리에 따라 난이도와 몹 종류를 골라 배치한다.
    def add_enemy(self, x, ground_y, patrol_bounds=None):
        # 진행 거리가 늘수록 높은 난이도가 나타날 확률을 높인다.
        if x >= 3500 and self.rng.random() < 0.18:
            difficulty = "expert"
        # 중후반 구간에서는 어려움 난이도 몹을 일정 확률로 선택한다.
        elif x >= 2200 and self.rng.random() < 0.23:
            difficulty = "hard"
        # 초중반 구간에서는 보통 난이도 몹을 확률적으로 섞는다.
        elif x >= 1000 and self.rng.random() < 0.5:
            difficulty = "medium"
        # 더 높은 난이도 선택에 실패하면 쉬운 몹을 기본으로 배치한다.
        else:
            difficulty = "easy"
        enemy_type = self.rng.choice(ENEMY_TYPES_BY_DIFFICULTY[difficulty])
        self.enemies.append(Enemy(x, ground_y, enemy_type, patrol_bounds))

    # 종류별 효과와 고유 ID를 가진 아이템을 코스에 추가한다.
    def add_item(self, center_x, center_y):
        item_type = self.rng.choices(
            ("coin", "heart", "speed", "jump"), weights=(55, 20, 13, 12), k=1
        )[0]
        rect = pygame.Rect(center_x - 11, center_y - 11, 22, 22)
        item_id = f"{center_x}:{center_y}:{item_type}"
        self.items.append({"id": item_id, "type": item_type, "rect": rect, "collected": False})

    # 플레이어 양쪽에 월드를 미리 만들고 생성 여부를 반환한다.
    def update_generation(self, player_x):
        if not self.infinite:
            return False
        generated = False
        if player_x + WIDTH + 700 > self.world_end:
            self.generate_chunk(self.world_end, 5)
            generated = True
        if player_x - 700 < self.world_start:
            self.generate_left_chunk()
            generated = True
        return generated
