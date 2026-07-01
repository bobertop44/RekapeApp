import os
import requests
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

class DownloadGame:
    def __init__(self, cache_path, log_func=None):
        self.cache_path = cache_path
        self.log_func = log_func or print

    def download_game_info(self, game_key: str, url: str = None, progress_callback=None) -> bool:
        if not url:
            if game_key == "wrg":
                url = "http://127.0.0.1:5000/wrg/download"
            elif game_key == "wrgbeta":
                url = "http://127.0.0.1:5000/wrgbeta/download"
            else:
                self.log("[Error] URL not specified.")
                return False

        try:
            response = requests.get(url, timeout=10, stream=True)
            response.raise_for_status()

            Path(self.cache_path).mkdir(parents=True, exist_ok=True)

            ext = ".rar"
            file_name = f"{game_key}{ext}"
            file_path = os.path.join(self.cache_path, file_name)

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0 and progress_callback:
                            percent = int((downloaded / total_size) * 100)
                            progress_callback(percent)

            self.log(f"✅ {file_name} загружен")
            return True

        except Exception as e:
            self.log(f"❌ Ошибка загрузки: {e}")
            return False

    def log(self, message):
        if self.log_func:
            self.log_func(message)
        else:
            print(message)


class DownloadWorker(QThread):
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(int)   # новый сигнал

    def __init__(self, downloader, game_key, url=None):
        super().__init__()
        self.downloader = downloader
        self.game_key = game_key
        self.url = url

    def run(self):
        # Передаём callback для прогресса
        success = self.downloader.download_game_info(
            self.game_key,
            self.url,
            progress_callback=self.progress.emit
        )
        if success:
            self.finished.emit(True, f"{self.game_key} скачан")
        else:
            self.finished.emit(False, f"Ошибка скачивания {self.game_key}")