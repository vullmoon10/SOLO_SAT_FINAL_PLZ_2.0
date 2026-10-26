import random
import pygame
from settings import WIDTH, HEIGHT, GROUND_Y
from world.terrain import Terrain
from entities.enemies import Enemy


class World(Terrain):
    def __init__(self, seed=None):
        super().__init__()
        self.seed = seed if seed is not None else random.randrange(1, 2**31)
        self.rng = random.Random(self.seed)
        self.generate_chunk(0, 12)

    def generate_chunk(self, start_x, count=5):
        x = start_x
        for _ in range(count):
            width = self.rng.randint(190, 290)
            self.ground_segments.append(pygame.Rect(x, GROUND_Y, width, HEIGHT - GROUND_Y))
            if self.rng.random() < 0.45:
                bw, bh = self.rng.choice([28, 36, 48]), self.rng.choice([35, 50, 65])
                bx = x + self.rng.randint(40, max(41, width - bw))
                self.decorations.append(pygame.Rect(bx, GROUND_Y - bh, bw, bh))
            if self.rng.random() < 0.35:
                self.spikes.append({"x": x + self.rng.randint(40, max(41, width - 70)),
                                    "y": GROUND_Y, "count": self.rng.randint(3, 5)})
            if self.rng.random() < 0.9:
                pw = self.rng.randint(100, min(150, width - 40))
                px = x + self.rng.randint(20, width - pw - 20)
                py = self.rng.randint(350, 455)
                self.platforms.append(pygame.Rect(px, py, pw, 12))
                if self.rng.random() < 0.7:
                    self.ladders.append(pygame.Rect(px + pw // 2 - 11, py, 22, GROUND_Y - py + 2))
                if self.rng.random() < 0.6:
                    self.add_enemy(px + self.rng.randint(15, max(16, pw - 35)), py)
            if self.rng.random() < 0.4:
                self.add_enemy(x + self.rng.randint(40, max(41, width - 35)), GROUND_Y)
            x += width
        self.world_end = x

    def add_enemy(self, x, ground_y):
        if x >= 3500 and self.rng.random() < 0.2:
            enemy_type = "challenge"
        elif x >= 1000 and self.rng.random() < 0.5:
            enemy_type = "advanced"
        else:
            enemy_type = "basic"
        self.enemies.append(Enemy(x, ground_y, enemy_type))

    def update_generation(self, player_x):
        if self.world_end < player_x + WIDTH + 700:
            self.generate_chunk(self.world_end + self.rng.randint(20, 60), 5)
        cutoff = player_x - WIDTH - 300
        self.platforms = [o for o in self.platforms if o.right > cutoff]
        self.ground_segments = [o for o in self.ground_segments if o.right > cutoff]
        self.ladders = [o for o in self.ladders if o.right > cutoff]
        self.spikes = [s for s in self.spikes if s["x"] + s["count"] * 13 > cutoff]
        self.decorations = [o for o in self.decorations if o.right > cutoff]
        self.enemies = [o for o in self.enemies if o.rect.right > cutoff]
