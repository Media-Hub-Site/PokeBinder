import sys
import traceback
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QApplication, QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QObject, QPoint

class ToastSignalEmitter(QObject):
    show_toast_signal = pyqtSignal(str, str, int)

# Instancia global del emisor de señales para hilos secundarios
toast_emitter = ToastSignalEmitter()

class ToastNotificationWidget(QWidget):
    """Burbuja flotante de notificación estilo Toast moderna con glassmorphism y animación."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.SubWindow | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(16, 10, 16, 10)
        self.layout.setSpacing(10)
        
        self.lbl_icon = QLabel("💡", self)
        self.lbl_icon.setStyleSheet("font-size: 16px; background: transparent;")
        self.layout.addWidget(self.lbl_icon)
        
        self.lbl_text = QLabel("", self)
        self.lbl_text.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_text.setStyleSheet("color: #f8fafc; background: transparent;")
        self.lbl_text.setWordWrap(True)
        self.layout.addWidget(self.lbl_text)
        
        # Sombra proyectada suave
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide_toast)
        
        self.hide()

    def show_toast(self, message: str, toast_type: str = "info", duration_ms: int = 2500):
        try:
            self._hide_timer.stop()
            
            # Iconos y estilos según tipo
            if toast_type == "wait" or toast_type == "warning":
                icon = "⏳"
                bg_color = "rgba(234, 179, 8, 0.92)"     # Ámbar suave
                border_color = "rgba(254, 240, 138, 0.6)"
            elif toast_type == "error":
                icon = "⚠️"
                bg_color = "rgba(239, 68, 68, 0.92)"      # Rojo suave
                border_color = "rgba(254, 202, 202, 0.6)"
            elif toast_type == "success":
                icon = "✅"
                bg_color = "rgba(34, 197, 94, 0.92)"      # Verde suave
                border_color = "rgba(187, 247, 208, 0.6)"
            else:
                icon = "💡"
                bg_color = "rgba(14, 165, 233, 0.92)"     # Azul brillante
                border_color = "rgba(186, 230, 253, 0.6)"

            self.lbl_icon.setText(icon)
            self.lbl_text.setText(message)
            
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {bg_color};
                    border: 1.5px solid {border_color};
                    border-radius: 16px;
                }}
            """)
            
            self.adjustSize()
            
            # Posicionar centrado abajo relativo al parent (o pantalla principal)
            parent_win = self.parentWidget() or QApplication.activeWindow()
            if parent_win and parent_win.isVisible():
                p_rect = parent_win.rect()
                w = max(self.width(), 260)
                h = self.height()
                cx = (p_rect.width() - w) // 2
                cy = p_rect.height() - h - 30
                self.setGeometry(cx, cy, w, h)
            
            self.show()
            self.raise_()
            
            self._hide_timer.start(duration_ms)
        except Exception as e:
            print(f"Error mostrando Toast: {e}")

    def hide_toast(self):
        try:
            self.hide()
        except Exception:
            pass


_global_toast_widget = None

def init_global_toast(parent_window):
    global _global_toast_widget
    _global_toast_widget = ToastNotificationWidget(parent_window)
    toast_emitter.show_toast_signal.connect(_on_show_toast_signal)

def _on_show_toast_signal(message, toast_type, duration_ms):
    if _global_toast_widget:
        _global_toast_widget.show_toast(message, toast_type, duration_ms)

def show_toast(message: str, toast_type: str = "info", duration_ms: int = 2500):
    """Función global thread-safe para invocar notificaciones flotantes en cualquier lugar de la app."""
    try:
        toast_emitter.show_toast_signal.emit(message, toast_type, duration_ms)
    except Exception as e:
        print(f"[Toast] {message} ({e})")


def install_global_exception_hook():
    """Hook global de excepciones para prevenir que la aplicación falle o se cierre de golpe."""
    def custom_excepthook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print("⚠️ Excepción no capturada interceptada globalmente:\n", err_msg)
        
        # Mostrar notificación flotante amigable al usuario
        if issubclass(exc_type, AttributeError) or issubclass(exc_type, KeyError):
            show_toast("Por favor, espera un segundo... procesando acción", "wait", 2200)
        else:
            show_toast("Acción rápida detectada. Por favor espera un momento", "wait", 2500)

    sys.excepthook = custom_excepthook
