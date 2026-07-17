from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal

from ..session import SessionLocal
from ..models import Usuarios


class LoginWindow(QWidget):
    login_successful = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inicio de Sesión")
        self.setObjectName("LoginBackground")

        self.session = SessionLocal()

        # Layout principal para centrar la tarjeta de login
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Crear tarjeta central de Login (LoginCard)
        card = QFrame()
        card.setObjectName("LoginCard")
        card.setFixedSize(380, 260)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(18)

        self.label = QLabel("Ingresa tu nombre de usuario:")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 16px; font-weight: 600; color: #a85a7c;")

        self.input_username = QLineEdit()
        self.input_username.setPlaceholderText("Nombre de usuario")
        self.input_username.setFixedHeight(38)
        self.input_username.setObjectName("LoginInput")

        self.btn_login = QPushButton("Entrar / Crear usuario")
        self.btn_login.setFixedHeight(42)
        self.btn_login.setObjectName("LoginBtn")
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.clicked.connect(self.handle_login)

        card_layout.addWidget(self.label)
        card_layout.addWidget(self.input_username)
        card_layout.addWidget(self.btn_login)

        main_layout.addWidget(card, 0, Qt.AlignmentFlag.AlignCenter)

        self.usuario_logueado = None

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
            self.mostrar_mensaje("Error", "Debes ingresar un nombre de usuario.", tipo="warning")
            return

        user = self.session.query(Usuarios).filter(Usuarios.nombre.ilike(username)).first()

        if user:
            self.mostrar_mensaje("Bienvenido", f"Bienvenido de nuevo, {username}!", tipo="info")
        else:
            try:
                nuevo = Usuarios(nombre=username)
                self.session.add(nuevo)
                self.session.commit()
                self.mostrar_mensaje("Usuario creado", f"Usuario '{username}' creado correctamente.", tipo="info")
            except Exception as e:
                self.session.rollback()
                self.mostrar_mensaje("Error", f"No se pudo crear usuario: {e}", tipo="error")
                return

        self.usuario_logueado = username
        self.login_successful.emit(username)


    def get_usuario(self):
        return self.usuario_logueado

    def closeEvent(self, event):
        if hasattr(self, 'session') and self.session:
            self.session.close()
        super().closeEvent(event)
