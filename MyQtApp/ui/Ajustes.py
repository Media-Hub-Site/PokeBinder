from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QComboBox, QSizePolicy, QFrame, QApplication, QMessageBox,
    QDialog, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import os
from MyQtApp.config import STYLE_FILE, STYLE_DARK_FILE, load_settings, save_settings, DEFAULT_SETTINGS, get_available_music_tracks
from MyQtApp.i18n import t, language_manager
from MyQtApp.app.backup import create_database_backup, list_backups, restore_database_backup


def _make_divider():
    hr = QFrame()
    hr.setFrameShape(QFrame.Shape.HLine)
    hr.setFrameShadow(QFrame.Shadow.Sunken)
    hr.setStyleSheet("background-color: rgba(242, 156, 164, 0.3); border: none; max-height: 1px;")
    return hr


def _make_section_card(title: str, icon: str = "") -> tuple:
    """Crea una tarjeta de sección con título y devuelve (card_widget, inner_layout, title_lbl)."""
    card = QWidget()
    card.setObjectName("settings_card")
    card.setStyleSheet("""
        QWidget#settings_card {
            background-color: rgba(255, 247, 248, 0.85);
            border: 1.5px solid rgba(242, 156, 164, 0.4);
            border-radius: 12px;
        }
    """)
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(18, 12, 18, 14)
    card_layout.setSpacing(12)

    title_lbl = None
    if title:
        title_lbl = QLabel(f"  {icon}  {title}" if icon else title)
        title_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #a3364a; border: none; background: transparent; padding-bottom: 2px;")
        card_layout.addWidget(title_lbl)
        card_layout.addWidget(_make_divider())

    return card, card_layout, title_lbl


def _make_setting_row(label_text: str, control: QWidget, label_width: int = 140) -> tuple:
    """Crea una fila etiqueta + control bien alineada y devuelve (row_layout, lbl)."""
    row = QHBoxLayout()
    row.setSpacing(12)
    lbl = QLabel(label_text)
    lbl.setFont(QFont("Segoe UI", 10))
    lbl.setStyleSheet("color: #5a2a3a; border: none; background: transparent;")
    lbl.setFixedWidth(label_width)
    lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
    row.addWidget(lbl)
    row.addWidget(control)
    return row, lbl


def _make_slider_row(label_text: str, icon: str, initial_value: int, callback) -> tuple:
    """Crea fila con ícono + slider + valor y devuelve (row_layout, slider, lbl)."""
    row = QHBoxLayout()
    row.setSpacing(10)

    lbl = QLabel(label_text)
    lbl.setFont(QFont("Segoe UI", 10))
    lbl.setStyleSheet("color: #5a2a3a; border: none; background: transparent;")
    lbl.setFixedWidth(140)
    lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    row.addWidget(lbl)

    icon_lbl = QLabel(icon)
    icon_lbl.setFixedWidth(24)
    icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    row.addWidget(icon_lbl)

    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(0, 100)
    slider.setValue(initial_value)
    slider.setFixedHeight(26)
    row.addWidget(slider, stretch=1)

    val_lbl = QLabel(f"{initial_value}%")
    val_lbl.setFont(QFont("Segoe UI", 9))
    val_lbl.setFixedWidth(36)
    val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    val_lbl.setStyleSheet("color: #888; border: none; background: transparent;")
    row.addWidget(val_lbl)

    def _on_change(v):
        val_lbl.setText(f"{v}%")
        callback(v)

    slider.valueChanged.connect(_on_change)
    return row, slider, lbl


