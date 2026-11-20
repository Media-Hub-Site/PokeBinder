from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QComboBox, QSizePolicy, QFrame, QApplication, QMessageBox,
    QDialog, QListWidget, QListWidgetItem, QGridLayout, QLineEdit, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QPainter, QPainterPath, QColor
import os
import hashlib
from MyQtApp.config import STYLE_FILE, STYLE_DARK_FILE, load_settings, save_settings, DEFAULT_SETTINGS, get_available_music_tracks, PROJECT_ROOT, ICONS_DIR
from MyQtApp.i18n import t, language_manager
from MyQtApp.app.backup import create_database_backup, list_backups, restore_database_backup
from MyQtApp.session import SessionLocal
from MyQtApp.models import Usuarios


PRESET_AVATARS = [
    ("Pikachu", "assets/images/en/pikachu_basep-1.webp"),
    ("Charizard", "assets/images/en/charizard_dp3-3.webp"),
    ("Gengar", "assets/images/en/gengar_base3-5.webp"),
    ("Eevee", "assets/images/en/eevee_mcd19-12.webp"),
    ("Mewtwo", "assets/images/en/mewtwo_basep-3.webp"),
    ("Lucario", "assets/images/en/lucario_pop6-2.webp"),
    ("Snorlax", "assets/images/en/snorlax_base2-11.webp"),
    ("Squirtle", "assets/images/en/squirtle_bw10-14.webp"),
    ("Bulbasaur", "assets/images/en/bulbasaur_det1-1.webp"),
    ("Charmander", "assets/images/en/charmander_det1-4.webp"),
    ("Jigglypuff", "assets/images/en/jigglypuff_basep-7.webp"),
    ("Mew", "assets/images/en/mew_si1-1.webp"),
]


def _get_circular_avatar(image_path: str | None, size: int = 56) -> QPixmap:
    pixmap = None
    if image_path:
        full_path = image_path
        if not os.path.isabs(full_path):
            full_path = os.path.join(PROJECT_ROOT, image_path)
        if os.path.exists(full_path):
            pixmap = QPixmap(full_path)

    if not pixmap or pixmap.isNull():
        default_icon = os.path.join(ICONS_DIR, "TCG_Logo.png")
        if os.path.exists(default_icon):
            pixmap = QPixmap(default_icon)
        else:
            pixmap = QPixmap(size, size)
            pixmap.fill(QColor("#f7a8b8"))

    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)

    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)

    scaled = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
    ox = (scaled.width() - size) // 2
    oy = (scaled.height() - size) // 2
    painter.drawPixmap(0, 0, scaled, ox, oy, size, size)
    painter.end()
    return result


class AvatarPickerDialog(QDialog):
    """Diálogo para seleccionar un avatar Pokémon preset o subir una imagen personalizada."""

    def __init__(self, current_avatar: str | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("Seleccionar Avatar de Perfil"))
        self.setFixedSize(540, 480)
        self.selected_path = current_avatar

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header = QLabel(t("Elige un Avatar Pokémon o sube una imagen:"))
        header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        header.setStyleSheet("color: #a3364a;")
        layout.addWidget(header)

        # Grid de presets
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(12)

        self.buttons = []
        for idx, (name, path) in enumerate(PRESET_AVATARS):
            r = idx // 4
            c = idx % 4

            btn = QPushButton()
            btn.setFixedSize(96, 96)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(name)

            pix = _get_circular_avatar(path, size=72)
            btn.setIcon(pix)
            btn.setIconSize(pix.size())

            is_selected = (self.selected_path == path)
            border_color = "#e25b70" if is_selected else "rgba(242, 156, 164, 0.4)"
            bg_color = "rgba(242, 156, 164, 0.25)" if is_selected else "rgba(255, 255, 255, 0.8)"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_color};
                    border: 2px solid {border_color};
                    border-radius: 12px;
                }}
                QPushButton:hover {{
                    border-color: #e25b70;
                    background-color: rgba(242, 156, 164, 0.35);
                }}
            """)
            btn.clicked.connect(lambda checked, p=path: self._select_preset(p))
            grid.addWidget(btn, r, c)
            self.buttons.append((btn, path))

        layout.addWidget(grid_widget)

        # Botón para cargar archivo personalizado
        custom_layout = QHBoxLayout()
        self.btn_upload = QPushButton(f"📁  {t('Subir Imagen Personalizada...')}")
        self.btn_upload.setProperty("class", "pill")
        self.btn_upload.setFixedHeight(34)
        self.btn_upload.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_upload.clicked.connect(self._choose_custom_file)
        custom_layout.addWidget(self.btn_upload)
        custom_layout.addStretch()
        layout.addLayout(custom_layout)

        layout.addStretch()

        # Botones de acción
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton(t("Cancelar"))
        self.btn_cancel.setFixedHeight(34)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_apply = QPushButton(f"✔  {t('Aceptar')}")
        self.btn_apply.setProperty("class", "pill")
        self.btn_apply.setFixedHeight(34)
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_apply)
        layout.addLayout(btn_layout)

    def _select_preset(self, path: str):
        self.selected_path = path
        for btn, bpath in self.buttons:
            is_selected = (bpath == path)
            border_color = "#e25b70" if is_selected else "rgba(242, 156, 164, 0.4)"
            bg_color = "rgba(242, 156, 164, 0.25)" if is_selected else "rgba(255, 255, 255, 0.8)"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_color};
                    border: 2px solid {border_color};
                    border-radius: 12px;
                }}
                QPushButton:hover {{
                    border-color: #e25b70;
                    background-color: rgba(242, 156, 164, 0.35);
                }}
            """)

    def _choose_custom_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("Seleccionar Imagen de Avatar"),
            "",
            "Imágenes (*.png *.jpg *.jpeg *.webp *.bmp *.gif)"
        )
        if file_path:
            self.selected_path = file_path
            self.accept()


