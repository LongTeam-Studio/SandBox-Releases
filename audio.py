"""音频模块：初始化音效、合成波形、播放声音和背景音乐。
SETTINGS/SOUNDS/game_logger 留在 main.py，运行时通过 import main 访问。
"""
import math
import os
import random
import sys
import pygame
import main
from config import *
from utils import log

__all__ = ["init_sounds","create_sine_wave","create_eating_sound","play_sound","play_random_ogg_music"]

def init_sounds():
    try:
        if not os.path.exists(TOOL_DIR):
            os.makedirs(TOOL_DIR, exist_ok=True)
        
        # 創建簡單音效
        main.SOUNDS["dig"] = pygame.mixer.Sound(buffer=create_sine_wave(440, 0.1, 44100))
        main.SOUNDS["place"] = pygame.mixer.Sound(buffer=create_sine_wave(220, 0.1, 44100))
        main.SOUNDS["hurt"] = pygame.mixer.Sound(buffer=create_sine_wave(880, 0.1, 44100))
        main.SOUNDS["eat"] = pygame.mixer.Sound(buffer=create_eating_sound())
        
        for sound in main.SOUNDS.values():
            if sound:
                sound.set_volume(main.SETTINGS["sound_volume"])
        pygame.mixer.music.set_volume(main.SETTINGS["music_volume"])
    except Exception as e:
        log(f"音效初始化失敗：{str(e)}")


def create_sine_wave(freq, duration, sample_rate):
    samples = int(duration * sample_rate)
    wave = bytearray()
    for i in range(samples):
        t = i / sample_rate
        val = 0.5 * math.sin(2 * math.pi * freq * t)
        sample = int(val * 32767)
        wave.extend(sample.to_bytes(2, 'little', signed=True))
    return bytes(wave)


def create_eating_sound():
    sample_rate = 44100
    duration = 0.3
    samples = int(duration * sample_rate)
    wave = bytearray()
    for i in range(samples):
        t = i / sample_rate
        freq1 = 300 + 50 * math.sin(2 * math.pi * 5 * t)
        freq2 = 600 + 100 * math.sin(2 * math.pi * 8 * t)
        val = 0.3 * math.sin(2 * math.pi * freq1 * t) + 0.2 * math.sin(2 * math.pi * freq2 * t)
        val *= math.exp(-3 * t)
        sample = int(val * 32767)
        wave.extend(sample.to_bytes(2, 'little', signed=True))
    return bytes(wave)


def play_sound(sound_name):
    if main.SOUNDS.get(sound_name):
        try:
            main.SOUNDS[sound_name].play()
        except Exception as e:
            log(f"音效播放失敗：{str(e)}")


def play_random_ogg_music(prefix=None):
    """隨機播放OGG音樂，可指定前綴過濾"""
    if not os.path.exists(OGG_DIR):
        if main.game_logger:
            main.game_logger.warning("音樂目錄不存在，跳過播放")
        return
    ogg_files = [f for f in os.listdir(OGG_DIR) if f.lower().endswith(".ogg")]
    if prefix is not None:
        ogg_files = [f for f in ogg_files if f.lower().startswith(prefix.lower())]
    if not ogg_files:
        if main.game_logger:
            main.game_logger.warning(f"無匹配的ogg音樂文件（前綴：{prefix}），跳過播放")
        return
    try:
        random_ogg = random.choice(ogg_files)
        ogg_path = os.path.join(OGG_DIR, random_ogg)
        pygame.mixer.music.load(ogg_path)
        pygame.mixer.music.play()
        pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)
        if main.game_logger:
            main.game_logger.info(f"播放音樂：{random_ogg}")
    except Exception as e:
        if main.game_logger:
            main.game_logger.error(f"音樂加載失敗：{str(e)}")

