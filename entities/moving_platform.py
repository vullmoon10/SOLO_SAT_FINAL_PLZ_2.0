"""월드 안에서 좌우로 왕복하는 발판."""

import pygame


class MovingPlatform:
    def __init__(self, x, y, width=100, travel=70, speed=1.4):
        self.spawn_x = x
        self.rect = pygame.Rect(x, y, width, 12)
        self.left_limit = x - travel
        self.right_limit = x + travel
        self.direction = 1
        self.speed = speed

    def update(self):
        previous = self.rect.copy()
        self.rect.x += round(self.speed * self.direction)
        if self.rect.left <= self.left_limit:
            self.rect.left = self.left_limit
            self.direction = 1
        elif self.rect.left >= self.right_limit:
            self.rect.left = self.right_limit
            self.direction = -1
        return previous
