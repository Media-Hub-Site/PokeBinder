import sys
import os
from PyQt6.QtWidgets import QApplication, QWidget, QStackedWidget, QVBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QParallelAnimationGroup, pyqtProperty
from MyQtApp.ui.Login import LoginWindow
from MyQtApp.ui.Index import MainWindow
from MyQtApp.models import Base
from MyQtApp.session import engine
from MyQtApp.config import apply_global_style

class AppWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TCG Inventory Manager")
        
        # Obtener geometría centrada para la ventana de Login (520x520)
        self.setGeometry(self.get_centered_geometry(520, 520))
        self.setMinimumSize(520, 520)
        self.setMaximumSize(520, 520)
        
        self.setObjectName("MainBackground")

        # Layout principal
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Stack de páginas
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)

        # Añadir LoginWidget
        self.login_widget = LoginWindow()
        self.stack.addWidget(self.login_widget)

        # Conectar señal de login exitoso
        self.login_widget.login_successful.connect(self.on_login_successful)

        # Overlay de transición (Flash blanco)
        self.flash_overlay = QWidget(self)
        self.flash_overlay.setStyleSheet("background-color: white; border-radius: 20px;")
        self.flash_overlay.hide()

        # Efecto de opacidad para el flash
        self.flash_opacity = QGraphicsOpacityEffect(self.flash_overlay)
        self.flash_overlay.setGraphicsEffect(self.flash_opacity)

        # Ajustar geometría del flash inicialmente
        self.flash_overlay.setGeometry(self.rect())

    @pyqtProperty(float)
    def windowProgress(self):
        return getattr(self, "_window_progress", 0.0)

    @windowProgress.setter
    def windowProgress(self, val):
        self._window_progress = val
        w = int(self._start_w + (self._end_w - self._start_w) * val)
        h = int(self._start_h + (self._end_h - self._start_h) * val)
        
        # Centrar relativo a la pantalla donde se encuentra actualmente la ventana
        screen_obj = self.screen()
        if screen_obj is None:
            screen_obj = QApplication.primaryScreen()
        screen = screen_obj.availableGeometry()
        x = screen.x() + (screen.width() - w) // 2
        y = screen.y() + (screen.height() - h) // 2
        self.setGeometry(x, y, w, h)

    def get_centered_geometry(self, width, height):
        screen_obj = self.screen()
        if screen_obj is None:
            screen_obj = QApplication.primaryScreen()
        screen = screen_obj.availableGeometry()
        x = screen.x() + (screen.width() - width) // 2
        y = screen.y() + (screen.height() - height) // 2
        return QRect(x, y, width, height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.flash_overlay.setGeometry(self.rect())

    def on_login_successful(self, username):
        # Desbloquear límites de tamaño temporalmente para la animación
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)

        # Crear la ventana principal
        self.main_window = MainWindow(username)
        
        # Conectar el logout de MainWindow de vuelta al stack
        self.main_window.logout_requested.connect(self.on_logout_requested)
        
        self.stack.addWidget(self.main_window)

        # Ejecutar la transición de flash blanco con redimensionamiento animado a 1000x650
        self.ejecutar_transicion_flash(nuevo_indice=1, target_w=1000, target_h=650)

    def on_logout_requested(self):
        # Desbloquear límites de tamaño temporalmente para la animación
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)

        # Ejecutar transición de regreso al Login (índice 0) con redimensionamiento animado a 520x520
        self.ejecutar_transicion_flash(nuevo_indice=0, destruir_main=True, target_w=520, target_h=520)

    def ejecutar_transicion_flash(self, nuevo_indice, destruir_main=False, target_w=None, target_h=None):
        self.flash_overlay.show()
        self.flash_overlay.raise_()

        # Animación de Entrada (Fade in suave)
        self.anim_in = QPropertyAnimation(self.flash_opacity, b"opacity")
        self.anim_in.setDuration(200)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        self.anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Animación de Salida (Fade out suave)
        self.anim_out = QPropertyAnimation(self.flash_opacity, b"opacity")
        self.anim_out.setDuration(200)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Grupo paralelo para la entrada y cambio de tamaño
        grupo_in = QParallelAnimationGroup(self)
        grupo_in.addAnimation(self.anim_in)

        if target_w and target_h:
            self._start_w = self.width()
            self._start_h = self.height()
            self._end_w = target_w
            self._end_h = target_h
            
            self.anim_geom = QPropertyAnimation(self, b"windowProgress")
            self.anim_geom.setDuration(240)
            self.anim_geom.setStartValue(0.0)
            self.anim_geom.setEndValue(1.0)
            self.anim_geom.setEasingCurve(QEasingCurve.Type.OutCubic)
            grupo_in.addAnimation(self.anim_geom)

        # Conservar referencia para evitar recolección de basura
        self._trans_group = grupo_in

        def al_completar_in():
            self.stack.setCurrentIndex(nuevo_indice)
            if destruir_main:
                if self.stack.count() > 1:
                    widget_main = self.stack.widget(1)
                    self.stack.removeWidget(widget_main)
                    widget_main.deleteLater()
                self.main_window = None
                # Fijar tamaño del login
                self.setMinimumSize(520, 520)
                self.setMaximumSize(520, 520)
                if hasattr(self.login_widget, 'load_profiles'):
                    self.login_widget.load_profiles()
            else:
                # Establecer límites del main window
                self.setMinimumSize(950, 600)
                self.setMaximumSize(16777215, 16777215)
                
            self.anim_out.start()

        def al_completar_out():
            self.flash_overlay.hide()
            self._trans_group = None

        grupo_in.finished.connect(al_completar_in)
        self.anim_out.finished.connect(al_completar_out)
        
        grupo_in.start()


