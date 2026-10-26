"""에셋에서 배경 음악과 효과음을 불러와 재생한다."""
from pathlib import Path

import pygame


SOUND_DIR = Path(__file__).resolve().parents[1] / "assets" / "sounds"
MUSIC_END_EVENT = pygame.USEREVENT + 1


class AudioManager:
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
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except pygame.error:
            return
        self.available = True
        try:
            pygame.mixer.music.set_volume(0.35)
            pygame.mixer.music.set_endevent(MUSIC_END_EVENT)
        except pygame.error:
            pass
        for key, filename in {
            "menu": "메뉴 선택.mp3",
            "damage": "몹2, 가시 데미지.mp3",
            "mob2_wrong": "몹2, 가시 데미지.mp3",
            "mob1_wrong": "몹1 오답.mp3",
            "game_over": "게임오버.mp3",
        }.items():
            path = SOUND_DIR / filename
            if path.is_file():
                try:
                    sound = pygame.mixer.Sound(str(path))
                    sound.set_volume(0.65)
                    self.effects[key] = sound
                except pygame.error:
                    continue

    def play_effect(self, name):
        sound = self.effects.get(name) if self.available else None
        if sound:
            try:
                channel = sound.play()
                if self.paused and channel:
                    channel.pause()
            except pygame.error:
                pass

    def set_paused(self, paused):
        if not self.available or self.paused == paused:
            return
        self.paused = paused
        try:
            if paused:
                pygame.mixer.music.pause()
                pygame.mixer.pause()
            else:
                pygame.mixer.music.unpause()
                pygame.mixer.unpause()
        except pygame.error:
            pass

    def play_game_over(self):
        if not self.available:
            return
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass
        self.play_effect("game_over")

    def play_menu_music(self):
        self._start_music_cycle()

    def play_game_music(self):
        self._start_music_cycle()

    def handle_music_event(self, event):
        if not self.available or event.type != MUSIC_END_EVENT:
            return False
        tracks = [path for path in self.music_tracks if path.is_file()]
        if not tracks:
            return True
        self.track_index = (self.track_index + 1) % len(tracks)
        self._queue_next(tracks)
        return True

    def _start_music_cycle(self):
        if not self.available or self.cycle_started:
            return
        tracks = [path for path in self.music_tracks if path.is_file()]
        if not tracks:
            return
        self.track_index = 0
        try:
            pygame.mixer.music.load(str(tracks[self.track_index]))
            pygame.mixer.music.play()
            self.cycle_started = True
            self._queue_next(tracks)
        except pygame.error:
            pass

    def _queue_next(self, tracks):
        try:
            next_index = (self.track_index + 1) % len(tracks)
            pygame.mixer.music.queue(str(tracks[next_index]))
        except pygame.error:
            pass

