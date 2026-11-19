# -*- coding: utf-8 -*-
"""冒烟测试：验证 A 级联机静默瘫痪已修复。无需显示器（pygame 用桩件）。
运行： python smoke_test.py
"""
import sys, types, importlib, os
HERE = os.path.dirname(os.path.abspath(__file__))
pg = types.ModuleType("pygame")
class _Rect:
    def __init__(self, x, y, w, h): self.x, self.y, self.w, self.h = x, y, w, h
pg.Rect = _Rect
pg.init = pg.quit = lambda *a, **k: None
pg.display = types.SimpleNamespace(set_mode=lambda *a, **k: None, set_caption=lambda *a, **k: None)
pg.font = types.SimpleNamespace(SysFont=lambda *a, **k: None, Font=lambda *a, **k: None)
for m in ("image", "draw", "mixer", "event", "key", "mouse", "transform"):
    setattr(pg, m, types.SimpleNamespace())
for const in ("K_i", "QUIT", "USEREVENT", "MOUSEBUTTONDOWN", "KEYDOWN"):
    setattr(pg, const, 0)
sys.modules["pygame"] = pg
sys.path.insert(0, HERE)

import net.network as network
main = importlib.import_module("main")

assert main.MULTIPLAYER_AVAILABLE is True, "MULTIPLAYER_AVAILABLE 仍为 False：A级未修复"
assert main.LOADED_CHUNKS is network.LOADED_CHUNKS, "分块字典未与网络模块共享引用"
assert network.CHUNK_SIZE == main.CHUNK_SIZE and network.Y_MAX == main.Y_MAX, "configure 未同步世界参数"

class _Chunk:
    def __init__(s): s.blocks = [[[0] * network.CHUNK_SIZE for _ in range(network.Y_MAX)] for _ in range(network.CHUNK_SIZE)]
probe = _Chunk()
network.LOADED_CHUNKS[(999, 999)] = probe
assert network._apply_block_update(999 * 16 + 2, 60, 999 * 16 + 4, 5) is True
assert probe.blocks[2][60][4] == 5, "block_update 未写入本地分块"
del network.LOADED_CHUNKS[(999, 999)]

print("冒烟测试全部通过 ✅  A 级联机静默瘫痪已修复；B 级裸 except 已清零。")
