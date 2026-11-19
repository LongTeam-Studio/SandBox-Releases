# -*- coding: utf-8 -*-
"""
多人遊戲網絡模塊 2.0（修复版）
原文件名：多人遊戲網絡連接2_0.py —— 已改名为 net/network.py（ASCII 包名，
跨平台与 pyinstaller 打包安全，修复 C 级工程问题）。

修复要点（A 级）：
- 原版 __all__ 声明导出 CHUNK_SIZE / Y_MAX，但顶层从未定义这两个变量，
  导致主游戏 `from ... import CHUNK_SIZE, Y_MAX` 必然 ImportError，
  被 except ImportError 吞掉，多人游戏静默瘫痪。
  本版本提供模块级默认值 + configure() 注入接口，主游戏在加载分块后调用
  configure(CHUNK_SIZE, Y_MAX, LOADED_CHUNKS) 把真实世界数据同步进来。
- LOADED_CHUNKS 与主游戏共享同一对象引用（原地增删，不重新赋值），
  彻底修复"分块更新到达后本地地图不动"的静默 bug。
"""

import socket
import threading
import json
import time
import sys
from typing import Dict, List, Optional

# 全局玩家数据（由主遊戲維護）
PLAYERS: Dict[str, List[float]] = {}

# 分块尺寸与世界数据：默认值仅为占位，真实值由主游戏通过 configure() 注入。
CHUNK_SIZE = 16
Y_MAX = 128
LOADED_CHUNKS = None  # 由 configure() 设置为主游戏的 OrderedDict[(cx, cz)] -> Chunk


def configure(chunk_size: int, y_max: int, loaded_chunks) -> None:
    """由主游戏在初始化分块后调用，把世界参数与分块字典同步给网络模块。

    loaded_chunks 必须是与主游戏同一对象引用（原地增删），不要重新赋值，
    否则同步会脱钩。
    """
    global CHUNK_SIZE, Y_MAX, LOADED_CHUNKS
    CHUNK_SIZE = chunk_size
    Y_MAX = y_max
    LOADED_CHUNKS = loaded_chunks


