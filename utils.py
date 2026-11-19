"""日志工具：GameLogger + log()。依赖 config.LOG_DIR。"""
import os
import sys
import traceback
from datetime import datetime
from config import *


class GameLogger:
    """遊戲日誌系統"""
    def __init__(self, log_dir, enabled=True):
        self.log_dir = log_dir
        self.enabled = enabled
        self.log_file = None
        self.console_output = True
        self.log_levels = {"INFO": "[INFO]", "WARNING": "[WARNING]", "ERROR": "[ERROR]", "FATAL": "[FATAL]", "EXIT": "[EXIT]"}
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        if self.enabled:
            self._create_log_file()
    
    def _create_log_file(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            log_filename = f"{timestamp}-sandboxlog.log"
            self.log_file_path = os.path.join(self.log_dir, log_filename)
            self.log_file = open(self.log_file_path, 'a', encoding='utf-8')
            self._write_to_file(f"=== 沙盒遊戲日誌文件 ===\n")
            self._write_to_file(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self._write_to_file(f"遊戲版本: 1.11.1 正式版\n")
            self._write_to_file(f"操作系統: {sys.platform}\n")
            self._write_to_file("=" * 40 + "\n")
            return True
        except Exception as e:
            print(f"[ERROR] 創建日誌文件失敗: {e}")
            return False
    
    def _get_timestamp(self):
        return datetime.now().strftime("[%H:%M:%S]")
    
    def _write_to_file(self, message):
        if self.log_file and not self.log_file.closed:
            try:
                self.log_file.write(message)
                self.log_file.flush()
            except Exception:
                pass
    
    def _format_message(self, level, message):
        return f"{self._get_timestamp()} {self.log_levels.get(level, '[UNKNOWN]')} {message}\n"
    
    def log(self, level, message):
        if not self.enabled:
            return
        formatted = self._format_message(level, message)
        if self.console_output:
            print(formatted.rstrip())
        self._write_to_file(formatted)
    
    def info(self, message):
        self.log("INFO", message)
    def warning(self, message):
        self.log("WARNING", message)
    def error(self, message):
        self.log("ERROR", message)
    def fatal(self, message):
        self.log("FATAL", message)
    def exit(self, message, exit_code=0):
        self.log("EXIT", f"{message}, Exit Code: {exit_code}")
    def exception(self, message, exception_obj=None):
        if exception_obj:
            exc_info = traceback.format_exception(type(exception_obj), exception_obj, exception_obj.__traceback__)
            exc_str = "".join(exc_info)
            self.error(f"{message}\n異常詳情:\n{exc_str}")
        else:
            self.error(message)
    def set_enabled(self, enabled):
        self.enabled = enabled
        if enabled and not self.log_file:
            self._create_log_file()
        elif not enabled and self.log_file:
            self.close()
    def close(self):
        if self.log_file:
            try:
                self.log_file.close()
                self.log_file = None
            except Exception:
                pass


def log(content):
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, f"game_{datetime.now().strftime('%Y%m%d')}.log")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {content}\n")
    except Exception as e:
        print(f"日志写入失败: {e}")

