from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QComboBox, QSpinBox, QSizePolicy, QFrame, QGridLayout, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import os
from MyQtApp.config import STYLE_FILE, STYLE_DARK_FILE, load_settings, save_settings, DEFAULT_SETTINGS


class AjustesWidget(QWidget):
    """Pantalla de ajustes (UI, lógica de temas, y señales de cambio de estado)."""

    music_volume_changed = pyqtSignal(int)
    sound_volume_changed = pyqtSignal(int)
    music_track_changed = pyqtSignal(int)
    animations_toggled = pyqtSignal(bool)
    theme_toggled = pyqtSignal(bool)
    card_size_changed = pyqtSignal(str)
    logout_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('ajustes_root')
        self.settings = load_settings()

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # --- Top ---
        top_rows = QVBoxLayout()
        top_rows.setSpacing(12)

        def make_audio_row(text, initial_value, callback):
            row = QHBoxLayout()
            lbl = QLabel(text)
            lbl.setProperty('class', 'label_pill')
            lbl.setFont(QFont('Segoe UI', 11))
            lbl.setFixedHeight(36)
            lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            row.addWidget(lbl)

            sp = QLabel("🔊")
            sp.setFixedWidth(28)
            sp.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(sp)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(initial_value)
            slider.setFixedHeight(28)
            slider.valueChanged.connect(callback)
            row.addWidget(slider)
            
            return row, slider

        row_musica, self.slider_musica = make_audio_row('Música', self.settings["volumen_musica"], self.on_music_volume)
        row_sonido, self.slider_sonido = make_audio_row('Sonido', self.settings["volumen_sonido"], self.on_sound_volume)

        top_rows.addLayout(row_musica)
        top_rows.addLayout(row_sonido)

        root.addLayout(top_rows)

        # Divider
        hr = QFrame()
        hr.setFrameShape(QFrame.Shape.HLine)
        hr.setFrameShadow(QFrame.Shadow.Sunken)
        hr.setStyleSheet('color: rgba(0,0,0,0.12);')
        root.addWidget(hr)

        # Font size slider row
        font_row = QHBoxLayout()
        font_pill = QLabel('Tamaño de fuente')
        font_pill.setProperty('class', 'label_pill')
        font_pill.setFixedHeight(36)
        font_row.addWidget(font_pill)

        self.font_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_slider.setRange(8, 30)
        self.font_slider.setValue(self.settings["tamano_fuente"])
        self.font_slider.setFixedHeight(28)
        self.font_slider.valueChanged.connect(self.on_font_size_changed)
        font_row.addWidget(self.font_slider)
        root.addLayout(font_row)

        root.addSpacing(6)

        # Grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)

        # Row 0: Tema
        lbl_tema = QLabel('Tema')
        lbl_tema.setProperty('class', 'label_pill')
        lbl_tema.setFixedHeight(36)
        
        self.btn_tema = QPushButton('Umbreon (Oscuro)' if self.settings["tema_oscuro"] else 'Sylveon (Claro)')
        self.btn_tema.setProperty('class', 'pill')
        self.btn_tema.setFixedHeight(36)
        self.btn_tema.clicked.connect(self.toggle_theme)

        grid.addWidget(lbl_tema, 0, 0)
        grid.addWidget(self.btn_tema, 0, 1)

        lbl_tamcart = QLabel('Tamaño Cartas')
        lbl_tamcart.setProperty('class', 'label_pill')
        lbl_tamcart.setFixedHeight(36)
        self.btn_tamcart = QPushButton(self.settings["tamano_cartas"])
        self.btn_tamcart.setProperty('class', 'pill')
        self.btn_tamcart.setFixedHeight(36)
        self.btn_tamcart.clicked.connect(self.toggle_card_size)
        grid.addWidget(lbl_tamcart, 0, 2)
        grid.addWidget(self.btn_tamcart, 0, 3)

        # Row 1: Animaciones toggle
        lbl_anim = QLabel('Animaciones')
        lbl_anim.setProperty('class', 'label_pill')
        lbl_anim.setFixedHeight(36)
        grid.addWidget(lbl_anim, 1, 0)

        self.btn_anim_si = QPushButton('SI' if self.settings["animaciones"] else 'NO')
        self.btn_anim_si.setProperty('class', 'pill selected' if self.settings["animaciones"] else 'pill')
        self.btn_anim_si.setFixedHeight(36)
        self.btn_anim_si.clicked.connect(self.toggle_animations)
        grid.addWidget(self.btn_anim_si, 1, 1)

        lbl_cambiar = QLabel('Cambiar Música')
        lbl_cambiar.setProperty('class', 'label_pill')
        lbl_cambiar.setFixedHeight(36)
        grid.addWidget(lbl_cambiar, 1, 2)

        self.spin_change = QSpinBox()
        self.spin_change.setRange(1, 3)
        self.spin_change.setValue(self.settings["pista_musica"])
        self.spin_change.setFixedHeight(36)
        self.spin_change.valueChanged.connect(self.on_music_track)
        grid.addWidget(self.spin_change, 1, 3)

        # Row 2: Idioma
        lbl_idioma = QLabel('Idioma')
        lbl_idioma.setProperty('class', 'label_pill')
        lbl_idioma.setFixedHeight(36)
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(['Español', 'English'])
        self.combo_lang.setCurrentText(self.settings["idioma"])
        self.combo_lang.setFixedHeight(36)
        self.combo_lang.currentIndexChanged.connect(self.on_language_changed)
        grid.addWidget(lbl_idioma, 2, 0)
        grid.addWidget(self.combo_lang, 2, 1)

        grid.setColumnStretch(4, 1)
        root.addLayout(grid)

        # Footer
        footer = QHBoxLayout()
        footer.addStretch()
        
        self.btn_logout = QPushButton('Cerrar sesión')
        self.btn_logout.setProperty('class', 'pill logout_btn')
        self.btn_logout.setFixedHeight(36)
        footer.addWidget(self.btn_logout)

        self.btn_rest = QPushButton('Restaurar valores')
        self.btn_save = QPushButton('Guardar')
        for b in (self.btn_rest, self.btn_save):
            b.setProperty('class', 'pill')
            b.setFixedHeight(36)
            footer.addWidget(b)
            
        self.btn_logout.clicked.connect(self.logout_requested.emit)
        self.btn_rest.clicked.connect(self.restaurar_valores)
        self.btn_save.clicked.connect(self.guardar_valores)

        root.addLayout(footer)
        self.setMinimumWidth(700)

    # --- Callbacks Instantáneos ---
    def on_music_volume(self, val):
        self.settings["volumen_musica"] = val
        save_settings(self.settings)
        self.music_volume_changed.emit(val)

    def on_sound_volume(self, val):
        self.settings["volumen_sonido"] = val
        save_settings(self.settings)
        self.sound_volume_changed.emit(val)

    def on_music_track(self, val):
        self.settings["pista_musica"] = val
        save_settings(self.settings)
        self.music_track_changed.emit(val)

    def on_font_size_changed(self, val):
        self.settings["tamano_fuente"] = val
        save_settings(self.settings)
        app = QApplication.instance()
        if app:
            from MyQtApp.config import apply_global_style
            apply_global_style(app)

    def on_language_changed(self, index):
        self.settings["idioma"] = self.combo_lang.currentText()
        save_settings(self.settings)

    def toggle_card_size(self):
        sizes = ["Pequeño", "Normal", "Grande"]
        current = self.settings.get("tamano_cartas", "Normal")
        try:
            next_idx = (sizes.index(current) + 1) % len(sizes)
        except ValueError:
            next_idx = 1
        next_size = sizes[next_idx]
        self.settings["tamano_cartas"] = next_size
        self.btn_tamcart.setText(next_size)
        save_settings(self.settings)
        self.card_size_changed.emit(next_size)

    def toggle_animations(self):
        self.settings["animaciones"] = not self.settings["animaciones"]
        encendido = self.settings["animaciones"]
        self.btn_anim_si.setText('SI' if encendido else 'NO')
        self.btn_anim_si.setProperty('class', 'pill selected' if encendido else 'pill')
        self.btn_anim_si.style().unpolish(self.btn_anim_si)
        self.btn_anim_si.style().polish(self.btn_anim_si)
        save_settings(self.settings)
        self.animations_toggled.emit(encendido)

    def toggle_theme(self):
        app = QApplication.instance()
        if not app:
            return

        self.settings["tema_oscuro"] = not self.settings["tema_oscuro"]
        es_oscuro = self.settings["tema_oscuro"]
        
        self.btn_tema.setText('Umbreon (Oscuro)' if es_oscuro else 'Sylveon (Claro)')
        save_settings(self.settings)
        
        from MyQtApp.config import apply_global_style
        apply_global_style(app)
                
        self.theme_toggled.emit(es_oscuro)

    # --- Persistencia ---
    def restaurar_valores(self):
        self.settings = DEFAULT_SETTINGS.copy()
        save_settings(self.settings)
        
        # Bloquear temporalmente señales para evitar disparos múltiples durante el reset visual
        self.slider_musica.blockSignals(True)
        self.slider_sonido.blockSignals(True)
        self.font_slider.blockSignals(True)
        self.spin_change.blockSignals(True)
        self.combo_lang.blockSignals(True)
        
        self.slider_musica.setValue(self.settings["volumen_musica"])
        self.slider_sonido.setValue(self.settings["volumen_sonido"])
        self.font_slider.setValue(self.settings["tamano_fuente"])
        self.spin_change.setValue(self.settings["pista_musica"])
        self.combo_lang.setCurrentText(self.settings["idioma"])
        self.btn_tamcart.setText(self.settings["tamano_cartas"])
        
        self.slider_musica.blockSignals(False)
        self.slider_sonido.blockSignals(False)
        self.font_slider.blockSignals(False)
        self.spin_change.blockSignals(False)
        self.combo_lang.blockSignals(False)
        
        self.btn_tema.setText('Sylveon (Claro)')
        self.btn_anim_si.setText('SI')
        self.btn_anim_si.setProperty('class', 'pill selected')
        self.btn_anim_si.style().unpolish(self.btn_anim_si)
        self.btn_anim_si.style().polish(self.btn_anim_si)
        
        app = QApplication.instance()
        if app:
            from MyQtApp.config import apply_global_style
            apply_global_style(app)
            
        self.music_volume_changed.emit(self.settings["volumen_musica"])
        self.sound_volume_changed.emit(self.settings["volumen_sonido"])
        self.music_track_changed.emit(self.settings["pista_musica"])
        self.animations_toggled.emit(self.settings["animaciones"])
        self.theme_toggled.emit(self.settings["tema_oscuro"])
        self.card_size_changed.emit(self.settings["tamano_cartas"])

    def guardar_valores(self):
        save_settings(self.settings)
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Ajustes Guardados", "Los ajustes se han guardado y aplicado correctamente.")