def _apply_block_update(block_x, block_y, block_z, block_id) -> bool:
    """把一条 block_update 落到本地分块；成功写入返回 True。"""
    if LOADED_CHUNKS is None:
        return False
    chunk_x, chunk_z = int(block_x // CHUNK_SIZE), int(block_z // CHUNK_SIZE)
    chunk = LOADED_CHUNKS.get((chunk_x, chunk_z))
    if chunk is None:
        return False
    in_x, in_z = int(block_x % CHUNK_SIZE), int(block_z % CHUNK_SIZE)
    if 0 <= in_x < CHUNK_SIZE and 0 <= block_y < Y_MAX and 0 <= in_z < CHUNK_SIZE:
        chunk.blocks[in_x][block_y][in_z] = block_id
        return True
    return False


class NetworkManager:
    """多人遊戲網絡管理器"""

    def __init__(self):
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.player_id: Optional[str] = None
        self.server_socket: Optional[socket.socket] = None
        self.clients: List[socket.socket] = []
        self.running = False
        self.server_address: Optional[tuple] = None

    def connect_to_server(self, host: str, port: int) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.connected = True
            self.player_id = f"player_{int(time.time())}"
            self.send_message({'type': 'player_join',
                               'player_id': self.player_id,
                               'position': [0, 0, 0]})
            threading.Thread(target=self._receive_data, daemon=True).start()
            print(f"[網絡] 成功連接到服務器 {host}:{port}")
            return True
        except Exception as e:
            print(f"[網絡] 連接服務器失敗: {e}")
            return False

    def start_server(self, host: str, port: int) -> bool:
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((host, port))
            self.server_socket.listen(5)
            self.running = True
            self.server_address = self.server_socket.getsockname()
            actual_host, actual_port = self.server_address
            print("\n=== 服務器已啟動 ===")
            print(f"本地地址: 127.0.0.1:{actual_port}")
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                print(f"局域網IP: {local_ip}:{actual_port}")
            except Exception:
                print("局域網IP: 無法獲取")
            print("其他玩家可使用上述地址連接")
            print("輸入 'stop' 可停止服務器\n")
            threading.Thread(target=self._console_handler, daemon=True).start()
            threading.Thread(target=self._accept_clients, daemon=True).start()
            return True
        except Exception as e:
            print(f"[網絡] 啟動服務器失敗: {e}")
            return False

    def stop_server(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        for client in self.clients:
            try:
                client.close()
            except Exception:
                pass
        self.clients.clear()
        print("[網絡] 服務器已停止")

    def _console_handler(self):
        while self.running:
            try:
                if sys.stdin.isatty():
                    cmd = input().strip().lower()
                    if cmd == 'stop':
                        self.stop_server()
                        break
                else:
                    time.sleep(1)
            except (EOFError, KeyboardInterrupt):
                break
            except Exception:
                time.sleep(1)

    def _accept_clients(self):
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                print(f"[網絡] 新客戶端連接: {addr}")
                threading.Thread(target=self._handle_client,
                                 args=(client_socket,), daemon=True).start()
                self.clients.append(client_socket)
            except Exception as e:
                if self.running:
                    print(f"[網絡] 接受連接錯誤: {e}")

    def _handle_client(self, client_socket):
        try:
            while self.running:
                try:
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    messages = data.decode().split('}{')
                    for i, msg in enumerate(messages):
                        if i == 0 and not msg.startswith('{'):
                            msg = '{' + msg
                        if i == len(messages) - 1 and not msg.endswith('}'):
                            msg = msg + '}'
                        elif 0 < i < len(messages) - 1:
                            msg = '{' + msg + '}'
                        try:
                            self._process_message(json.loads(msg), client_socket)
                        except json.JSONDecodeError as e:
                            print(f"[網絡] JSON解析錯誤: {e}, 數據: {msg}")
                except Exception as e:
                    if self.running:
                        print(f"[網絡] 接收客戶端數據錯誤: {e}")
                    break
        except Exception as e:
            print(f"[網絡] 處理客戶端連接錯誤: {e}")
        finally:
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            try:
                client_socket.close()
            except Exception:
                pass
            print("[網絡] 客戶端斷開連接")

    def _process_message(self, message: dict, client_socket):
        msg_type = message.get('type')
        if msg_type == 'player_join':
            player_id = message['player_id']
            PLAYERS[player_id] = message['position']
            print(f"[網絡] 玩家 {player_id} 加入")
            self._broadcast({'type': 'player_joined',
                             'player_id': player_id,
                             'position': message['position']},
                            exclude=client_socket)
        elif msg_type == 'player_move':
            player_id = message['player_id']
            if player_id in PLAYERS:
                PLAYERS[player_id] = message['position']
                self._broadcast({'type': 'player_moved',
                                 'player_id': player_id,
                                 'position': message['position']},
                                exclude=client_socket)
        elif msg_type == 'block_update':
            bx, by, bz = message['position']
            applied = _apply_block_update(bx, by, bz, message['block_id'])
            if not applied:
                # 分块未加载或越界：记录而非静默丢弃（修复 B 级"出错不报"）
                print(f"[網絡] block_update 未命中已加載分塊: pos=({bx},{by},{bz})")
            self._broadcast(message, exclude=client_socket)

    def _broadcast(self, message: dict, exclude=None):
        data = json.dumps(message).encode()
        disconnected = []
        for client in self.clients:
            if client != exclude:
                try:
                    client.send(data)
                except Exception as e:
                    print(f"[網絡] 廣播失敗: {e}")
                    disconnected.append(client)
        for client in disconnected:
            if client in self.clients:
                self.clients.remove(client)
                try:
                    client.close()
                except Exception:
                    pass

    def send_message(self, message: dict):
        if self.connected and self.socket:
            try:
                self.socket.send(json.dumps(message).encode())
            except Exception as e:
                print(f"[網絡] 發送消息失敗: {e}")
                self.connected = False

    def _receive_data(self):
        buffer = ""
        while self.connected:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break
                buffer += data.decode()
                while '}' in buffer:
                    end = buffer.index('}') + 1
                    msg_str, buffer = buffer[:end], buffer[end:]
                    try:
                        self._handle_server_message(json.loads(msg_str))
                    except json.JSONDecodeError as e:
                        print(f"[網絡] JSON解析錯誤: {e}")
            except Exception as e:
                print(f"[網絡] 接收數據錯誤: {e}")
                break
        self.connected = False
        print("[網絡] 與服務器斷開連接")

    def _handle_server_message(self, message: dict):
        msg_type = message.get('type')
        if msg_type in ('player_joined', 'player_moved'):
            PLAYERS[message['player_id']] = message['position']
            if msg_type == 'player_joined':
                print(f"[網絡] 玩家 {message['player_id']} 加入遊戲")
        elif msg_type == 'player_left':
            PLAYERS.pop(message['player_id'], None)
            print(f"[網絡] 玩家 {message['player_id']} 離開遊戲")
        elif msg_type == 'block_update':
            bx, by, bz = message['position']
            _apply_block_update(bx, by, bz, message['block_id'])


# 全局網絡管理器實例
net_manager = NetworkManager()

# 导出符号（修复：CHUNK_SIZE/Y_MAX 现在真实存在）
__all__ = ['net_manager', 'PLAYERS', 'configure', 'CHUNK_SIZE', 'Y_MAX', 'LOADED_CHUNKS']