class PasswordConfigDialog(QDialog):
    """Diálogo para configurar, cambiar o eliminar la contraseña del perfil."""

    def __init__(self, username: str, has_password: bool, parent=None):
        super().__init__(parent)
        self.username = username
        self.has_password = has_password
        self.remove_requested = False
        self.new_password = None

        self.setWindowTitle(t("Seguridad de la Cuenta"))
        self.setFixedSize(380, 270 if has_password else 220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f"🔐  {t('Contraseña para')} {username}")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: #a3364a;")
        layout.addWidget(title)

        if has_password:
            layout.addWidget(QLabel(t("Contraseña actual:")))
            self.txt_old_pwd = QLineEdit()
            self.txt_old_pwd.setEchoMode(QLineEdit.EchoMode.Password)
            self.txt_old_pwd.setPlaceholderText(t("Ingresa contraseña actual"))
            self.txt_old_pwd.setFixedHeight(32)
            layout.addWidget(self.txt_old_pwd)

        layout.addWidget(QLabel(t("Nueva contraseña (deja vacío para eliminar):") if has_password else t("Nueva contraseña:")))
        self.txt_new_pwd = QLineEdit()
        self.txt_new_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_new_pwd.setPlaceholderText(t("Nueva contraseña"))
        self.txt_new_pwd.setFixedHeight(32)
        layout.addWidget(self.txt_new_pwd)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton(t("Cancelar"))
        self.btn_cancel.setFixedHeight(34)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton(f"💾  {t('Guardar')}")
        self.btn_save.setProperty("class", "pill")
        self.btn_save.setFixedHeight(34)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self.on_save)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def on_save(self):
        new_pwd = self.txt_new_pwd.text().strip()
        db = SessionLocal()
        try:
            user = db.query(Usuarios).filter(Usuarios.nombre_usuario == self.username).first()
            if not user:
                QMessageBox.critical(self, "Error", t("Usuario no encontrado."))
                return

            if self.has_password:
                old_pwd = self.txt_old_pwd.text().strip()
                old_hash = hashlib.sha256(old_pwd.encode('utf-8')).hexdigest()
                if user.password_hash and old_hash != user.password_hash:
                    QMessageBox.warning(self, "Error", t("La contraseña actual es incorrecta."))
                    return

            if not new_pwd:
                user.password_hash = None
                db.commit()
                self.remove_requested = True
                QMessageBox.information(self, t("Éxito"), t("La contraseña ha sido eliminada. La cuenta ahora inicia sesión directamente."))
            else:
                user.password_hash = hashlib.sha256(new_pwd.encode('utf-8')).hexdigest()
                db.commit()
                self.new_password = new_pwd
                QMessageBox.information(self, t("Éxito"), t("Contraseña actualizada con éxito."))

            self.accept()
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", f"Error al guardar contraseña: {e}")
        finally:
            db.close()


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

    def __init__(self, usuario=None, parent=None):
        super().__init__(parent)
        self.setObjectName("ajustes_root")
        self.usuario = usuario
        self.settings = load_settings()
        self.user_avatar_path = None
        self.user_has_password = False

        self._load_user_profile_data()

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # ───── Título ──────────────────────────────────────────────────────────
        self.title_lbl = QLabel(f"⚙️  {t('Ajustes')}")
        self.title_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color: #a3364a;")
        root.addWidget(self.title_lbl)

        # ───── Sección 0: Perfil de Usuario ────────────────────────────────────
        if self.usuario:
            prof_card, prof_layout, self.lbl_sec_perfil = _make_section_card(t("Perfil de Usuario"), "👤")

            prof_row = QHBoxLayout()
            prof_row.setSpacing(16)

            # Avatar preview widget
            self.avatar_preview_lbl = QLabel()
            self.avatar_preview_lbl.setFixedSize(56, 56)
            self._update_avatar_preview()
            prof_row.addWidget(self.avatar_preview_lbl)

            # User details & actions
            info_layout = QVBoxLayout()
            info_layout.setSpacing(4)

            self.user_name_lbl = QLabel(f"<b>{self.usuario}</b>")
            self.user_name_lbl.setFont(QFont("Segoe UI", 11))
            self.user_name_lbl.setStyleSheet("color: #5a2a3a; border: none; background: transparent;")
            info_layout.addWidget(self.user_name_lbl)

            btn_sub_layout = QHBoxLayout()
            btn_sub_layout.setSpacing(10)

            self.btn_change_avatar = QPushButton(f"✨  {t('Cambiar Avatar')}")
            self.btn_change_avatar.setProperty("class", "pill")
            self.btn_change_avatar.setFixedHeight(30)
            self.btn_change_avatar.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_change_avatar.clicked.connect(self._open_avatar_picker)
            btn_sub_layout.addWidget(self.btn_change_avatar)

            self.btn_change_pwd = QPushButton()
            self._refresh_pwd_btn_text()
            self.btn_change_pwd.setProperty("class", "pill")
            self.btn_change_pwd.setFixedHeight(30)
            self.btn_change_pwd.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_change_pwd.clicked.connect(self._open_password_config)
            btn_sub_layout.addWidget(self.btn_change_pwd)

            btn_sub_layout.addStretch()
            info_layout.addLayout(btn_sub_layout)

            prof_row.addLayout(info_layout)
            prof_card.layout().addLayout(prof_row)
            root.addWidget(prof_card)
        else:
            self.lbl_sec_perfil = None

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

    def _load_user_profile_data(self):
        if not self.usuario:
            return
        db = SessionLocal()
        try:
            user = db.query(Usuarios).filter(Usuarios.nombre_usuario == self.usuario).first()
            if user:
                self.user_avatar_path = user.avatar
                self.user_has_password = bool(user.password_hash)
        except Exception:
            pass
        finally:
            db.close()

    def _update_avatar_preview(self):
        if hasattr(self, 'avatar_preview_lbl') and self.avatar_preview_lbl:
            pix = _get_circular_avatar(self.user_avatar_path, size=56)
            self.avatar_preview_lbl.setPixmap(pix)

    def _refresh_pwd_btn_text(self):
        if hasattr(self, 'btn_change_pwd') and self.btn_change_pwd:
            if self.user_has_password:
                self.btn_change_pwd.setText(f"🔑  {t('Cambiar/Quitar Contraseña')}")
            else:
                self.btn_change_pwd.setText(f"🔒  {t('Añadir Contraseña')}")

    def _open_avatar_picker(self):
        dlg = AvatarPickerDialog(current_avatar=self.user_avatar_path, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_avatar = dlg.selected_path
            db = SessionLocal()
            try:
                user = db.query(Usuarios).filter(Usuarios.nombre_usuario == self.usuario).first()
                if user:
                    user.avatar = new_avatar
                    db.commit()
                    self.user_avatar_path = new_avatar
                    self._update_avatar_preview()
                    QMessageBox.information(self, t("Avatar Actualizado"), t("Tu nuevo avatar ha sido guardado exitosamente."))
            except Exception as e:
                db.rollback()
                QMessageBox.critical(self, "Error", f"Error al guardar el avatar: {e}")
            finally:
                db.close()

    def _open_password_config(self):
        dlg = PasswordConfigDialog(username=self.usuario, has_password=self.user_has_password, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_user_profile_data()
            self._refresh_pwd_btn_text()

    def retranslate_ui(self):
        self.title_lbl.setText(f"⚙️  {t('Ajustes')}")
        if hasattr(self, 'lbl_sec_perfil') and self.lbl_sec_perfil:
            self.lbl_sec_perfil.setText(f"  👤  {t('Perfil de Usuario')}")
        if hasattr(self, 'btn_change_avatar') and self.btn_change_avatar:
            self.btn_change_avatar.setText(f"✨  {t('Cambiar Avatar')}")
        self._refresh_pwd_btn_text()
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
