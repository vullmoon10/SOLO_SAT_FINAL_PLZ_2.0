"""근접 처치가 가능하고 플레이어에게 투사체를 발사하는 잡몹."""

import math

import pygame


class Projectile:
    def __init__(self, x, y, vx, vy):
        self.rect = pygame.Rect(round(x) - 6, round(y) - 6, 12, 12)
        self.vx = vx
        self.vy = vy

    def update(self):
        self.rect.x += round(self.vx)
        self.rect.y += round(self.vy)


class TrashMob:
    def __init__(self, x, ground_y, patrol_bounds, mob_id=None):
        self.mob_id = str(mob_id if mob_id is not None else x)
        self.rect = pygame.Rect(x, ground_y - 32, 32, 32)
        self.patrol_left, right = patrol_bounds
        self.patrol_right = max(self.patrol_left, right - self.rect.width)
        self.direction = 1
        self.speed = 1.1
        self.active = True
        self.enabled = True
        self.defeated = False
        self.hp = 100
        self.projectiles = []
        self.next_shot_at = 1000 + (x % 1000)

    def update(self, player_rect, now):
        if not self.active:
            return
        if self.patrol_right > self.patrol_left:
            self.rect.x += round(self.speed * self.direction)
            if self.rect.left <= self.patrol_left:
                self.rect.left = self.patrol_left
                self.direction = 1
            elif self.rect.left >= self.patrol_right:
                self.rect.left = self.patrol_right
                self.direction = -1

        dx = player_rect.centerx - self.rect.centerx
        dy = player_rect.centery - self.rect.centery
        if now >= self.next_shot_at and abs(dx) <= 520 and abs(dy) <= 260:
            distance = max(1, math.hypot(dx, dy))
            self.projectiles.append(Projectile(self.rect.centerx, self.rect.centery,
                                               dx / distance * 4.0, dy / distance * 4.0))
            self.next_shot_at = now + 1900
        for projectile in self.projectiles:
            projectile.update()
        self.projectiles = [shot for shot in self.projectiles
                            if -30 <= shot.rect.x <= 10_000 and -300 <= shot.rect.y <= 900]

    def take_damage(self, damage):
        self.hp = max(0, self.hp - max(0, int(damage)))
        if self.hp == 0:
            self.defeated = True
            self.active = False
            self.projectiles.clear()
            return True
        return False

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)
        self.active = self.enabled and not self.defeated
        if not self.active:
            self.projectiles.clear()
