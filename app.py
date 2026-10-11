import sys
import os
import json
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QPlainTextEdit, 
                               QStackedWidget, QProgressBar, QMenuBar, QFileDialog, 
                               QMessageBox, QFrame, QInputDialog, QSpinBox, QCheckBox,
                               QScrollArea, QComboBox, QGraphicsOpacityEffect, QSizePolicy)
from PySide6.QtCore import Qt, QTimer, QTime, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QShortcut, QKeySequence, QFont, QAction, QColor, QTextDocument


class SmoothScrollArea(QScrollArea):
    """A custom scroll area that provides smooth, animated scrolling and hides scrollbars."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.scroll_pos = 0.0
        self.target_pos = 0.0
        
        self.scroll_timer = QTimer(self)
        self.scroll_timer.timeout.connect(self._animate_scroll)

    def wheelEvent(self, event):
        self.scroll_by(event.angleDelta().y() * 2)

    def scroll_by(self, delta):
        """Smoothly scroll by delta pixels (positive = up, negative = down)."""
        max_scroll = self.verticalScrollBar().maximum()
        self.target_pos = max(0.0, min(self.target_pos - delta, float(max_scroll)))
        if not self.scroll_timer.isActive():
            self.scroll_timer.start(16)
            
    def _animate_scroll(self):
        diff = self.target_pos - self.scroll_pos
        if abs(diff) < 1.0:
            self.scroll_pos = self.target_pos
            self.verticalScrollBar().setValue(int(self.target_pos))
            self.scroll_timer.stop()
        else:
            self.scroll_pos += diff * 0.15
            self.verticalScrollBar().setValue(int(self.scroll_pos))
            
    def reset_scroll(self):
        self.scroll_pos = 0.0
        self.target_pos = 0.0
        self.verticalScrollBar().setValue(0)


class SpeakerPresenter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Speaker Pro - Presentation Tool")
        self.resize(1000, 700)
        
        # App State
        self.bullets = []
        self.current_index = 0
        self.font_size = 48
        self.is_timer_running = False
        self.elapsed_time = QTime(0, 0, 0)
        self.show_all_bullets = False  
        self.target_minutes = 5
        self.auto_fit_font = True  # Auto-shrink text so a bullet fits on screen
        
        # Script Library State (Default to Current Working Directory)
        self.scripts_folder = os.getcwd()
        self.current_file = ""
        
        # Config path for auto-save (Stored in Current Working Directory)
        self.config_file = os.path.join(os.getcwd(), ".speaker_pro_config.json")
        
        # Apply a dark mode theme
        self.apply_theme()

        # UI Setup
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.setup_present_view()
        self.setup_edit_view()
        self.setup_menu()
        self.setup_shortcuts()

        # Timer setup
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)

        # Load previous session or default text
        self.load_session()

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; }
            QLabel { color: #f0f0f0; }
            #nextBullet { color: #666666; font-size: 22px; }
            #counterLabel { color: #aaaaaa; font-size: 16px; }
            #timerLabel { color: #ff4d4d; font-size: 16px; font-weight: bold; }
            #scriptNameLabel { color: #888888; font-size: 14px; font-style: italic; }
            QPushButton {
                background-color: #2d2d2d; color: #ffffff;
                border: 1px solid #3d3d3d; padding: 15px 32px;
                border-radius: 5px; font-size: 16px;
            }
            QPushButton:hover { background-color: #3d3d3d; }
            QPushButton#smallBtn {
                padding: 8px 16px; font-size: 14px;
            }
            QPlainTextEdit {
                background-color: #1e1e1e; color: #f0f0f0;
                font-size: 22px; border: 1px solid #3d3d3d;
                padding: 10px;
            }
            QProgressBar {
                background-color: #2d2d2d; border: none; border-radius: 2px; 
                text-align: center; color: white;
            }
            QProgressBar::chunk { background-color: #ff4d4d; border-radius: 2px; }
            QMenuBar { background-color: #1e1e1e; color: white; }
            QMenuBar::item:selected { background-color: #3d3d3d; }
            QMenu { background-color: #1e1e1e; color: white; border: 1px solid #3d3d3d; }
            QMenu::item:selected { background-color: #3d3d3d; }
            #helpOverlay { 
                background-color: rgba(0, 0, 0, 220); 
                color: white; 
                font-size: 24px; 
                padding: 40px; 
                border-radius: 20px;
            }
            QSpinBox {
                background-color: #1e1e1e; color: #f0f0f0;
                border: 1px solid #3d3d3d; padding: 5px;
                font-size: 16px;
            }
            QCheckBox {
                color: #f0f0f0;
                font-size: 16px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #3d3d3d;
                background-color: #1e1e1e;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #ff4d4d;
                border: 1px solid #ff4d4d;
            }
            QComboBox {
                background-color: #1e1e1e; color: #f0f0f0;
                border: 1px solid #3d3d3d; padding: 8px 12px;
                font-size: 16px; border-radius: 5px;
                min-height: 20px;
            }
            QComboBox:hover { border: 1px solid #555555; }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox::down-arrow {
                image: none; border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #aaaaaa;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e1e1e; color: #f0f0f0;
                border: 1px solid #3d3d3d; selection-background-color: #3d3d3d;
                outline: none; padding: 4px;
            }
            QScrollBar:vertical { border: none; background: transparent; width: 0px; margin: 0px; }
            QScrollBar::handle:vertical { background: transparent; min-height: 0px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

    def setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")

        open_action = QAction("Open Script...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        save_action = QAction("Save Script As...", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        set_folder_action = QAction("Set Script Folder...", self)
        set_folder_action.triggered.connect(self.set_scripts_folder)
        file_menu.addAction(set_folder_action)

        open_folder_action = QAction("Open Script Folder in Explorer", self)
        open_folder_action.triggered.connect(self.open_scripts_folder)
        file_menu.addAction(open_folder_action)

        file_menu.addSeparator()

        new_script_action = QAction("New Script from Library", self)
        new_script_action.setShortcut("Ctrl+N")
        new_script_action.triggered.connect(self.new_script)
        file_menu.addAction(new_script_action)

        # --- SETTINGS MENU ---
        settings_menu = menubar.addMenu("Settings")
        
        export_settings_action = QAction("Save Settings As...", self)
        export_settings_action.triggered.connect(self.export_settings)
        settings_menu.addAction(export_settings_action)
        
        import_settings_action = QAction("Load Settings...", self)
        import_settings_action.triggered.connect(self.import_settings)
        settings_menu.addAction(import_settings_action)
        
        settings_menu.addSeparator()
        
        reset_settings_action = QAction("Reset to Default Settings", self)
        reset_settings_action.triggered.connect(self.reset_settings)
        settings_menu.addAction(reset_settings_action)

    def setup_present_view(self):
        self.present_view = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        # Top Bar (Timer, Script Name, and Counter)
        top_bar = QHBoxLayout()
        self.count_label = QLabel("0 / 0")
        self.count_label.setObjectName("counterLabel")
        
        self.script_name_label = QLabel("")
        self.script_name_label.setObjectName("scriptNameLabel")
        self.script_name_label.setAlignment(Qt.AlignCenter)
        
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setObjectName("timerLabel")
        
        top_bar.addWidget(self.count_label)
        top_bar.addStretch()
        top_bar.addWidget(self.script_name_label)
        top_bar.addStretch()
        top_bar.addWidget(self.timer_label)
        layout.addLayout(top_bar)

        # Next bullet (Preview) — single line, elided so long previews
        # never squeeze the main text area.
        self.next_label = QLabel("Next: ...")
        self.next_label.setObjectName("nextBullet")
        self.next_label.setAlignment(Qt.AlignCenter)
        self.next_label.setWordWrap(False)
        self.next_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout.addWidget(self.next_label, stretch=1)

        # Scrollable Current bullet (Main focus)
        self.scroll_area = SmoothScrollArea()
        self.scroll_area.setStyleSheet("background-color: transparent;")
        
        self.current_label = QLabel()
        self.current_label.setObjectName("currentBullet")
        self.current_label.setAlignment(Qt.AlignCenter)
        self.current_label.setWordWrap(True)
        self.update_font_size()
        
        # Fade animation for bullet changes
        self.bullet_opacity = QGraphicsOpacityEffect(self.current_label)
        self.current_label.setGraphicsEffect(self.bullet_opacity)
        self.fade_anim = QPropertyAnimation(self.bullet_opacity, b"opacity", self)
        self.fade_anim.setDuration(180)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        
        self.scroll_area.setWidget(self.current_label)
        layout.addWidget(self.scroll_area, stretch=3)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        layout.addWidget(self.progress_bar)

        # Controls
        self.controls_layout = QHBoxLayout()
        self.prev_btn = QPushButton("◀ Previous (Left)")
        self.edit_btn = QPushButton("✎ Edit Script (E)")
        self.next_btn = QPushButton("Next (Right) ▶")

        self.prev_btn.clicked.connect(self.prev_bullet)
        self.next_btn.clicked.connect(self.next_bullet)
        self.edit_btn.clicked.connect(self.show_edit_view)

        self.prev_btn.setFocusPolicy(Qt.NoFocus)
        self.edit_btn.setFocusPolicy(Qt.NoFocus)
        self.next_btn.setFocusPolicy(Qt.NoFocus)

        self.controls_layout.addWidget(self.prev_btn)
        self.controls_layout.addStretch()
        self.controls_layout.addWidget(self.edit_btn)
        self.controls_layout.addStretch()
        self.controls_layout.addWidget(self.next_btn)

        layout.addLayout(self.controls_layout)
        
        self.present_view.setLayout(layout)
        self.stacked_widget.addWidget(self.present_view)

        # Blackout Overlay
        self.blackout_overlay = QWidget(self.present_view)
        self.blackout_overlay.setStyleSheet("background-color: black;")
        self.blackout_overlay.hide()

        # Help Overlay
        self.help_overlay = QLabel(self.present_view)
        self.help_overlay.setObjectName("helpOverlay")
        self.help_overlay.setAlignment(Qt.AlignCenter)
        self.help_overlay.setText(
            "<b>Keyboard Shortcuts</b><br><br>"
            "Next Bullet: <b>Right Arrow</b> or <b>Space</b><br>"
            "Previous Bullet: <b>Left Arrow</b><br>"
            "First / Last Bullet: <b>Home / End</b><br>"
            "Scroll Long Text: <b>Up / Down Arrows</b> or <b>Mouse Wheel</b><br>"
            "Toggle Overview (All Bullets): <b>O</b><br>"
            "Edit Script: <b>E</b><br>"
            "New Script: <b>Ctrl+N</b><br>"
            "Toggle Fullscreen: <b>F</b><br>"
            "Blackout Screen: <b>B</b><br>"
            "Go to Slide: <b>G</b><br>"
            "Start/Stop Timer: <b>T</b><br>"
            "Reset Timer: <b>R</b><br>"
            "Increase Font: <b>+</b><br>"
            "Decrease Font: <b>-</b><br>"
            "Hide Help: <b>H</b> or <b>Esc</b><br><br>"
            "<i>Tip: Text auto-shrinks to fit the screen. If a bullet is still too long, scroll with ↑/↓!</i>"
        )
        self.help_overlay.hide()

        # "Scroll for more" hint — appears only when the current bullet
        # is longer than the screen and you haven't reached the bottom yet.
        self.scroll_hint = QLabel("▼  Scroll for more  ▼", self.present_view)
        self.scroll_hint.setStyleSheet("color: #777777; font-size: 14px; background: transparent;")
        self.scroll_hint.hide()
        self.scroll_area.verticalScrollBar().valueChanged.connect(lambda _ : self.update_scroll_hint())

    def setup_edit_view(self):
        self.edit_view = QWidget()
        layout = QVBoxLayout()
        
        info_label = QLabel("Type or paste your script here. (One bullet point per line)")
        info_label.setStyleSheet("font-size: 18px; margin-bottom: 10px;")
        
        # ─── Script Library Row ───
        library_layout = QHBoxLayout()
        library_label = QLabel("📁 Script Library:")
        library_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        self.script_combo = QComboBox()
        self.script_combo.setMinimumWidth(350)
        self.script_combo.currentIndexChanged.connect(self.on_script_selected)
        
        self.new_btn = QPushButton("＋ New")
        self.new_btn.setObjectName("smallBtn")
        self.new_btn.clicked.connect(self.new_script)
        
        self.refresh_btn = QPushButton("⟳ Refresh")
        self.refresh_btn.setObjectName("smallBtn")
        self.refresh_btn.clicked.connect(self.refresh_scripts_list)
        
        self.folder_btn = QPushButton("📂 Set Folder...")
        self.folder_btn.setObjectName("smallBtn")
        self.folder_btn.clicked.connect(self.set_scripts_folder)
        
        self.delete_btn = QPushButton("🗑 Delete")
        self.delete_btn.setObjectName("smallBtn")
        self.delete_btn.clicked.connect(self.delete_current_script)
        
        library_layout.addWidget(library_label)
        library_layout.addWidget(self.script_combo, stretch=1)
        library_layout.addWidget(self.new_btn)
        library_layout.addWidget(self.refresh_btn)
        library_layout.addWidget(self.delete_btn)
        library_layout.addWidget(self.folder_btn)
        
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Enter your bullet points here...")
        
        # Settings row
        settings_layout = QHBoxLayout()
        target_label = QLabel("Target Time (minutes):")
        target_label.setStyleSheet("font-size: 16px;")
        self.target_spin = QSpinBox()
        self.target_spin.setRange(0, 999)
        self.target_spin.setValue(self.target_minutes)
        self.target_spin.setFixedWidth(80)
        
        self.overview_checkbox = QCheckBox("Show all bullet points on one slide (Overview Mode)")
        self.autofit_checkbox = QCheckBox("Auto-fit text size (single bullet view)")
        self.autofit_checkbox.setChecked(self.auto_fit_font)
        
        settings_layout.addWidget(target_label)
        settings_layout.addWidget(self.target_spin)
        settings_layout.addSpacing(30)
        settings_layout.addWidget(self.overview_checkbox)
        settings_layout.addSpacing(30)
        settings_layout.addWidget(self.autofit_checkbox)
        settings_layout.addStretch()
        
        save_btn = QPushButton("Save & Present (Esc)")
        save_btn.clicked.connect(self.save_and_present)
        save_btn.setFocusPolicy(Qt.NoFocus)

        layout.addWidget(info_label)
        layout.addLayout(library_layout)
        layout.addWidget(self.text_edit, stretch=1)
        layout.addLayout(settings_layout)
        layout.addWidget(save_btn, alignment=Qt.AlignRight)
        
        self.edit_view.setLayout(layout)
        self.stacked_widget.addWidget(self.edit_view)

        # Auto-save settings when changed
        self.target_spin.valueChanged.connect(self.auto_save_settings)
        self.overview_checkbox.stateChanged.connect(self.auto_save_settings)
        self.autofit_checkbox.stateChanged.connect(self.auto_save_settings)

    def setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Right), self, activated=self.next_bullet)
        QShortcut(QKeySequence(Qt.Key_Space), self, activated=self.next_bullet)
        QShortcut(QKeySequence(Qt.Key_Left), self, activated=self.prev_bullet)
        QShortcut(QKeySequence(Qt.Key_PageDown), self, activated=self.next_bullet)
        QShortcut(QKeySequence(Qt.Key_PageUp), self, activated=self.prev_bullet)
        
        QShortcut(QKeySequence(Qt.Key_E), self, activated=self.show_edit_view)
        
        QShortcut(QKeySequence(Qt.Key_F), self, activated=self.toggle_fullscreen)
        QShortcut(QKeySequence(Qt.Key_T), self, activated=self.toggle_timer)
        QShortcut(QKeySequence(Qt.Key_R), self, activated=self.reset_timer)
        QShortcut(QKeySequence(Qt.Key_B), self, activated=self.toggle_blackout)
        QShortcut(QKeySequence(Qt.Key_G), self, activated=self.go_to_slide)
        
        QShortcut(QKeySequence(Qt.Key_Plus), self, activated=lambda: self.change_font_size(2))
        QShortcut(QKeySequence(Qt.Key_Equal), self, activated=lambda: self.change_font_size(2))
        QShortcut(QKeySequence(Qt.Key_Minus), self, activated=lambda: self.change_font_size(-2))
        
        QShortcut(QKeySequence(Qt.Key_H), self, activated=self.toggle_help)
        QShortcut(QKeySequence(Qt.Key_O), self, activated=self.toggle_all_bullets) 
        
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self.handle_escape)

    def keyPressEvent(self, event):
        """Keyboard scrolling + Home/End navigation (Present view only).
        Implemented via keyPressEvent (not QShortcut) so editing text in the
        editor still works normally."""
        if self.stacked_widget.currentWidget() == self.present_view:
            key = event.key()
            if key == Qt.Key_Up:
                self.scroll_area.scroll_by(160)
                return
            if key == Qt.Key_Down:
                self.scroll_area.scroll_by(-160)
                return
            if key == Qt.Key_Home and self.bullets:
                if self.current_index != 0:
                    self.current_index = 0
                    self.update_display()
                return
            if key == Qt.Key_End and self.bullets:
                last = len(self.bullets) - 1
                if self.current_index != last:
                    self.current_index = last
                    self.update_display()
                return
        super().keyPressEvent(event)

    def handle_escape(self):
        if self.blackout_overlay.isVisible():
            self.blackout_overlay.hide()
        elif self.help_overlay.isVisible():
            self.help_overlay.hide()
        elif self.isFullScreen():
            self.toggle_fullscreen()
        else:
            self.save_and_present()

    # ─── Script Library Methods ───

    def set_scripts_folder(self):
        start_dir = self.scripts_folder if self.scripts_folder and os.path.isdir(self.scripts_folder) \
                    else os.getcwd()
        folder = QFileDialog.getExistingDirectory(self, "Select Script Library Folder", start_dir)
        if folder:
            self.scripts_folder = folder
            self.current_file = ""
            self.refresh_scripts_list()
            self.save_session()
            QMessageBox.information(self, "Script Folder Set", 
                                    f"Script library folder set to:\n{folder}")

    def open_scripts_folder(self):
        if not self.scripts_folder or not os.path.isdir(self.scripts_folder):
            QMessageBox.information(self, "No Folder", "Please set a script folder first.")
            return
        if sys.platform == "win32":
            os.startfile(self.scripts_folder)
        elif sys.platform == "darwin":
            os.system(f'open "{self.scripts_folder}"')
        else:
            os.system(f'xdg-open "{self.scripts_folder}"')

    def refresh_scripts_list(self):
        self.script_combo.blockSignals(True)
        self.script_combo.clear()
        
        if not self.scripts_folder or not os.path.isdir(self.scripts_folder):
            self.script_combo.addItem("⚠ No folder selected — click 'Set Folder...'")
            self.script_combo.blockSignals(False)
            return
        
        files = sorted([f for f in os.listdir(self.scripts_folder) 
                        if f.lower().endswith('.txt')], key=str.lower)
        
        if not files:
            self.script_combo.addItem("📂 No .txt files found in folder")
            self.script_combo.blockSignals(False)
            return
        
        self.script_combo.addItem("── Select a script ──")
        for f in files:
            self.script_combo.addItem(f)
        
        if self.current_file:
            basename = os.path.basename(self.current_file)
            idx = self.script_combo.findText(basename)
            if idx >= 0:
                self.script_combo.setCurrentIndex(idx)
        
        self.script_combo.blockSignals(False)

    def on_script_selected(self, index):
        if index <= 0:
            return
        
        filename = self.script_combo.itemText(index)
        filepath = os.path.join(self.scripts_folder, filename)
        
        if not os.path.exists(filepath):
            return
        
        if self.current_file and self.current_file != filepath:
            self.save_current_script()
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.text_edit.setPlainText(f.read())
            self.current_file = filepath
            self.update_script_name_display()
            self.auto_save_settings()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load file:\n{e}")

    def new_script(self):
        if not self.scripts_folder or not os.path.isdir(self.scripts_folder):
            QMessageBox.information(self, "No Folder", 
                                    "Please set a script library folder first.\n"
                                    "Click 'Set Folder...' to choose one.")
            return
        
        name, ok = QInputDialog.getText(self, "New Script", "Enter script name:", text="My Presentation")
        if not ok or not name.strip():
            return
        
        name = name.strip()
        if not name.lower().endswith('.txt'):
            name += '.txt'
        
        invalid_chars = '<>:"/\\|?*'
        for ch in invalid_chars:
            name = name.replace(ch, '_')
        
        filepath = os.path.join(self.scripts_folder, name)
        
        if os.path.exists(filepath):
            reply = QMessageBox.question(self, "File Exists", f"'{name}' already exists.\nOverwrite it?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        
        self.current_file = filepath
        self.save_current_script()
        self.refresh_scripts_list()
        
        idx = self.script_combo.findText(name)
        if idx >= 0:
            self.script_combo.setCurrentIndex(idx)
        
        self.update_script_name_display()

    def delete_current_script(self):
        if not self.current_file or not os.path.exists(self.current_file):
            QMessageBox.information(self, "Nothing to Delete", "No script file is currently selected.")
            return
        
        filename = os.path.basename(self.current_file)
        reply = QMessageBox.question(self, "Confirm Delete", f"Delete '{filename}'?\nThis cannot be undone.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                os.remove(self.current_file)
                self.current_file = ""
                self.text_edit.clear()
                self.refresh_scripts_list()
                self.update_script_name_display()
                self.auto_save_settings()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete file:\n{e}")

    def save_current_script(self):
        if self.current_file:
            try:
                with open(self.current_file, 'w', encoding='utf-8') as f:
                    f.write(self.text_edit.toPlainText())
            except Exception:
                pass

    def update_script_name_display(self):
        if self.current_file:
            name = os.path.basename(self.current_file)
            self.script_name_label.setText(f"📄 {name}")
            self.setWindowTitle(f"Speaker Pro - {name}")
        else:
            self.script_name_label.setText("")
            self.setWindowTitle("Speaker Pro - Presentation Tool")

    # ─── Settings Save/Load Methods ───

    def get_settings_dict(self):
        return {
            "font_size": self.font_size,
            "target_minutes": self.target_spin.value(),
            "show_all_bullets": self.overview_checkbox.isChecked(),
            "auto_fit_font": self.autofit_checkbox.isChecked(),
            "scripts_folder": self.scripts_folder,
            "current_file": self.current_file,
            "window_width": self.width(),
            "window_height": self.height(),
            "window_x": self.x(),
            "window_y": self.y()
        }

    def apply_settings_dict(self, data):
        self.font_size = data.get("font_size", 48)
        self.target_minutes = data.get("target_minutes", 5)
        self.show_all_bullets = data.get("show_all_bullets", False)
        self.auto_fit_font = data.get("auto_fit_font", True)
        self.scripts_folder = data.get("scripts_folder", os.getcwd())
        self.current_file = data.get("current_file", "")
        
        self.target_spin.blockSignals(True)
        self.target_spin.setValue(self.target_minutes)
        self.target_spin.blockSignals(False)
        
        self.overview_checkbox.blockSignals(True)
        self.overview_checkbox.setChecked(self.show_all_bullets)
        self.overview_checkbox.blockSignals(False)
        
        self.autofit_checkbox.blockSignals(True)
        self.autofit_checkbox.setChecked(self.auto_fit_font)
        self.autofit_checkbox.blockSignals(False)
        
        self.update_font_size()
        
        w = data.get("window_width", 1000)
        h = data.get("window_height", 700)
        self.resize(w, h)
        
        x = data.get("window_x")
        y = data.get("window_y")
        if x is not None and y is not None:
            self.move(x, y)

    def export_settings(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Settings As", "", "JSON Files (*.json)")
        if file_name:
            if not file_name.lower().endswith('.json'):
                file_name += '.json'
            try:
                with open(file_name, 'w', encoding='utf-8') as f:
                    json.dump(self.get_settings_dict(), f, indent=2)
                QMessageBox.information(self, "Settings Saved", f"Settings successfully saved to:\n{file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save settings:\n{e}")

    def import_settings(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Settings", "", "JSON Files (*.json)")
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.apply_settings_dict(data)
                    
                    if self.current_file and os.path.exists(self.current_file):
                        with open(self.current_file, 'r', encoding='utf-8') as ff:
                            self.text_edit.setPlainText(ff.read())
                    else:
                        self.text_edit.clear()
                        self.current_file = ""
                        
                    self.refresh_scripts_list()
                    self.update_script_name_display()
                    self.save_and_present()
                    self.save_session()
                    QMessageBox.information(self, "Settings Loaded", "Settings successfully loaded.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load settings:\n{e}")

    def reset_settings(self):
        reply = QMessageBox.question(self, "Reset Settings", 
                                     "Are you sure you want to reset all settings to their defaults?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            defaults = {
                "font_size": 48,
                "target_minutes": 5,
                "show_all_bullets": False,
                "auto_fit_font": True,
                "scripts_folder": os.getcwd(),
                "current_file": "",
                "window_width": 1000,
                "window_height": 700
            }
            self.apply_settings_dict(defaults)
            self.set_default_text()
            self.save_session()

    def auto_save_settings(self):
        """Auto-saves config silently when settings are changed."""
        self.target_minutes = self.target_spin.value()
        self.show_all_bullets = self.overview_checkbox.isChecked()
        self.auto_fit_font = self.autofit_checkbox.isChecked()
        self.save_session()

    # ─── Session & State Methods ───

    def set_default_text(self):
        self.text_edit.setPlainText(
            "Welcome to Speaker Pro! A powerful, distraction-free presentation tool.\n"
            "1. This is your first bullet point. The audience sees this large and centered.\n"
            "2. Press the Right Arrow or Spacebar to move to the next point.\n"
            "3. Notice the 'Next:' preview at the top of the screen? That's for your eyes only!\n"
            "4. Press 'O' to toggle Overview Mode. (Or check the box in the editor to start here!)\n"
            "5. In Overview Mode, all points are visible. The current one is highlighted in white.\n"
            "6. This is great for showing your audience the agenda or a summary of your talk.\n"
            "7. Press 'F' for Fullscreen. Press 'B' to Blackout the screen during discussions.\n"
            "8. Press 'G' to jump to a specific slide number instantly.\n"
            "9. Press 'T' to start the timer, and 'R' to reset it. Set a target time in the editor!\n"
            "10. Use the Script Library dropdown to manage multiple presentations.\n"
            "11. Click 'Set Folder' to choose where your .txt scripts live, then use 'New' to create more.\n"
            "12. Finally, press 'H' to see the full list of shortcuts, or 'E' to write your own script."
        )
        self.overview_checkbox.setChecked(False)
        self.current_file = ""
        self.refresh_scripts_list()
        self.save_and_present()

    def load_session(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.apply_settings_dict(data)
                    self.refresh_scripts_list()
                    
                    if self.current_file and os.path.exists(self.current_file):
                        try:
                            with open(self.current_file, 'r', encoding='utf-8') as ff:
                                self.text_edit.setPlainText(ff.read())
                        except Exception:
                            self.text_edit.setPlainText(data.get("script", ""))
                    else:
                        self.text_edit.setPlainText(data.get("script", ""))
                        self.current_file = ""
                    
                    self.update_script_name_display()
                    self.save_and_present()
            except Exception:
                self.set_default_text()
        else:
            self.set_default_text()

    def save_session(self):
        try:
            data = self.get_settings_dict()
            data["script"] = self.text_edit.toPlainText()  # Keep script text as hidden backup
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def closeEvent(self, event):
        self.save_session()
        self.save_current_script()
        super().closeEvent(event)

    def save_and_present(self):
        self.save_current_script()
        
        text = self.text_edit.toPlainText()
        self.bullets = [line.strip() for line in text.split('\n') if line.strip()]
        self.current_index = 0
        self.show_all_bullets = self.overview_checkbox.isChecked()
        self.auto_fit_font = self.autofit_checkbox.isChecked()
        self.target_minutes = self.target_spin.value()
        self.update_font_size()
        self.update_display()
        self.update_script_name_display()
        self.stacked_widget.setCurrentWidget(self.present_view)

    def show_edit_view(self):
        if self.isFullScreen():
            self.toggle_fullscreen()
        self.overview_checkbox.setChecked(self.show_all_bullets)
        self.autofit_checkbox.setChecked(self.auto_fit_font)
        self.refresh_scripts_list()
        self.stacked_widget.setCurrentWidget(self.edit_view)
        self.scroll_hint.hide()

    def update_display(self):
        if not self.bullets:
            self.fade_anim.stop()
            self.bullet_opacity.setOpacity(1.0)
            self.current_label.setTextFormat(Qt.PlainText)
            self.update_font_size()
            self.current_label.setText("No bullets found. Press 'E' to edit.")
            self.next_label.setText("")
            self.count_label.setText("0 / 0")
            self.progress_bar.setValue(0)
            self.scroll_area.reset_scroll()
            QTimer.singleShot(0, self.update_scroll_hint)
            return

        if self.show_all_bullets:
            self.fade_anim.stop()
            self.bullet_opacity.setOpacity(1.0)
            self.fit_overview_text()
            self.next_label.setText("Overview Mode (Mouse wheel to scroll - Press 'O' to exit)")
        else:
            self.current_label.setTextFormat(Qt.PlainText)
            self.current_label.setText(self.bullets[self.current_index])
            if self.auto_fit_font:
                self.fit_single_bullet_text()
            else:
                self.update_font_size()
            self.update_next_preview()
            self.start_bullet_fade()

        self.count_label.setText(f"{self.current_index + 1} / {len(self.bullets)}")
        
        progress = int(((self.current_index + 1) / len(self.bullets)) * 100)
        self.progress_bar.setValue(progress)
        
        self.scroll_area.reset_scroll()
        QTimer.singleShot(0, self.update_scroll_hint)

    def fit_overview_text(self):
        if not self.bullets:
            return
            
        self.present_view.layout().activate()
        
        available_width = self.scroll_area.viewport().width() - 40
        available_height = self.scroll_area.viewport().height() - 40
        
        if available_width <= 0 or available_height <= 0:
            available_width = 800
            available_height = 500

        html_parts = []
        for i, bullet in enumerate(self.bullets):
            escaped_bullet = bullet.replace("<", "&lt;").replace(">", "&gt;")
            if i == self.current_index:
                html_parts.append(f'<p style="color: #ffffff; font-weight: bold; margin: 8px 0;">► {escaped_bullet}</p>')
            else:
                html_parts.append(f'<p style="color: #888888; margin: 8px 0;">&nbsp;&nbsp;&nbsp;{escaped_bullet}</p>')
        html = "".join(html_parts)

        min_font_size = 18
        best_font_size = min_font_size
        
        for size in range(self.font_size, min_font_size - 1, -1):
            font = QFont("Arial", size)
            font.setWeight(QFont.Bold)
            
            doc = QTextDocument()
            doc.setHtml(html)
            doc.setDefaultFont(font)
            doc.setTextWidth(available_width)
            
            if doc.size().height() <= available_height:
                best_font_size = size
                break

        font = QFont("Arial", best_font_size)
        font.setWeight(QFont.Bold)
        self.current_label.setFont(font)
        self.current_label.setTextFormat(Qt.RichText)
        self.current_label.setText(html)

    # ─── Single Bullet View Helpers ───

    def fit_single_bullet_text(self):
        """Shrink the font (down to a minimum) so the current bullet fits on screen.
        If it still doesn't fit at the minimum size, smooth scrolling remains available."""
        if not self.bullets:
            return
        text = self.bullets[self.current_index]
        
        self.present_view.layout().activate()
        available_width = self.scroll_area.viewport().width() - 40
        available_height = self.scroll_area.viewport().height() - 40
        
        if available_width <= 0:
            available_width = 800
        if available_height <= 0:
            available_height = 500

        min_font_size = 16
        chosen = min_font_size

        for size in range(self.font_size, min_font_size - 1, -1):
            font = QFont("Arial", size)
            font.setWeight(QFont.Bold)
            doc = QTextDocument()
            doc.setDefaultFont(font)
            doc.setTextWidth(available_width)
            doc.setPlainText(text)
            if doc.size().height() <= available_height:
                chosen = size
                break

        font = QFont("Arial", chosen)
        font.setWeight(QFont.Bold)
        self.current_label.setFont(font)

    def update_next_preview(self):
        """Single-line, elided preview of the next bullet (keeps layout stable)."""
        if not self.bullets:
            self.next_label.setText("")
            return
        if self.current_index + 1 < len(self.bullets):
            next_text = self.bullets[self.current_index + 1]
            metrics = self.next_label.fontMetrics()
            available = max(120, self.next_label.width() - 40)
            elided = metrics.elidedText(next_text, Qt.ElideRight, available)
            self.next_label.setText(f"Next: {elided}")
        else:
            self.next_label.setText("End of script")

    def start_bullet_fade(self):
        """Quick fade-in when the bullet changes."""
        self.fade_anim.stop()
        self.fade_anim.start()

    def update_scroll_hint(self):
        """Show a subtle hint if the current bullet is longer than the screen."""
        if not hasattr(self, 'scroll_hint'):
            return
        if (self.stacked_widget.currentWidget() == self.present_view
                and not self.show_all_bullets
                and self.bullets
                and not self.blackout_overlay.isVisible()
                and not self.help_overlay.isVisible()):
            overflow = self.current_label.height() > self.scroll_area.viewport().height() + 4
            sb = self.scroll_area.verticalScrollBar()
            at_bottom = sb.value() >= sb.maximum() - 2
            if overflow and not at_bottom:
                self.position_scroll_hint()
                self.scroll_hint.show()
                self.scroll_hint.raise_()
            else:
                self.scroll_hint.hide()
        else:
            self.scroll_hint.hide()

    def position_scroll_hint(self):
        if not hasattr(self, 'scroll_hint'):
            return
        geo = self.scroll_area.geometry()
        self.scroll_hint.adjustSize()
        x = geo.center().x() - self.scroll_hint.width() // 2
        y = geo.bottom() - self.scroll_hint.height() - 10
        self.scroll_hint.move(x, y)

    def next_bullet(self):
        if self.stacked_widget.currentWidget() == self.present_view:
            if self.current_index < len(self.bullets) - 1:
                self.current_index += 1
                self.update_display()

    def prev_bullet(self):
        if self.stacked_widget.currentWidget() == self.present_view:
            if self.current_index > 0:
                self.current_index -= 1
                self.update_display()

    def go_to_slide(self):
        if self.stacked_widget.currentWidget() == self.present_view and self.bullets:
            max_slides = len(self.bullets)
            num, ok = QInputDialog.getInt(self, "Go to Slide", f"Enter slide number (1-{max_slides}):", 
                                          min(self.current_index + 1, max_slides), 1, max_slides, 1)
            if ok:
                self.current_index = num - 1
                self.update_display()

    def toggle_all_bullets(self):
        if self.stacked_widget.currentWidget() == self.present_view:
            self.show_all_bullets = not self.show_all_bullets
            self.overview_checkbox.blockSignals(True)
            self.overview_checkbox.setChecked(self.show_all_bullets)
            self.overview_checkbox.blockSignals(False)
            self.auto_save_settings()
            self.update_display()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.menuBar().show()
            for i in range(self.controls_layout.count()):
                w = self.controls_layout.itemAt(i).widget()
                if w is not None:
                    w.show()
        else:
            self.showFullScreen()
            self.menuBar().hide()
            for i in range(self.controls_layout.count()):
                w = self.controls_layout.itemAt(i).widget()
                if isinstance(w, QPushButton):
                    w.hide()

    def toggle_blackout(self):
        if self.stacked_widget.currentWidget() == self.present_view:
            self.blackout_overlay.setGeometry(self.present_view.rect())
            self.blackout_overlay.setVisible(not self.blackout_overlay.isVisible())
            self.blackout_overlay.raise_()
            self.update_scroll_hint()

    def toggle_timer(self):
        if self.stacked_widget.currentWidget() == self.present_view:
            if self.is_timer_running:
                self.timer.stop()
                self.is_timer_running = False
            else:
                self.timer.start(1000) 
                self.is_timer_running = True

    def reset_timer(self):
        if self.stacked_widget.currentWidget() == self.present_view:
            self.timer.stop()
            self.is_timer_running = False
            self.elapsed_time = QTime(0, 0, 0)
            self.timer_label.setText("00:00:00")
            self.timer_label.setStyleSheet("color: #ff4d4d; font-size: 16px; font-weight: bold;")

    def update_timer(self):
        self.elapsed_time = self.elapsed_time.addSecs(1)
        self.timer_label.setText(self.elapsed_time.toString("hh:mm:ss"))
        
        if self.target_minutes > 0:
            target_secs = self.target_minutes * 60
            elapsed_secs = self.elapsed_time.hour() * 3600 + self.elapsed_time.minute() * 60 + self.elapsed_time.second()
            
            if elapsed_secs > target_secs:
                self.timer_label.setStyleSheet("color: #ffcc00; font-size: 16px; font-weight: bold;")
            elif elapsed_secs == target_secs:
                self.timer_label.setStyleSheet("color: #4dff4d; font-size: 16px; font-weight: bold;")

    def change_font_size(self, delta):
        self.font_size = max(12, min(120, self.font_size + delta))
        if self.stacked_widget.currentWidget() == self.present_view:
            if self.show_all_bullets:
                self.fit_overview_text()
            elif self.auto_fit_font:
                self.fit_single_bullet_text()
            else:
                self.update_font_size()
        self.auto_save_settings()

    def update_font_size(self):
        font = QFont("Arial", self.font_size)
        font.setWeight(QFont.Bold)
        self.current_label.setFont(font)

    def toggle_help(self):
        if self.stacked_widget.currentWidget() == self.present_view:
            self.help_overlay.setGeometry(self.present_view.rect())
            self.help_overlay.setVisible(not self.help_overlay.isVisible())
            self.help_overlay.raise_()
            self.update_scroll_hint()

    def resizeEvent(self, event):
        if hasattr(self, 'help_overlay'):
            self.help_overlay.setGeometry(self.present_view.rect())
        if hasattr(self, 'blackout_overlay'):
            self.blackout_overlay.setGeometry(self.present_view.rect())
        if hasattr(self, 'current_label') and self.stacked_widget.currentWidget() == self.present_view:
            if self.show_all_bullets:
                self.fit_overview_text()
            elif self.auto_fit_font:
                self.fit_single_bullet_text()
            if not self.show_all_bullets:
                self.update_next_preview()
            self.position_scroll_hint()
            QTimer.singleShot(0, self.update_scroll_hint)
        super().resizeEvent(event)

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Script", 
                                                     self.scripts_folder or "", 
                                                     "Text Files (*.txt)")
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    self.text_edit.setPlainText(f.read())
                self.current_file = file_name
                
                if self.scripts_folder and os.path.commonpath([self.scripts_folder, file_name]) == self.scripts_folder:
                    self.refresh_scripts_list()
                    basename = os.path.basename(file_name)
                    idx = self.script_combo.findText(basename)
                    if idx >= 0:
                        self.script_combo.setCurrentIndex(idx)
                
                self.update_script_name_display()
                self.save_and_present()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file:\n{e}")

    def save_file(self):
        default_name = os.path.basename(self.current_file) if self.current_file else "script.txt"
        default_path = os.path.join(self.scripts_folder, default_name) if self.scripts_folder else default_name
        
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Script As", default_path, 
                                                     "Text Files (*.txt)")
        if file_name:
            try:
                with open(file_name, 'w', encoding='utf-8') as f:
                    f.write(self.text_edit.toPlainText())
                self.current_file = file_name
                self.update_script_name_display()
                
                if self.scripts_folder and os.path.commonpath([self.scripts_folder, file_name]) == self.scripts_folder:
                    self.refresh_scripts_list()
                    basename = os.path.basename(file_name)
                    idx = self.script_combo.findText(basename)
                    if idx >= 0:
                        self.script_combo.setCurrentIndex(idx)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file:\n{e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpeakerPresenter()
    window.show()
    sys.exit(app.exec())