from MyQtApp.ui.toast import init_global_toast, install_global_exception_hook

def ensure_db_schema_up_to_date():
    import sqlite3
    from MyQtApp.config import DB_PATH
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(usuario_carta)")
            cols = [row[1] for row in cur.fetchall()]
            if "variante" not in cols:
                cur.execute("ALTER TABLE usuario_carta ADD COLUMN variante VARCHAR DEFAULT 'Normal'")
            if "idioma" not in cols:
                cur.execute("ALTER TABLE usuario_carta ADD COLUMN idioma VARCHAR DEFAULT 'es'")
            
            cur.execute("PRAGMA table_info(Cartas)")
            cols_cartas = [row[1] for row in cur.fetchall()]
            if "variantes_disponibles" not in cols_cartas:
                cur.execute("ALTER TABLE Cartas ADD COLUMN variantes_disponibles VARCHAR DEFAULT 'normal,reverse,holo'")
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error asegurando esquema DB: {e}")

def main():
    install_global_exception_hook()

    # Soporte para inyección de idioma desde Launcher (--lang=es/en) o variable de entorno
    lang_arg = os.environ.get("MEDIAHUB_APP_LANG", "")
    for arg in sys.argv[1:]:
        if arg.startswith("--lang="):
            lang_arg = arg.split("=", 1)[1].strip()
    
    if lang_arg:
        from MyQtApp.i18n import language_manager
        lang_map = {
            "es": "Español", "en": "English", "ja": "日本語", "fr": "Français", "pt": "Português"
        }
        chosen = lang_map.get(lang_arg.lower(), "Español")
        language_manager.set_language(chosen)

    app = QApplication(sys.argv)

    # Inicializar Base de datos
    Base.metadata.create_all(bind=engine)
    ensure_db_schema_up_to_date()

    # Generar respaldo de seguridad preventivo al iniciar
    try:
        from MyQtApp.app.backup import create_database_backup
        create_database_backup(tag="auto")
    except Exception as e:
        print(f"Error generando respaldo automático de inicio: {e}")

    # Cargar Estilos Globales
    apply_global_style(app)

    window = AppWindow()
    init_global_toast(window)
    window.show()
    sys.exit(app.exec())




if __name__ == "__main__":
    main()
