"""에셋에서 배경 음악과 효과음을 불러와 재생한다."""
from pathlib import Path

import pygame


SOUND_DIR = Path(__file__).resolve().parents[1] / "assets" / "sounds"
MUSIC_END_EVENT = pygame.USEREVENT + 1


# 효과음 로딩과 배경 음악 재생·일시 정지를 관리한다.
class AudioManager:
    # 사운드 시스템을 초기화하고 파일이 존재하는 효과음을 불러온다.
    def __init__(self):
        self.effects = {}
        self.music_tracks = [
            SOUND_DIR / "bgm1-wet hands.mp3",
            SOUND_DIR / "bgm2-first step.mp3",
            SOUND_DIR / "bgm3-sweden.mp3",
        ]
        self.track_index = 0
        self.cycle_started = False
        self.paused = False
        self.available = False
        # 믹서를 시작할 수 없으면 오디오 없이 게임이 계속 실행되게 한다.
        try:
            # 이미 시작한 믹서는 재초기화하지 않는다.
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        # 사운드 장치를 쓸 수 없으면 오디오 없이 계속 진행한다.
        except pygame.error:
            return
        self.available = True
        # 배경 음악의 기본 음량과 다음 곡 알림 이벤트를 설정한다.
        try:
            pygame.mixer.music.set_volume(0.35)
            pygame.mixer.music.set_endevent(MUSIC_END_EVENT)
        # 배경 음악 설정이 실패해도 게임 자체는 실행한다.
        except pygame.error:
            pass
        # 준비된 효과음 파일만 사운드 객체로 등록한다.
        for key, filename in {
            "menu": "메뉴 선택.mp3",
            "damage": "몹2, 가시 데미지.mp3",
            "mob2_wrong": "몹2, 가시 데미지.mp3",
            "mob1_wrong": "몹1 오답.mp3",
            "game_over": "게임오버.mp3",
        }.items():
            path = SOUND_DIR / filename
            # 실제 파일이 있는 효과음만 불러온다.
            if path.is_file():
                # 효과음 로드 실패가 나머지 사운드 로드를 막지 않게 한다.
                try:
                    sound = pygame.mixer.Sound(str(path))
                    sound.set_volume(0.65)
                    self.effects[key] = sound
                # 특정 효과음 파일의 오류는 다른 효과음 로드를 막지 않는다.
                except pygame.error:
                    continue

    # 요청된 효과음을 재생하고 일시 정지 상태도 적용한다.
    def play_effect(self, name):
        sound = self.effects.get(name) if self.available else None
        # 등록된 효과음이 있을 때만 재생 시도를 한다.
        if sound:
            # 장치 오류가 효과음 호출을 중단시키지 않도록 보호한다.
            try:
                channel = sound.play()
                # 재생 직후 게임이 정지 상태면 새 채널도 바로 멈춘다.
                if self.paused and channel:
                    channel.pause()
            # 효과음 재생 오류를 무시해 입력 처리를 계속한다.
            except pygame.error:
                pass

    # 배경 음악과 현재 재생 채널을 일시 정지하거나 다시 재생한다.
    def set_paused(self, paused):
        # 오디오를 쓸 수 없거나 상태 변화가 없으면 아무 동작도 하지 않는다.
        if not self.available or self.paused == paused:
            return
        self.paused = paused
        # 믹서 정지·재개 중 장치 오류가 나도 게임 상태는 유지한다.
        try:
            # 게임 정지 상태에 맞춰 음악과 효과음 채널을 함께 제어한다.
            if paused:
                pygame.mixer.music.pause()
                pygame.mixer.pause()
            # 일시 정지를 해제하면 음악과 효과음 재생을 다시 시작한다.
            else:
                pygame.mixer.music.unpause()
                pygame.mixer.unpause()
        # 장치 오류가 나도 게임의 일시 정지 상태는 유지한다.
        except pygame.error:
            pass

    # 게임 오버 음악을 멈추고 게임 오버 효과음을 재생한다.
    def play_game_over(self):
        # 오디오 장치가 준비되지 않았으면 종료 효과음만 생략한다.
        if not self.available:
            return
        # 현재 배경 음악을 멈추고 종료 효과음으로 전환한다.
        try:
            pygame.mixer.music.stop()
        # 이미 멈춘 음악 등 오디오 오류는 게임 오버 진행에 영향을 주지 않는다.
        except pygame.error:
            pass
        self.play_effect("game_over")

    # 메뉴 음악 재생 목록을 시작한다.
    def play_menu_music(self):
        self._start_music_cycle()

    # 게임 음악 재생 목록을 시작한다.
    def play_game_music(self):
        self._start_music_cycle()

    # 곡 종료 이벤트에서 다음 배경 음악을 예약한다.
    def handle_music_event(self, event):
        # 오디오 종료 이벤트가 아니면 호출자가 계속 처리하게 둔다.
        if not self.available or event.type != MUSIC_END_EVENT:
            return False
        tracks = [path for path in self.music_tracks if path.is_file()]
        # 재생 가능한 곡이 없으면 음악 이벤트만 소비한다.
        if not tracks:
            return True
        self.track_index = (self.track_index + 1) % len(tracks)
        self._queue_next(tracks)
        return True

    # 재생 목록에서 첫 곡을 시작하고 다음 곡을 예약한다.
    def _start_music_cycle(self):
        # 오디오를 사용할 수 없거나 이미 시작한 목록이면 중복 실행을 막는다.
        if not self.available or self.cycle_started:
            return
        tracks = [path for path in self.music_tracks if path.is_file()]
        # 파일이 존재하는 곡이 없으면 음악 없이 진행한다.
        if not tracks:
            return
        self.track_index = 0
        # 첫 곡 로드나 재생이 실패해도 게임은 계속 실행한다.
        try:
            pygame.mixer.music.load(str(tracks[self.track_index]))
            pygame.mixer.music.play()
            self.cycle_started = True
            self._queue_next(tracks)
        # 재생 오류가 나면 배경 음악만 건너뛴다.
        except pygame.error:
            pass

    # 현재 곡의 다음 트랙을 순환 목록에서 예약한다.
    def _queue_next(self, tracks):
        # 다음 트랙 예약 오류는 현재 게임 진행에 영향을 주지 않게 한다.
        try:
            next_index = (self.track_index + 1) % len(tracks)
            pygame.mixer.music.queue(str(tracks[next_index]))
        # 다음 곡 예약에 실패하면 현재 재생은 그대로 둔다.
        except pygame.error:
            pass

