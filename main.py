import sys
import os
import json
import webbrowser
import time
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton,
    QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget,
    QFileDialog, QStyle, QDialog, QComboBox,
    QFormLayout, QDialogButtonBox, QProgressBar
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QIcon
from service.check import FileChecking
from service.downloadgame import DownloadWorker, DownloadGame
import requests
from PyQt6.QtCore import QThread, pyqtSignal

class SettingsDialog(QDialog):
    """Окно настроек: выбор языка"""
    def __init__(self, parent, current_lang):
        self.folder_path = os.path.join(os.path.expanduser("~"), "Documents", "Rekape", "RekapeApp")
        self.settingsfile = os.path.join(self.folder_path, "set.json")
        self.cache_path = os.path.join(self.folder_path, "cache")
        self.progress_bars = {}
        self.logfile = os.path.join(self.cache_path, "log.txt")
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setModal(True)
        self.resize(300, 150)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        layout = QFormLayout(self)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Ru", "En"])
        self.lang_combo.setCurrentText(current_lang)
        layout.addRow("Язык:", self.lang_combo)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        cachesize =0
        if os.path.exists(os.path.join(self.cache_path, "log.txt")):
            cachesize = cachesize + os.path.getsize(os.path.join(self.cache_path, "log.txt"))
        if os.path.exists(self.cache_path):
            cachesize = cachesize + os.path.getsize(self.cache_path)
        cachesize /= 1024
        cachesize = round(cachesize, 2)
        self.clearcache = QPushButton(f"Clear cache ({cachesize} Kb)")
        self.clearcache.setFixedSize(130, 30)
        self.clearcache.clicked.connect(self.clearcachefunc)
        layout.addWidget(self.clearcache)
        layout.addRow(self.button_box)
        

    def get_lang(self):
        return self.lang_combo.currentText()
    def clearcachefunc(self):
        if os.path.exists(os.path.join(self.cache_path,"wrg.json")):
            os.remove(os.path.join(self.cache_path,"wrg.json"))
        else:
            pass
        if os.path.exists(os.path.join(self.cache_path,"log.txt")):
            os.remove(os.path.join(self.cache_path,"log.txt"))
        else:
            pass
        cachesize = 0
        cachesize = cachesize + os.path.getsize(self.cache_path)
        cachesize /= 1024
        cachesize = round(cachesize, 2)
        self.clearcache.setText(f"Clear cahce ({cachesize})")
        

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # --- Пути и создание папок ---
        self.folder_path = os.path.join(os.path.expanduser("~"), "Documents", "Rekape", "RekapeApp")
        self.settingsfile = os.path.join(self.folder_path, "set.json")
        self.cache_path = os.path.join(self.folder_path, "cache")
        self.downloader = DownloadGame(self.cache_path, self.log)
        self.game_path_labels = {}
        self.logfile = os.path.join(self.cache_path, "log.txt")
        self.progress_bars = {}
        # Создаём папки, если их нет
        os.makedirs(self.folder_path, exist_ok=True)
        os.makedirs(self.cache_path, exist_ok=True)

        # Если файл настроек отсутствует – создаём с дефолтными значениями
        if not os.path.exists(self.settingsfile):
            default = {
                "language": "Ru",
                "games": {}
            }
            with open(self.settingsfile, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=4, ensure_ascii=False)

        # Читаем настройки
        with open(self.settingsfile, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.lang = data.get("language", "Ru")

        # Загружаем JSON с сервера (синхронно, но можно вынести в поток)
        self.load_game_info("wrg.json")

        # --- Окно ---
        self.setWindowTitle("Rekape App")
        self.setGeometry(100, 100, 1000, 500)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        central = QWidget()
        central.setStyleSheet("background-color: #2a2a2a;")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Верхняя панель ---
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet("background-color: #242424;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)

        self.label1 = QLabel("Rekape App")
        self.label1.setStyleSheet("color: white; font-size: 16px;")
        title_layout.addWidget(self.label1)
        title_layout.addStretch()

        self.minimize_btn = QPushButton("—")
        self.minimize_btn.setFixedSize(35, 28)
        self.minimize_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 18px;
            }
            QPushButton:hover { background-color: #3a3a4a; border-radius: 4px; }
        """)
        self.minimize_btn.clicked.connect(self.showMinimized)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(35, 28)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 18px;
            }
            QPushButton:hover { background-color: #e74c3c; border-radius: 4px; }
        """)
        self.close_btn.clicked.connect(self.close)

        title_layout.addWidget(self.minimize_btn)
        title_layout.addWidget(self.close_btn)
        main_layout.addWidget(title_bar)

        # --- Основная область ---
        main_horizontal = QHBoxLayout()
        main_horizontal.setContentsMargins(0, 0, 0, 0)
        main_horizontal.setSpacing(0)

        # Левая панель
        left_panel = QWidget()
        left_panel.setFixedWidth(200)
        left_panel.setStyleSheet("background-color: #3a3a3a;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        panel_title = QLabel("Игры")
        panel_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        left_layout.addWidget(panel_title)

        # Список игр + JSON-ключи
        self.games = {
            "Winter Racing Game": "wrg",
            "Winter Racing Game Beta": "wrgbeta"
        }

        for game in self.games:
            btn = QPushButton(game)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #cccccc;
                    border: none;
                    text-align: left;
                    padding: 8px 4px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                    border-radius: 4px;
                }
            """)
            btn.clicked.connect(lambda checked, g=game: self.on_game_selected(g))
            left_layout.addWidget(btn)

        left_layout.addStretch()  # растяжение между играми и кнопкой настроек

        # Кнопка "Настройки"
        settings_btn = QPushButton(" Настройки")
        settings_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        settings_btn.setIcon(settings_icon)
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #cccccc;
                border: none;
                text-align: left;
                padding: 8px 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border-radius: 4px;
            }
        """)
        settings_btn.clicked.connect(self.open_settings)
        left_layout.addWidget(settings_btn)
        #Button site
        websitebtn = QPushButton(" WebSite")
        websiteicon = self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        websitebtn.setIcon(websiteicon)
        websitebtn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #cccccc;
                border: none;
                text-align: left;
                padding: 8px 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border-radius: 4px;
            }
        """)
        websitebtn.clicked.connect(self.website)
        left_layout.addWidget(websitebtn)
        # Правая область (QStackedWidget)
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: #2a2a2a;")
        self.game_pages = {}
        self.game_descs = {}  # для обновления описаний при смене языка

        for game, json_key in self.games.items():
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(20, 20, 20, 20)

            title = QLabel(game)
            title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
            layout.addWidget(title)

            path_label = QLabel("Путь: не выбран")
            path_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
            path_label.setWordWrap(True)
            layout.addWidget(path_label)
            self.game_path_labels[game] = path_label

            desc = QLabel("Описание загружается...")
            desc.setWordWrap(True)
            desc.setStyleSheet("color: #cccccc; font-size: 14px;")

            # Загрузка описания из кэша
            cache_file = os.path.join(self.settingsfile, f"{json_key}.json")
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        desc.setText(data.get("Description" + self.lang, "Описание не найдено"))
                except:
                    desc.setText("Ошибка чтения описания")
            else:
                desc.setText("Описание для этой игры не найдено")

            layout.addWidget(desc)
            self.game_descs[game] = desc
            progress_bar = QProgressBar()
            progress_bar.setVisible(False)   # скрыт по умолчанию
            progress_bar.setFixedHeight(20)
            progress_bar.setStyleSheet("""
    QProgressBar {
        border: 1px solid #444;
        border-radius: 4px;
        background-color: #1e1e2a;
        color: white;
        text-align: center;
    }
    QProgressBar::chunk {
        background-color: #4a6a8a;
        border-radius: 4px;
    }
