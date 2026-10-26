"""시드 기반으로 지형과 난이도별 몹을 생성하고 월드를 확장한다."""

import random
import pygame
from settings import WIDTH, HEIGHT, GROUND_Y, SPAWN_SAFE_END
from world.terrain import Terrain
from entities.enemies import Enemy, ENEMY_TYPES_BY_DIFFICULTY


# 지형과 난이도별 몹을 시드 기반으로 생성하는 월드 객체다.
class World(Terrain):
    # 시드 난수 생성기를 만들고 첫 구간을 생성한다.
    def __init__(self, seed=None):
        super().__init__()
        self.seed = seed if seed is not None else random.randrange(1, 2**31)
        self.rng = random.Random(self.seed)
        self.generate_chunk(0, 12)

    # 지정한 위치부터 지면과 무작위 지형·몹 청크를 덧붙인다.
    def generate_chunk(self, start_x, count=5):
        x = start_x
        # 일정 수의 구간을 하나씩 만들며 월드 끝 좌표를 갱신한다.
        for _ in range(count):
            width = self.rng.randint(190, 290)
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
                if spike_x >= SPAWN_SAFE_END:
                    self.spikes.append({"x": spike_x, "y": GROUND_Y, "count": self.rng.randint(3, 5)})
            # 대부분 구간에 발판을 만들고, 시작 안전 구간은 비워 둔다.
            if self.rng.random() < 0.9:
                pw = self.rng.randint(100, min(150, width - 40))
                px = x + self.rng.randint(20, width - pw - 20)
                py = self.rng.randint(350, 455)
                # 시작 위치 주변에는 발판과 그 부속 오브젝트를 만들지 않는다.
                if px >= SPAWN_SAFE_END:
                    self.platforms.append(pygame.Rect(px, py, pw, 12))
                    # 발판과 지면을 연결하는 사다리를 확률적으로 추가한다.
                    if self.rng.random() < 0.7:
                        self.ladders.append(pygame.Rect(px + pw // 2 - 11, py, 22, GROUND_Y - py + 2))
                    # 일부 발판에는 그 높이의 몹을 배치한다.
                    if self.rng.random() < 0.6:
                        self.add_enemy(px + self.rng.randint(15, max(16, pw - 35)), py)
            # 지면에도 확률적으로 몹을 생성하되 시작 구간은 안전하게 둔다.
            if self.rng.random() < 0.4:
                enemy_x = x + self.rng.randint(40, max(41, width - 35))
                # 시작 안전 구간을 넘은 지면 좌표에만 몹을 둔다.
                if enemy_x >= SPAWN_SAFE_END:
                    self.add_enemy(enemy_x, GROUND_Y)
            x += width
        self.world_end = x

    # 월드 진행 거리에 따라 난이도와 몹 종류를 골라 배치한다.
    def add_enemy(self, x, ground_y):
        # 진행 거리가 늘수록 높은 난이도가 나타날 확률을 높인다.
        if x >= 6500 and self.rng.random() < 0.18:
            difficulty = "expert"
        # 중후반 구간에서는 어려움 난이도 몹을 일정 확률로 선택한다.
        elif x >= 3500 and self.rng.random() < 0.23:
            difficulty = "hard"
        # 초중반 구간에서는 보통 난이도 몹을 확률적으로 섞는다.
        elif x >= 1000 and self.rng.random() < 0.5:
            difficulty = "medium"
        # 더 높은 난이도 선택에 실패하면 쉬운 몹을 기본으로 배치한다.
        else:
            difficulty = "easy"
        enemy_type = self.rng.choice(ENEMY_TYPES_BY_DIFFICULTY[difficulty])
        self.enemies.append(Enemy(x, ground_y, enemy_type))

    # 플레이어 앞 월드를 미리 만들고 지나간 지형을 메모리에서 정리한다.
    def update_generation(self, player_x):
        # 화면 앞쪽 월드가 부족할 때 다음 청크를 생성한다.
        if self.world_end < player_x + WIDTH + 700:
            self.generate_chunk(self.world_end + self.rng.randint(20, 60), 5)
        cutoff = player_x - WIDTH - 300
        self.platforms = [o for o in self.platforms if o.right > cutoff]
        self.ground_segments = [o for o in self.ground_segments if o.right > cutoff]
        self.ladders = [o for o in self.ladders if o.right > cutoff]
        self.spikes = [s for s in self.spikes if s["x"] + s["count"] * 13 > cutoff]
        self.decorations = [o for o in self.decorations if o.right > cutoff]
        self.enemies = [o for o in self.enemies if o.rect.right > cutoff]
