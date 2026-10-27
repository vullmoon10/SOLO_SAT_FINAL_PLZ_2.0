"""플레이어의 이동, 점프, 사다리 오르기와 충돌 상태를 관리한다."""

import pygame
from settings import MOVE_SPEED, GRAVITY, JUMP_POWER, GROUND_Y, PLAYER_WIDTH, PLAYER_HEIGHT


# 플레이어의 충돌 상자와 입력에 따른 이동 상태를 관리한다.
class Player:  # 플레이어 위치와 이동 물리를 관리
    # 시작 좌표와 수직 이동·등반·치트 상태를 초기화한다.
    def __init__(self, x=60, y=450, cheats=None, physics=None):  # 시작 위치와 이동 상태를 초기화
        self.rect = pygame.Rect(x, y, PLAYER_WIDTH, PLAYER_HEIGHT)  # 플레이어 충돌 상자
        self.vy = 0.0  # 세로 속도
        self.on_ground = False  # 지면 착지 여부
        self.climbing = False  # 사다리 등반 여부
        self.facing = 1  # 오른쪽 방향으로 시작
        self.horizontal_velocity = 0.0  # 방향키와 A/D 입력의 가속 속도
        self.speed_boost_until = 0  # 속도 아이템 종료 시각
        self.jump_boost_until = 0  # 점프 아이템 종료 시각
        self.swing_until = 0  # 막대기 휘두르기 애니메이션 종료 시각
        self.attack_cooldown_until = 0  # 다음 공격 가능 시각
        self.stick_mode = "normal"  # 막대기 공격 연출 종류
        self.special_effect_until = 0  # 특수 공격 효과 종료 시각
        self.cheats = cheats if cheats is not None else {}  # 이동에 적용할 치트 설정
        self.physics = physics or {
            "move_speed": MOVE_SPEED, "gravity": GRAVITY, "jump_power": JUMP_POWER,
        }

    # 입력, 중력, 사다리 이동과 지형 착지를 한 프레임 계산한다.
    def update(self, keys, world):  # 입력·중력·지형 충돌을 반영해 위치를 갱신
        now = pygame.time.get_ticks()
        if self.cheats.get("superspeed"):
            max_speed = 100
        elif now < self.speed_boost_until:
            max_speed = self.physics["move_speed"] * 2
        else:
            max_speed = self.physics["move_speed"]
        horizontal = int(bool(keys[pygame.K_d] or keys[pygame.K_RIGHT])) - int(bool(keys[pygame.K_a] or keys[pygame.K_LEFT]))
        if horizontal:
            self.facing = 1 if horizontal > 0 else -1
            acceleration = max(0.6, max_speed * 0.06)
            if self.horizontal_velocity * horizontal < 0:
                self.horizontal_velocity += horizontal * acceleration * 2
            else:
                self.horizontal_velocity += horizontal * acceleration
            self.horizontal_velocity = max(-max_speed, min(max_speed, self.horizontal_velocity))
        else:
            self.horizontal_velocity *= 0.82
            if abs(self.horizontal_velocity) < 0.25:
                self.horizontal_velocity = 0
        dx = round(self.horizontal_velocity)
        self.rect.x += dx  # 입력 이동량을 가로 위치에 적용
        speed = max_speed  # 사다리 이동에는 현재 모드의 최대 속도를 사용

        # 사다리는 플레이어의 발 위치까지 포함해 판정하고, 사다리 밖으로 나가면 중력을 복구
        # 현재 충돌 범위와 겹치는 사다리를 찾아 등반 가능 여부를 판정한다.
        ladder = next((item for item in world.ladders  # 플레이어와 겹치는 사다리를 찾기
                       if self.rect.centerx >= item.left - 8
                       and self.rect.centerx <= item.right + 8
                       and self.rect.bottom >= item.top
                       and self.rect.top <= item.bottom), None)  # 플레이어와 겹치는 사다리
        climb_input = int(bool(keys[pygame.K_s] or keys[pygame.K_DOWN])) - int(bool(keys[pygame.K_w] or keys[pygame.K_UP]))  # 사다리 위아래 입력 방향
        self.climbing = ladder is not None and climb_input != 0  # 사다리 영역에서 등반 입력 중인지 여부

        previous = self.rect.copy()  # 착지 판정을 위한 이전 프레임 위치
        # 사다리에서는 입력 방향으로 움직이고, 그 외에는 중력을 적용한다.
        if self.climbing:  # 사다리를 오르는 동안 중력 대신 입력 이동을 적용
            self.rect.y += climb_input * speed  # 입력 방향 사다리 이동
            self.rect.top = max(self.rect.top, ladder.top - self.rect.height + 2)  # 사다리 위쪽 이동 한계
            self.rect.bottom = min(self.rect.bottom, ladder.bottom)  # 사다리 아래쪽 이동 한계
            self.vy = 0  # 등반 중 중력을 정지
        # 사다리를 타지 않을 때에는 낙하 중력을 적용한다.
        else:
            self.vy += self.physics["gravity"]  # 낙하 속도 상한 없이 중력을 계속 반영
            self.rect.y += int(self.vy)  # 세로 속도를 위치에 적용

        self.on_ground = False  # 이번 프레임 착지 여부를 다시 판정
        # 낙하 중인 플레이어가 지면이나 발판을 위에서 통과했는지 확인한다.
        if not self.climbing and self.vy >= 0:  # 하강 중일 때 지면·발판 착지를 판정
            # 모든 지면과 발판 표면에 대해 착지 여부를 검사한다.
            surfaces = world.ground_segments + world.platforms + [platform.rect for platform in world.moving_platforms]
            for surface in surfaces:
                overlap = self.rect.right > surface.left and self.rect.left < surface.right  # 수평 충돌 범위 중첩 여부
                crossed_top = previous.bottom <= surface.top and self.rect.bottom >= surface.top  # 위에서 표면을 통과했는지 여부
                # 사다리 하강 후 발판 내부 착지 판정
                ladder_exit_landing = (previous.bottom <= surface.top + 3 and self.rect.bottom >= surface.top  # 사다리에서 내려와 발판 높이에 도달했는지 확인
                                       and previous.top < surface.top and self.rect.bottom <= surface.top + 16)
                # 수평으로 겹치고 표면을 밟은 경우 발판 위에 착지시킨다.
                if overlap and (crossed_top or ladder_exit_landing):  # 착지 조건을 만족하면 발판 위에 정렬
                    self.rect.bottom = surface.top  # 발판 상단에 플레이어를 정렬
                    self.vy = 0  # 착지 시 낙하 속도를 제거
                    self.on_ground = True  # 점프 가능한 착지 상태로 설정
                    break

        # 무한맵은 왼쪽 생성 경계만 지키고, 일반 코스는 양 끝에서 멈춘다.
        self.rect.x = max(world.active_start, self.rect.x)
        self.rect.x = min(world.active_end - self.rect.width, self.rect.x)
        if self.rect.left == world.active_start and self.horizontal_velocity < 0:
            self.horizontal_velocity = 0
        if self.rect.right >= world.active_end and self.horizontal_velocity > 0:
            self.horizontal_velocity = 0

    # 지면에 착지한 경우에만 점프 속도를 적용한다.
    def jump(self):  # 지면에 있을 때 점프를 시작
        if self.cheats.get("superjump"):
            self.vy = -20
        elif pygame.time.get_ticks() < self.jump_boost_until:
            self.vy = -18
        else:
            self.vy = self.physics["jump_power"]
        self.on_ground = False  # 점프 직후 지면 상태를 해제
        self.climbing = False  # 점프 시 등반 상태를 해제

    # 추락 후 위치와 수직 이동 상태를 시작점으로 초기화한다.
    def reset_position(self):  # 플레이어 위치·상태 초기화
        self.rect.x, self.rect.y, self.vy = 60, 400, 0  # 플레이어 위치와 세로 속도를 초기화
        self.on_ground = False  # 초기화 후 착지 상태를 해제
        self.climbing = False  # 초기화 후 등반 상태를 해제