""")
            layout.addWidget(progress_bar)
            self.progress_bars[game] = progress_bar
            
            # Кнопки: "Выбрать папку" + "Запустить"
            btn_layout = QHBoxLayout()
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            svg_path = os.path.join(BASE_DIR, "static", "res", "folderasset.svg")
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
            locate_btn = QPushButton(icon, "")
            locate_btn.setFixedSize(30, 30)
            locate_btn.setToolTip("Выбрать папку с игрой")
            locate_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #3a3a4a;
                    border-radius: 4px;
                }
            """)
            locate_btn.clicked.connect(lambda checked, g=game: self.locate_game_folder(g))
            btn_layout.addWidget(locate_btn)

            launch_btn = QPushButton("Запустить")
            launch_btn.setFixedSize(120, 30)
            launch_btn.clicked.connect(lambda checked, g=game: self.startgame(g))
            launch_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4a6a8a;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    padding: 4px 10px;
                }
                QPushButton:hover { background-color: #5a8aaa; }
            """)
            btn_layout.addWidget(launch_btn)
            

            download_btn = QPushButton("Установить")
            download_btn.setFixedSize(120, 30)
            download_btn.clicked.connect(lambda checked, g=game: self.download_game_in_background(g))
            download_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4a6a8a;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                    padding: 4px 10px;
                }
                QPushButton:hover { background-color: #5a8aaa; }
            """)
            btn_layout.addWidget(download_btn)
            btn_layout.addStretch()
            layout.addLayout(btn_layout)
            layout.addStretch()

            self.stacked_widget.addWidget(page)
            self.game_pages[game] = page

        if self.games:
            self.stacked_widget.setCurrentWidget(self.game_pages[list(self.games.keys())[0]])

        main_horizontal.addWidget(left_panel)
        main_horizontal.addWidget(self.stacked_widget)

        main_layout.addLayout(main_horizontal)

        self.drag_pos = None

    def website(self):
        url = 'http://127.0.0.1:5000/'
        webbrowser.open(url)
    # --- Загрузка JSON с сервера ---
    def load_game_info(self, jsoncode):
        url = "http://127.0.0.1:5000/wrg/json"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            cache_file = os.path.join(self.cache_path, jsoncode)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print("[OK] JSON сохранён в кэш")
            self.log("[OK] wrg.json saved in cache folder")
        except Exception as e:
            print(f"[WARN] Не удалось загрузить JSON: {e}")
            self.log("[WARN] Failed to load json")

    def log(self, mes):
        with open(self.logfile, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " " + mes + "\n")

    
    def update_game_path(self, game_name):
        with open(self.settingsfile, "r", encoding="utf-8") as f:
            data = json.load(f)
        game_data = data.get("games", {}).get(game_name, {})
        game_path = game_data.get("path", "")
        label = self.game_path_labels.get(game_name)
        if label:
            if game_path:
                label.setText(f"Путь: {game_path}")
        else:
            label.setText("Путь: не выбран")

    
    def downloaded(self,game_name):
        progress_bar = self.progress_bars.get(game_name)
        progress_bar.setVisible(False)
        
    def download_game_in_background(self, game_name):
        game_key = self.games.get(game_name)
        if not game_key:
            self.log(f"❌ Игра {game_name} не найдена")
            return
        progress_bar = self.progress_bars.get(game_name)
        if progress_bar:
            progress_bar.setVisible(True)
            progress_bar.setValue(0)
        self.worker = DownloadWorker(self.downloader, game_key)
        self.worker.progress.connect(lambda value: self.on_download_progress(game_name, value))
        self.worker.start()
        self.log(f"[INFO] Загрузка {game_name} начата...")
    def open_settings(self):
        dialog = SettingsDialog(self, self.lang)
        if dialog.exec():
            new_lang = dialog.get_lang()
            if new_lang != self.lang:
                self.lang = new_lang
                # Сохраняем в настройки
                with open(self.settingsfile, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["language"] = self.lang
                with open(self.settingsfile, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                self.log(f"Язык изменён на {self.lang}")
                # Обновляем описания на всех страницах
                self.refresh_game_descriptions()

    def refresh_game_descriptions(self):
        """Перечитывает JSON-файлы и обновляет текст описания"""
        for game, json_key in self.games.items():
            desc = self.game_descs.get(game)
            if desc is None:
                continue
            cache_file = os.path.join(self.cache_path, f"{json_key}.json")
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        desc.setText(data.get("Description" + self.lang, "Описание не найдено"))
                except Exception as e:
                    desc.setText("Ошибка чтения описания")
                    self.log(f"Ошибка чтения {cache_file}: {e}")
            else:
                desc.setText("Описание для этой игры не найдено")

    
    def on_game_selected(self, game_name: str):
        if game_name in self.game_pages:
            self.stacked_widget.setCurrentWidget(self.game_pages[game_name])
        else:
            print(f"Страница для {game_name} не найдена")

   
    def startgame(self, game):
        with open(self.settingsfile, "r", encoding="utf-8") as f:
            data = json.load(f)
            game_data = data.get("games", {}).get(game, {})
            game_path = game_data.get("path", "")
            if not game_path:
                self.log(f"❌ Путь к игре {game} не задан")
                return
            exe_name = f"{game}.exe"
            exe_path = os.path.join(game_path, exe_name)
            if not os.path.exists(exe_path):
                self.log(f"❌ Исполняемый файл не найден: {exe_path}")
                return
            try:
                os.startfile(exe_path)
                self.log(f"✅ Запущена игра {game}")
            except Exception as e:
                self.log(f"❌ Ошибка запуска: {e}")
    def update_game_path(self, game_name):
        with open(self.settingsfile, "r", encoding="utf-8") as f:
            data = json.load(f)
        game_data = data.get("games", {}).get(game_name, {})
        game_path = game_data.get("path", "")
        label = self.game_path_labels.get(game_name)
        if label:
            if game_path:
                label.setText(f"Путь: {game_path}")
        else:
            label.setText("Путь: не выбран")
    
    def locate_game_folder(self, game_name):
        folder = QFileDialog.getExistingDirectory(
            self,
            f"Выберите папку с игрой {game_name}",
            os.path.expanduser("~")
        )
        if folder:
            self.log(f"[{game_name}] Папка выбрана: {folder}")
            with open(self.settingsfile, "r", encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("games", {})
            data["games"].setdefault(game_name, {})
            data["games"][game_name]["path"] = folder
            self.update_game_path(game_name) 
            with open(self.settingsfile, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
    def on_download_progress(self, game_name, percent):
        progress_bar = self.progress_bars.get(game_name)
        progress_bar.setVisible(True)
        if progress_bar:
            progress_bar.setValue(percent)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            widget_at = self.childAt(event.pos())
            if not isinstance(widget_at, QPushButton):
                self.drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.drag_pos is not None:
            delta = event.globalPosition().toPoint() - self.drag_pos
            self.move(self.pos() + delta)
            self.drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())