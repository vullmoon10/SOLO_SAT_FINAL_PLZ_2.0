import pygame
from settings import MOVE_SPEED, GRAVITY, JUMP_POWER, MAX_FALL_SPEED, GROUND_Y


class Player:  # 플레이어 위치와 이동 물리를 관리
    def __init__(self, x=60, y=450, cheats=None):  # 시작 위치와 이동 상태를 초기화
        self.rect = pygame.Rect(x, y, 22, 30)  # 플레이어 충돌 상자
        self.vy = 0.0  # 세로 속도
        self.on_ground = False  # 지면 착지 여부
        self.climbing = False  # 사다리 등반 여부
        self.cheats = cheats or {}  # 이동에 적용할 치트 설정

    def update(self, keys, world):  # 입력·중력·지형 충돌을 반영해 위치를 갱신
        speed = 500 if self.cheats.get("superspeed") else MOVE_SPEED  # 치트 적용 이동 속도
        dx = int(bool(keys[pygame.K_d] or keys[pygame.K_RIGHT])) * speed  # 오른쪽 입력 이동량
        dx -= int(bool(keys[pygame.K_a] or keys[pygame.K_LEFT])) * speed  # 왼쪽 입력 이동량을 차감
        self.rect.x += dx  # 입력 이동량을 가로 위치에 적용

        # 사다리는 플레이어의 발 위치까지 포함해 판정하고, 사다리 밖으로 나가면 중력을 복구
        ladder = next((item for item in world.ladders  # 플레이어와 겹치는 사다리를 찾기
                       if self.rect.centerx >= item.left - 8
                       and self.rect.centerx <= item.right + 8
                       and self.rect.bottom >= item.top
                       and self.rect.top <= item.bottom), None)  # 플레이어와 겹치는 사다리
        climb_input = int(bool(keys[pygame.K_s] or keys[pygame.K_DOWN])) - int(bool(keys[pygame.K_w] or keys[pygame.K_UP]))  # 사다리 위아래 입력 방향
        self.climbing = ladder is not None and climb_input != 0  # 사다리 영역에서 등반 입력 중인지 여부

        previous = self.rect.copy()  # 착지 판정을 위한 이전 프레임 위치
        if self.climbing:  # 사다리를 오르는 동안 중력 대신 입력 이동을 적용
            self.rect.y += climb_input * speed  # 입력 방향 사다리 이동
            self.rect.top = max(self.rect.top, ladder.top - self.rect.height + 2)  # 사다리 위쪽 이동 한계
            self.rect.bottom = min(self.rect.bottom, ladder.bottom)  # 사다리 아래쪽 이동 한계
            self.vy = 0  # 등반 중 중력을 정지
        else:
            self.vy = min(self.vy + GRAVITY, MAX_FALL_SPEED)  # 중력을 반영하고 낙하 속도를 제한
            self.rect.y += int(self.vy)  # 세로 속도를 위치에 적용

        self.on_ground = False  # 이번 프레임 착지 여부를 다시 판정
        if not self.climbing and self.vy >= 0:  # 하강 중일 때 지면·발판 착지를 판정
            for surface in world.ground_segments + world.platforms:
                overlap = self.rect.right > surface.left and self.rect.left < surface.right  # 수평 충돌 범위 중첩 여부
                crossed_top = previous.bottom <= surface.top and self.rect.bottom >= surface.top  # 위에서 표면을 통과했는지 여부
                # 사다리 하강 후 발판 내부 착지 판정
                ladder_exit_landing = (previous.bottom <= surface.top + 3 and self.rect.bottom >= surface.top  # 사다리에서 내려와 발판 높이에 도달했는지 확인
                                       and previous.top < surface.top and self.rect.bottom <= surface.top + 16)
                if overlap and (crossed_top or ladder_exit_landing):  # 착지 조건을 만족하면 발판 위에 정렬
                    self.rect.bottom = surface.top  # 발판 상단에 플레이어를 정렬
                    self.vy = 0  # 착지 시 낙하 속도를 제거
                    self.on_ground = True  # 점프 가능한 착지 상태로 설정
                    break

        # 월드 가장자리에서 플레이어가 무한히 화면 밖으로 걸어나가지 않게 
        self.rect.x = max(0, self.rect.x)  # 월드 시작점 왼쪽으로 이동하지 못하게 

    def jump(self):  # 지면에 있을 때 점프를 시작
        if self.on_ground:  # 공중 점프를 막고 점프 속도를 적용
            self.vy = -20 if self.cheats.get("superjump") else JUMP_POWER  # 치트 설정에 따른 점프 속도
            self.on_ground = False  # 점프 직후 지면 상태를 해제
            self.climbing = False  # 점프 시 등반 상태를 해제

    def reset_position(self):  # 플레이어 위치·상태 초기화
        self.rect.x, self.rect.y, self.vy = 60, 400, 0  # 플레이어 위치와 세로 속도를 초기화
        self.on_ground = False  # 초기화 후 착지 상태를 해제
        self.climbing = False  # 초기화 후 등반 상태를 해제
