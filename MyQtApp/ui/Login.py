import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame, QScrollArea, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QColor, QFont

from ..session import SessionLocal
from ..models import Usuarios
from MyQtApp.i18n import t, language_manager
from MyQtApp.config import PROJECT_ROOT, ICONS_DIR


def get_circular_avatar(image_path: str | None, size: int = 46) -> QPixmap:
    """Genera un avatar circular recortado a partir de una ruta o el logo por defecto."""
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
    # Centrar recorte
    ox = (scaled.width() - size) // 2
    oy = (scaled.height() - size) // 2
    painter.drawPixmap(0, 0, scaled, ox, oy, size, size)
    painter.end()

    return result


class AccountProfileCard(QFrame):
    """Tarjeta tipo botón interactivo para alternar y seleccionar perfil estilo Twitter/Switch."""
    selected = pyqtSignal(str)

    def __init__(self, username: str, avatar_path: str | None = None, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.username = username
        self.avatar_path = avatar_path
        self.is_active = is_active
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(58)
        self.setObjectName("AccountProfileCard")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(12)

        # Avatar circular
        self.avatar_lbl = QLabel()
        self.avatar_lbl.setFixedSize(44, 44)
        self.avatar_lbl.setPixmap(get_circular_avatar(avatar_path, 44))
        layout.addWidget(self.avatar_lbl)

        # Info del usuario (Nombre + Badge de cuenta local)
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 2, 0, 2)
        info_layout.setSpacing(1)

        self.lbl_name = QLabel(username)
        self.lbl_name.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_name.setObjectName("AccountCardName")

        self.lbl_subtitle = QLabel(t("Cuenta local"))
        self.lbl_subtitle.setObjectName("AccountCardSubtitle")
        self.lbl_subtitle.setStyleSheet("color: #888888; font-size: 11px;")

        info_layout.addWidget(self.lbl_name)
        info_layout.addWidget(self.lbl_subtitle)
        layout.addLayout(info_layout, stretch=1)

        # Indicador de selección / check estilo Twitter
        self.lbl_badge = QLabel("✔" if is_active else "➔")
        self.lbl_badge.setObjectName("AccountCardBadge")
        self.lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_badge.setFixedSize(28, 28)
        layout.addWidget(self.lbl_badge)

        self._update_style()

    def _update_style(self):
        if self.is_active:
            self.setStyleSheet("""
                QFrame#AccountProfileCard {
                    background-color: rgba(247, 168, 184, 0.25);
                    border: 2px solid #f56b7b;
                    border-radius: 12px;
                }
                QFrame#AccountProfileCard:hover {
                    background-color: rgba(247, 168, 184, 0.35);
                }
                QLabel#AccountCardBadge {
                    color: #FFFFFF;
                    background-color: #f56b7b;
                    border-radius: 14px;
                    font-weight: bold;
                    font-size: 13px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#AccountProfileCard {
                    background-color: rgba(255, 255, 255, 0.7);
                    border: 1.5px solid rgba(242, 156, 164, 0.4);
                    border-radius: 12px;
                }
                QFrame#AccountProfileCard:hover {
                    background-color: rgba(255, 240, 243, 0.95);
                    border-color: #f7a8b8;
                }
                QLabel#AccountCardBadge {
                    color: #a85a7c;
                    background-color: transparent;
                    font-weight: bold;
                    font-size: 15px;
                }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.username)
        super().mousePressEvent(event)


class LoginWindow(QWidget):
    login_successful = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(t("Inicio de Sesión"))
        self.setObjectName("LoginBackground")

        self.session = SessionLocal()
        self.usuario_logueado = None
        self.selected_profile_user = None

        self._init_ui()
        language_manager.language_changed.connect(self.retranslate_ui)

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)

        # Tarjeta de Login moderna y espaciosa
        self.card = QFrame()
        self.card.setObjectName("LoginCard")
        self.card.setFixedSize(480, 480)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(28, 22, 28, 24)
        card_layout.setSpacing(12)

        # Header con Título
        self.label_header = QLabel(t("Bienvenido a PokeBinder"))
        self.label_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_header.setStyleSheet("font-size: 18px; font-weight: 800; color: #a85a7c;")
        card_layout.addWidget(self.label_header)

        self.label_sub = QLabel(t("Selecciona un perfil existente o entra con otra cuenta:"))
        self.label_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_sub.setStyleSheet("font-size: 12px; color: #7a4f61; font-weight: 500;")
        card_layout.addWidget(self.label_sub)

        # Lista deslizable de perfiles
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(180)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid rgba(242, 156, 164, 0.4);
                border-radius: 12px;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 6px;
                margin: 4px 0 4px 0;
            }
            QScrollBar::handle:vertical {
                background: #f7a8b8;
                min-height: 20px;
                border-radius: 3px;
            }
        """)

        self.profiles_container = QWidget()
        self.profiles_container.setStyleSheet("background: transparent;")
        self.profiles_layout = QVBoxLayout(self.profiles_container)
        self.profiles_layout.setContentsMargins(6, 6, 6, 6)
        self.profiles_layout.setSpacing(8)
        self.scroll_area.setWidget(self.profiles_container)

        card_layout.addWidget(self.scroll_area)

        # Separador / O ingresar otro usuario
        lbl_or = QLabel(f"— {t('o escribe tu nombre de usuario')} —")
        lbl_or.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_or.setStyleSheet("color: #999999; font-size: 11px; font-weight: 600;")
        card_layout.addWidget(lbl_or)

        # Input de usuario
        self.input_username = QLineEdit()
        self.input_username.setPlaceholderText(t("Nombre de usuario"))
        self.input_username.setFixedHeight(38)
        self.input_username.setObjectName("LoginInput")
        self.input_username.returnPressed.connect(self.handle_login)
        card_layout.addWidget(self.input_username)

        # Botón principal
        self.btn_login = QPushButton(t("Entrar / Crear usuario"))
        self.btn_login.setFixedHeight(42)
        self.btn_login.setObjectName("LoginBtn")
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.clicked.connect(self.handle_login)
        card_layout.addWidget(self.btn_login)

        main_layout.addWidget(self.card, 0, Qt.AlignmentFlag.AlignCenter)

        # Cargar perfiles desde la base de datos
        self.load_profiles()

    def load_profiles(self):
        """Lee todos los usuarios existentes en la base de datos y crea tarjetas de perfil."""
        # Limpiar contenedor previo
        while self.profiles_layout.count():
            item = self.profiles_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        users = self.session.query(Usuarios).order_by(Usuarios.nombre.asc()).all()

        if not users:
            no_users_lbl = QLabel(t("No hay cuentas creadas aún. ¡Crea una abajo!"))
            no_users_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_users_lbl.setStyleSheet("color: #888888; font-style: italic; padding: 20px;")
            self.profiles_layout.addWidget(no_users_lbl)
            self.scroll_area.setFixedHeight(100)
            return
        else:
            self.scroll_area.setFixedHeight(180)

        for u in users:
            is_active = (self.selected_profile_user == u.nombre)
            card = AccountProfileCard(u.nombre, u.avatar, is_active=is_active)
            card.selected.connect(self.on_profile_selected)
            self.profiles_layout.addWidget(card)

        self.profiles_layout.addStretch()

    def on_profile_selected(self, username: str):
        """Al hacer clic directo sobre el bloque de un perfil, se selecciona y se autocompleta el campo."""
        self.selected_profile_user = username
        self.input_username.setText(username)
        # Refrescar tarjetas visualmente para marcar el check en la seleccionada
        self.load_profiles()

    def retranslate_ui(self):
        self.setWindowTitle(t("Inicio de Sesión"))
        self.label_header.setText(t("Bienvenido a PokeBinder"))
        self.label_sub.setText(t("Selecciona un perfil existente o entra con otra cuenta:"))
        self.input_username.setPlaceholderText(t("Nombre de usuario"))
        self.btn_login.setText(t("Entrar / Crear usuario"))
        self.load_profiles()

    def mostrar_mensaje(self, titulo, mensaje, tipo="info"):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(titulo)
        msg_box.setText(mensaje)

        if tipo == "info":
            msg_box.setIcon(QMessageBox.Icon.Information)
        elif tipo == "warning":
            msg_box.setIcon(QMessageBox.Icon.Warning)
        elif tipo == "error":
            msg_box.setIcon(QMessageBox.Icon.Critical)

        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def handle_login(self):
        username = self.input_username.text().strip()

        if not username:
            self.mostrar_mensaje(t("Error"), t("Debes ingresar un nombre de usuario."), tipo="warning")
            return

        user = self.session.query(Usuarios).filter(Usuarios.nombre.ilike(username)).first()

        if user:
            # Si el usuario tiene contraseña configurada, pedirla
            if user.password_hash:
                import hashlib
                pwd, ok = self._prompt_password(username)
                if not ok:
                    return
                input_hash = hashlib.sha256(pwd.encode("utf-8")).hexdigest()
                if input_hash != user.password_hash:
                    self.mostrar_mensaje(t("Error"), t("Contraseña incorrecta."), tipo="error")
                    return
            self.mostrar_mensaje(t("Bienvenido"), f"{t('Bienvenido de nuevo')}, {user.nombre}!", tipo="info")
            username = user.nombre
        else:
            try:
                nuevo = Usuarios(nombre=username)
                self.session.add(nuevo)
                self.session.commit()
                self.mostrar_mensaje(t("Usuario creado"), f"{t('Usuario creado')}: '{username}'.", tipo="info")
            except Exception as e:
                self.session.rollback()
                self.mostrar_mensaje(t("Error"), f"{t('Error')}: {e}", tipo="error")
                return

        self.usuario_logueado = username
        self.login_successful.emit(username)

    def _prompt_password(self, username: str) -> tuple[str, bool]:
        """Solicita contraseña si el perfil la tiene configurada."""
        dlg = QDialog(self)
        dlg.setWindowTitle(t("Contraseña requerida"))
        dlg.setFixedSize(320, 160)
        dlg.setStyleSheet(self.card.styleSheet())

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        lbl = QLabel(f"{t('Introduce la contraseña para')} {username}:")
        lbl.setStyleSheet("font-weight: 600; color: #a85a7c;")
        txt = QLineEdit()
        txt.setEchoMode(QLineEdit.EchoMode.Password)
        txt.setFixedHeight(34)
        txt.setObjectName("LoginInput")

        btn_row = QHBoxLayout()
        btn_ok = QPushButton(t("Entrar"))
        btn_ok.setObjectName("LoginBtn")
        btn_ok.clicked.connect(dlg.accept)
        btn_cancel = QPushButton(t("Cancelar"))
        btn_cancel.clicked.connect(dlg.reject)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)

        layout.addWidget(lbl)
        layout.addWidget(txt)
        layout.addLayout(btn_row)

        txt.returnPressed.connect(dlg.accept)
        txt.setFocus()

        res = dlg.exec()
        return txt.text(), (res == QDialog.DialogCode.Accepted)

    def get_usuario(self):
        return self.usuario_logueado

    def closeEvent(self, event):
        if hasattr(self, 'session') and self.session:
            self.session.close()
        super().closeEvent(event)