class RestoreBackupDialog(QDialog):
    """Diálogo modal para listar y seleccionar copias de seguridad a restaurar."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("Restaurar Copia de Seguridad"))
        self.setMinimumSize(480, 320)
        self.selected_backup = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        lbl_title = QLabel(t("Selecciona un respaldo para restaurar:"))
        lbl_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #5a2a3a;")
        layout.addWidget(lbl_title)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 1.5px solid rgba(242, 156, 164, 0.5);
                border-radius: 8px;
                padding: 6px;
                background-color: #ffffff;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f2f2f2;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #f29ca4;
                color: white;
            }
        """)

        backups = list_backups()
        if not backups:
            item = QListWidgetItem(t("No se encontraron respaldos de seguridad."))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.list_widget.addItem(item)
        else:
            for filename, full_path, dt_str in backups:
                item = QListWidgetItem(f"📅  {dt_str}   —   ({filename})")
                item.setData(Qt.ItemDataRole.UserRole, full_path)
                self.list_widget.addItem(item)

        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton(t("Cancelar"))
        self.btn_cancel.setFixedHeight(34)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_restore = QPushButton(f"↩️ {t('Restaurar')}")
        self.btn_restore.setFixedHeight(34)
        self.btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restore.clicked.connect(self.on_restore)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_restore)
        layout.addLayout(btn_layout)

    def on_restore(self):
        curr = self.list_widget.currentItem()
        if not curr:
            return
        path = curr.data(Qt.ItemDataRole.UserRole)
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Error", t("No se ha seleccionado una copia válida."))
            return

        reply = QMessageBox.question(
            self,
            t("Confirmar Restauración"),
            t("¿Estás seguro de restaurar este respaldo? Todos los perfiles e inventarios actuales se reemplazarán por esta copia de seguridad."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.selected_backup = path
            self.accept()


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
        self.setObjectName("ajustes_root")
        self.settings = load_settings()

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # ───── Título ──────────────────────────────────────────────────────────
        self.title_lbl = QLabel(f"⚙️  {t('Ajustes')}")
        self.title_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color: #a3364a;")
        root.addWidget(self.title_lbl)

        # ───── Sección 1: Audio ────────────────────────────────────────────────
        audio_card, audio_layout, self.lbl_sec_audio = _make_section_card(t("Audio"), "🎵")

        row_musica, self.slider_musica, self.lbl_musica = _make_slider_row(
            t("Música de fondo"), "🎶", self.settings["volumen_musica"], self.on_music_volume
        )
        row_sonido, self.slider_sonido, self.lbl_sonido = _make_slider_row(
            t("Efectos de sonido"), "🔊", self.settings["volumen_sonido"], self.on_sound_volume
        )
        audio_layout.addLayout(row_musica)
        audio_layout.addLayout(row_sonido)

        # Fila: Pista musical (botones circulares)
        track_row = QHBoxLayout()
        track_row.setSpacing(10)
        self.lbl_track = QLabel(t("Pista de música"))
        self.lbl_track.setFont(QFont("Segoe UI", 10))
        self.lbl_track.setStyleSheet("color: #5a2a3a; border: none; background: transparent;")
        self.lbl_track.setFixedWidth(140)
        self.lbl_track.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        track_row.addWidget(self.lbl_track)

        CIRCLE_BASE = """
            QPushButton {
                background-color: #fff0f3;
                color: #b05060;
                border: 2.5px solid #f29ca4;
                border-radius: 18px;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #fad8de;
                border-color: #e25b70;
            }
        """
        CIRCLE_ACTIVE = """
            QPushButton {
                background-color: #e25b70;
                color: white;
                border: 2.5px solid #c94358;
                border-radius: 18px;
                font-size: 12pt;
                font-weight: bold;
            }
        """
        self._track_btns = []
        current_track = self.settings.get("pista_musica", 1)
        available_tracks = get_available_music_tracks()
        for i in available_tracks:
            btn = QPushButton(str(i))
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(CIRCLE_ACTIVE if i == current_track else CIRCLE_BASE)
            btn.setProperty("track_num", i)
            btn.clicked.connect(lambda checked=False, n=i: self.select_music_track(n))
            track_row.addWidget(btn)
            self._track_btns.append(btn)

        self._circle_base_style = CIRCLE_BASE
        self._circle_active_style = CIRCLE_ACTIVE
        track_row.addStretch()
        audio_layout.addLayout(track_row)

        root.addWidget(audio_card)

        # ───── Sección 2: Apariencia ───────────────────────────────────────────
        ap_card, ap_layout, self.lbl_sec_apariencia = _make_section_card(t("Apariencia"), "🎨")

        # Fila: Tema
        self.btn_tema = QPushButton(t("Tema Oscuro") if self.settings["tema_oscuro"] else t("Tema Claro"))
        self.btn_tema.setProperty("class", "pill")
        self.btn_tema.setFixedHeight(34)
        self.btn_tema.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tema.clicked.connect(self.toggle_theme)
        row_tema, self.lbl_tema = _make_setting_row(t("Tema de color"), self.btn_tema)
        ap_layout.addLayout(row_tema)

        # Fila: Tamaño de cartas
        tam_cart_val = self.settings.get("tamano_cartas", "Normal")
        self.btn_tamcart = QPushButton(t(tam_cart_val))
        self.btn_tamcart.setProperty("class", "pill")
        self.btn_tamcart.setFixedHeight(34)
        self.btn_tamcart.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tamcart.clicked.connect(self.toggle_card_size)
        row_tamcart, self.lbl_tamcart = _make_setting_row(t("Tamaño de cartas"), self.btn_tamcart)
        ap_layout.addLayout(row_tamcart)

        # Fila: Tamaño de fuente con slider
        row_font, self.font_slider, self.lbl_fuente = _make_slider_row(
            t("Tamaño de fuente"), "🔡", self.settings["tamano_fuente"], self.on_font_size_changed
        )
        self.font_slider.setRange(8, 30)
        self.font_slider.setValue(self.settings["tamano_fuente"])
        ap_layout.addLayout(row_font)

        root.addWidget(ap_card)

        # ───── Sección 3: Sistema ──────────────────────────────────────────────
        sys_card, sys_layout, self.lbl_sec_sistema = _make_section_card(t("Sistema"), "🖥️")

        # Fila: Animaciones
        encendido = self.settings["animaciones"]
        self.btn_anim_si = QPushButton(t("SI") if encendido else t("NO"))
        self.btn_anim_si.setProperty("class", "pill selected" if encendido else "pill")
        self.btn_anim_si.setFixedHeight(34)
        self.btn_anim_si.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_anim_si.clicked.connect(self.toggle_animations)
        row_anim, self.lbl_anim = _make_setting_row(t("Animaciones UI"), self.btn_anim_si)
        sys_layout.addLayout(row_anim)

        # Fila: Idioma
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["Español", "English", "日本語", "Français", "Português"])
        current_lang = self.settings.get("idioma", "Español")
        self.combo_lang.setCurrentText(current_lang)
        self.combo_lang.setFixedHeight(34)
        self.combo_lang.setStyleSheet("""
            QComboBox {
                border: 1.5px solid #f29ca4;
                border-radius: 6px;
                padding: 2px 8px;
                font-size: 10pt;
            }
            QComboBox::drop-down { border: none; }
        """)
        self.combo_lang.currentIndexChanged.connect(self.on_language_changed)
        row_lang, self.lbl_idioma = _make_setting_row(t("Idioma"), self.combo_lang)
        sys_layout.addLayout(row_lang)

        root.addWidget(sys_card)

        # ───── Sección 4: Base de Datos y Respaldos ───────────────────────────
        db_card, db_layout, self.lbl_sec_db = _make_section_card(t("Base de Datos y Respaldos"), "🗄️")

        btn_backup_layout = QHBoxLayout()
        btn_backup_layout.setSpacing(12)

        self.btn_create_backup = QPushButton(f"💾 {t('Crear Respaldo')}")
        self.btn_create_backup.setProperty("class", "pill")
        self.btn_create_backup.setFixedHeight(34)
        self.btn_create_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_create_backup.clicked.connect(self.crear_respaldo_manual)

        self.btn_restore_backup = QPushButton(f"📂 {t('Restaurar Respaldo')}")
        self.btn_restore_backup.setProperty("class", "pill")
        self.btn_restore_backup.setFixedHeight(34)
        self.btn_restore_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restore_backup.clicked.connect(self.restaurar_respaldo_manual)

        btn_backup_layout.addWidget(self.btn_create_backup)
        btn_backup_layout.addWidget(self.btn_restore_backup)
        btn_backup_layout.addStretch()

        db_layout.addLayout(btn_backup_layout)
        root.addWidget(db_card)

        root.addStretch()

        # ───── Footer: Acciones ────────────────────────────────────────────────
        footer = QHBoxLayout()
        footer.setSpacing(10)

        self.btn_logout = QPushButton(f"🚪 {t('Cerrar sesión')}")
        self.btn_logout.setProperty("class", "pill logout_btn")
        self.btn_logout.setFixedHeight(36)
        self.btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_logout.clicked.connect(self.logout_requested.emit)

        footer.addWidget(self.btn_logout)
        footer.addStretch()

        self.btn_rest = QPushButton(f"↩️ {t('Restaurar valores')}")
        self.btn_save = QPushButton(f"💾 {t('Guardar')}")
        for b in (self.btn_rest, self.btn_save):
            b.setProperty("class", "pill")
            b.setFixedHeight(36)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            footer.addWidget(b)

        self.btn_rest.clicked.connect(self.restaurar_valores)
        self.btn_save.clicked.connect(self.guardar_valores)

        root.addLayout(footer)
        self.setMinimumWidth(580)

        # Conectar a los cambios de idioma para retraducir dinámicamente esta pantalla
        language_manager.language_changed.connect(self.retranslate_ui)

    def retranslate_ui(self):
        self.title_lbl.setText(f"⚙️  {t('Ajustes')}")
        if self.lbl_sec_audio:
            self.lbl_sec_audio.setText(f"  🎵  {t('Audio')}")
        self.lbl_musica.setText(t("Música de fondo"))
        self.lbl_sonido.setText(t("Efectos de sonido"))
        self.lbl_track.setText(t("Pista de música"))

        if self.lbl_sec_apariencia:
            self.lbl_sec_apariencia.setText(f"  🎨  {t('Apariencia')}")
        self.lbl_tema.setText(t("Tema de color"))
        self.lbl_tamcart.setText(t("Tamaño de cartas"))
        self.lbl_fuente.setText(t("Tamaño de fuente"))

        if self.lbl_sec_sistema:
            self.lbl_sec_sistema.setText(f"  🖥️  {t('Sistema')}")
        self.lbl_anim.setText(t("Animaciones UI"))
        self.lbl_idioma.setText(t("Idioma"))

        if hasattr(self, 'lbl_sec_db') and self.lbl_sec_db:
            self.lbl_sec_db.setText(f"  🗄️  {t('Base de Datos y Respaldos')}")
        if hasattr(self, 'btn_create_backup') and self.btn_create_backup:
            self.btn_create_backup.setText(f"💾 {t('Crear Respaldo')}")
        if hasattr(self, 'btn_restore_backup') and self.btn_restore_backup:
            self.btn_restore_backup.setText(f"📂 {t('Restaurar Respaldo')}")

        es_oscuro = self.settings.get("tema_oscuro", False)
        self.btn_tema.setText(t("Tema Oscuro") if es_oscuro else t("Tema Claro"))

        tam_cart_val = self.settings.get("tamano_cartas", "Normal")
        self.btn_tamcart.setText(t(tam_cart_val))

        encendido = self.settings.get("animaciones", True)
        self.btn_anim_si.setText(t("SI") if encendido else t("NO"))

        self.btn_logout.setText(t("Cerrar sesión"))
        self.btn_rest.setText(f"↩️ {t('Restaurar valores')}")
        self.btn_save.setText(f"💾 {t('Guardar')}")

    def crear_respaldo_manual(self):
        path = create_database_backup(tag="manual")
        if path:
            QMessageBox.information(
                self,
                t("Respaldo Creado"),
                f"{t('Copia de seguridad guardada con éxito en:')}\n{path}"
            )
        else:
            QMessageBox.critical(
                self,
                "Error",
                t("No se pudo crear la copia de seguridad de la base de datos.")
            )

    def restaurar_respaldo_manual(self):
        dlg = RestoreBackupDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_backup:
            if restore_database_backup(dlg.selected_backup):
                QMessageBox.information(
                    self,
                    t("Restauración Completada"),
                    t("La base de datos de perfiles ha sido restaurada con éxito. Por favor, reinicia la aplicación para refrescar todos los datos.")
                )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    t("Ocurrió un error al restaurar la base de datos.")
                )

    # ── Callbacks Instantáneos ─────────────────────────────────────────────────
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

    def select_music_track(self, track_num: int):
        """Selecciona la pista musical y actualiza visualmente los botones circulares."""
        self.settings["pista_musica"] = track_num
        save_settings(self.settings)
        for btn in self._track_btns:
            n = btn.property("track_num")
            btn.setStyleSheet(self._circle_active_style if n == track_num else self._circle_base_style)
        self.music_track_changed.emit(track_num)

    def on_font_size_changed(self, val):
        self.settings["tamano_fuente"] = val
        save_settings(self.settings)
        app = QApplication.instance()
        if app:
            from MyQtApp.config import apply_global_style
            apply_global_style(app)

    def on_language_changed(self, index):
        selected_lang = self.combo_lang.currentText()
        language_manager.set_language(selected_lang)

    def toggle_card_size(self):
        sizes = ["Pequeño", "Normal", "Grande"]
        current = self.settings.get("tamano_cartas", "Normal")
        try:
            next_idx = (sizes.index(current) + 1) % len(sizes)
        except ValueError:
            next_idx = 1
        next_size = sizes[next_idx]
        self.settings["tamano_cartas"] = next_size
        self.btn_tamcart.setText(t(next_size))
        save_settings(self.settings)
        self.card_size_changed.emit(next_size)

    def toggle_animations(self):
        self.settings["animaciones"] = not self.settings["animaciones"]
        encendido = self.settings["animaciones"]
        self.btn_anim_si.setText(t("SI") if encendido else t("NO"))
        self.btn_anim_si.setProperty("class", "pill selected" if encendido else "pill")
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
        self.btn_tema.setText(t("Tema Oscuro") if es_oscuro else t("Tema Claro"))
        save_settings(self.settings)
        from MyQtApp.config import apply_global_style
        apply_global_style(app)
        self.theme_toggled.emit(es_oscuro)

    # ── Persistencia ──────────────────────────────────────────────────────────
    def restaurar_valores(self):
        self.settings = DEFAULT_SETTINGS.copy()
        save_settings(self.settings)

        for w in (self.slider_musica, self.slider_sonido, self.font_slider, self.combo_lang):
            w.blockSignals(True)

        self.slider_musica.setValue(self.settings["volumen_musica"])
        self.slider_sonido.setValue(self.settings["volumen_sonido"])
        self.font_slider.setValue(self.settings["tamano_fuente"])
        self.combo_lang.setCurrentText(self.settings["idioma"])
        language_manager.set_language(self.settings["idioma"])
        self.btn_tamcart.setText(t(self.settings["tamano_cartas"]))

        # Actualizar botones circulares de pista
        default_track = self.settings["pista_musica"]
        for btn in self._track_btns:
            n = btn.property("track_num")
            btn.setStyleSheet(self._circle_active_style if n == default_track else self._circle_base_style)

        for w in (self.slider_musica, self.slider_sonido, self.font_slider, self.combo_lang):
            w.blockSignals(False)

        self.btn_tema.setText(t("Tema Claro"))
        self.btn_anim_si.setText(t("SI"))
        self.btn_anim_si.setProperty("class", "pill selected")
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
        self.retranslate_ui()

    def guardar_valores(self):
        save_settings(self.settings)
        QMessageBox.information(self, t("Ajustes Guardados"), t("Mensaje Guardado"))
