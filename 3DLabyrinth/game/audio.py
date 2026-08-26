"""程序化音效与背景音乐：用 numpy 直接合成，无需外部素材文件。"""

from __future__ import annotations

import math

import numpy as np
import pygame

SAMPLE_RATE = 22050


def _to_sound(samples: np.ndarray) -> pygame.mixer.Sound | None:
    data = np.clip(samples, -1.0, 1.0)
    pcm = (data * 32767).astype(np.int16)
    try:
        return pygame.mixer.Sound(buffer=pcm.tobytes())
    except pygame.error:
        return None


class Audio:
    """所有声音均为运行时合成；设备不可用时自动静默。"""

    def __init__(self) -> None:
        self.ok = False
        self.step_i = 0
        self.music_channel = None
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(SAMPLE_RATE, -16, 1, 512)
            self.steps = [self._sound(self._make_step(i)) for i in range(2)]
            self.select = self._sound(self._make_tone(880.0, 0.07, 0.35))
            self.pause = self._sound(self._make_tone(520.0, 0.12, 0.30))
            self.resume = self._sound(self._make_tone(700.0, 0.12, 0.30))
            self.jump = self._sound(self._make_jump())
            self.land = self._sound(self._make_land())
            self.win = self._sound(self._make_win())
            self.music = self._sound(self._make_music())
            self.music.set_volume(0.2)
            self.ok = True
        except pygame.error:
            self.ok = False

    @staticmethod
    def preinit() -> None:
        """必须在 pygame.init() 之前调用。"""
        try:
            pygame.mixer.pre_init(SAMPLE_RATE, -16, 1, 512)
        except pygame.error:
            pass

    def _sound(self, samples: np.ndarray) -> pygame.mixer.Sound:
        snd = _to_sound(samples)
        if snd is None:
            raise pygame.error("sound generation failed")
        return snd

    # ---------- 合成 ----------

    @staticmethod
    def _make_step(seed: int) -> np.ndarray:
        rng = np.random.default_rng(seed)
        n = int(SAMPLE_RATE * 0.08)
        t = np.arange(n) / SAMPLE_RATE
        noise = rng.standard_normal(n)
        k = 8
        noise = np.convolve(noise, np.ones(k) / k, mode="same")
        return noise * np.exp(-t * 45) * 0.5

    @staticmethod
    def _make_tone(freq: float, dur: float, vol: float) -> np.ndarray:
        n = int(SAMPLE_RATE * dur)
        t = np.arange(n) / SAMPLE_RATE
        return np.sin(2 * math.pi * freq * t) * np.exp(-t * 22) * vol

    @staticmethod
    def _make_win() -> np.ndarray:
        notes = (523.25, 659.25, 783.99, 1046.5)
        total = 1.2
        n = int(SAMPLE_RATE * total)
        out = np.zeros(n)
        for i, f in enumerate(notes):
            s = int(i * 0.24 * SAMPLE_RATE)
            e = min(s + int(0.4 * SAMPLE_RATE), n)
            t = np.arange(e - s) / SAMPLE_RATE
            out[s:e] += np.sin(2 * math.pi * f * t) * np.exp(-t * 6) * 0.30
        return out

    @staticmethod
    def _make_jump() -> np.ndarray:
        """上抛音效：短促上行扫频。"""
        dur = 0.18
        n = int(SAMPLE_RATE * dur)
        t = np.arange(n) / SAMPLE_RATE
        freq = 220.0 + 320.0 * (t / dur)
        phase = 2 * math.pi * np.cumsum(freq) / SAMPLE_RATE
        return np.sin(phase) * np.exp(-t * 12) * 0.25

    @staticmethod
    def _make_land() -> np.ndarray:
        """落地音效：低沉短促的撞击。"""
        n = int(SAMPLE_RATE * 0.12)
        t = np.arange(n) / SAMPLE_RATE
        return np.sin(2 * math.pi * 90.0 * t) * np.exp(-t * 28) * 0.40

    @staticmethod
    def _make_music() -> np.ndarray:
        """16 秒的柔和和弦氛围循环。"""
        chords = (
            (220.0, 261.63, 329.63),
            (174.61, 220.0, 261.63),
            (196.0, 246.94, 293.66),
            (196.0, 233.08, 293.66),
        )
        bar = 4.0
        total = bar * len(chords)
        n = int(SAMPLE_RATE * total)
        out = np.zeros(n)
        for ci, chord in enumerate(chords):
            s = int(ci * bar * SAMPLE_RATE)
            e = min(s + int(bar * SAMPLE_RATE), n)
            t = np.arange(e - s) / SAMPLE_RATE
            seg = np.zeros(e - s)
            for f in chord:
                seg += np.sin(2 * math.pi * f * t) * 0.10
                seg += np.sin(2 * math.pi * f * 2 * t) * 0.03
            env = np.minimum(t / 0.9, 1.0) * np.minimum((bar - t) / 0.9, 1.0)
            env = np.clip(env, 0.0, 1.0)
            out[s:e] += seg * env
        fade = int(SAMPLE_RATE * 0.6)
        out[-fade:] *= np.linspace(1.0, 0.0, fade)
        return out * 0.55

    # ---------- 播放 ----------

    def play_step(self) -> None:
        if not self.ok:
            return
        snd = self.steps[self.step_i % 2]
        snd.set_volume(0.30)
        snd.play()
        self.step_i += 1

    def play_select(self) -> None:
        if self.ok:
            self.select.play()

    def play_pause(self) -> None:
        if not self.ok:
            return
        self.pause.play()
        if self.music_channel is not None:
            self.music_channel.pause()

    def play_resume(self) -> None:
        if not self.ok:
            return
        self.resume.play()
        if self.music_channel is not None:
            self.music_channel.unpause()

    def play_jump(self) -> None:
        if self.ok:
            self.jump.play()

    def play_land(self) -> None:
        if self.ok:
            self.land.play()

    def play_win(self) -> None:
        if not self.ok:
            return
        self.music.stop()
        self.win.play()

    def start_music(self) -> None:
        if self.ok:
            self.music_channel = self.music.play(loops=-1)

    def stop_music(self) -> None:
        if self.ok:
            self.music.stop()
            self.music_channel = None
