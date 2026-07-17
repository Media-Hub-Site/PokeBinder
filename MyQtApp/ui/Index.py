import random
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QMessageBox, QStackedWidget, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QUrl, QPropertyAnimation, QEasingCurve, QPoint, QByteArray, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtMultimedia import QSoundEffect, QMediaPlayer, QAudioOutput
import os

from MyQtApp.config import SOUNDS_DIR, IMAGES_DIR, ICONS_DIR, load_settings
from MyQtApp.app.db_services import agregar_cartas_usuario, eliminar_cartas_usuario

from .Galeria import GaleriaCartas
from .Inventario import GaleriaCartasInventario
from .Ajustes import AjustesWidget
from .Binder import BinderView

class BotonConSonido(QPushButton):
    def __init__(self, texto, parent=None):
        super().__init__(texto, parent)

        self.hover_sound = QSoundEffect()
        self.hover_sound.setSource(QUrl.fromLocalFile(os.path.join(SOUNDS_DIR, "hover.wav")))

        self.click_sound = QSoundEffect()
        self.click_sound.setSource(QUrl.fromLocalFile(os.path.join(SOUNDS_DIR, "click.wav")))

        self.setMouseTracking(True)

    def enterEvent(self, event):
        settings = load_settings()
        vol = (settings.get("volumen_sonido", 80) / 100.0) * 0.3
        self.hover_sound.setVolume(vol)
        self.hover_sound.play()
        super().enterEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            settings = load_settings()
            vol = (settings.get("volumen_sonido", 80) / 100.0) * 0.8
            self.click_sound.setVolume(vol)
            self.click_sound.play()
        super().mousePressEvent(event)


class MainWindow(QWidget):
    logout_requested = pyqtSignal()

    def __init__(self, usuario):
        super().__init__()
        self.settings = load_settings()
        self.animaciones_activas = self.settings.get("animaciones", True)
        self.usuario = usuario
        self.setObjectName("MainBackground")
        self.setWindowTitle(f"Menú Principal - Usuario: {usuario.capitalize()}")
        self.setGeometry(550, 250, 1000, 650)

        main_layout = QHBoxLayout(self)

        # Barra lateral
        nav_layout = QVBoxLayout()

        iconoBuscar = QIcon(os.path.join(ICONS_DIR, "buscar.png"))
        iconoCarpeta = QIcon(os.path.join(ICONS_DIR, "carpeta.png"))
        iconoColeccion = QIcon(os.path.join(ICONS_DIR, "coleccion.png"))

        self.btn_buscar = BotonConSonido(iconoBuscar, "Buscar")
        self.btn_ver_carpeta = BotonConSonido(iconoCarpeta, "Binder")
        self.btn_mi_coleccion = BotonConSonido(iconoColeccion, "Colección")

        botones_principales = [
            self.btn_buscar,
            self.btn_ver_carpeta,
            self.btn_mi_coleccion,
            BotonConSonido("⚙️ Ajustes"),
        ]

        for btn in botones_principales:
            btn.setFixedHeight(45)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("class", "NavButton")
            nav_layout.addWidget(btn)

        self.btn_ajustes = botones_principales[-1]

        nav_layout.addSpacing(30)

        self.btn_agregar = BotonConSonido("➕ Agregar")
        self.btn_eliminar = BotonConSonido("🗑️ Eliminar")
        self.btn_vaciar = BotonConSonido("⚠️ Vaciar")

        botones_secundarios_layout = QVBoxLayout()
        for btn in [self.btn_agregar, self.btn_eliminar, self.btn_vaciar]:
            btn.setFixedHeight(40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("class", "ActionSecondary")
            botones_secundarios_layout.addWidget(btn)
            botones_secundarios_layout.addSpacing(10)

        nav_layout.addLayout(botones_secundarios_layout)
        nav_layout.addStretch()

        self.btn_salir = BotonConSonido("🚪 Salir del programa")
        self.btn_salir.setFixedHeight(50)
        self.btn_salir.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_salir.setProperty("class", "ExitButton")
        nav_layout.addWidget(self.btn_salir)
        nav_layout.addSpacing(20)

        # Panel lateral
        side_widget = QWidget()
        side_layout_wrapper = QVBoxLayout(side_widget)
        side_layout_wrapper.setContentsMargins(12, 12, 12, 12)
        side_widget.setObjectName('side')
        side_layout_wrapper.addLayout(nav_layout)
        side_layout_wrapper.addStretch()

        main_layout.addWidget(side_widget, 1)

        # Páginas con transición
        self.paginas = QStackedWidget()
        self.paginas.addWidget(GaleriaCartas(IMAGES_DIR))       # índice 0
        self.paginas.addWidget(BinderView(self.usuario))           # índice 1
        self.paginas.addWidget(GaleriaCartasInventario(IMAGES_DIR, self.usuario))  # índice 2
        self.paginas.addWidget(AjustesWidget())  # índice 3

        # Área principal
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(14, 14, 14, 14)
        content_layout.setSpacing(8)
        content_widget.setObjectName('content')

        content_layout.addWidget(self.paginas)

        # Pie inferior
        bottom_bar = QWidget()
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(6, 6, 6, 6)
        bottom_layout.setSpacing(8)
        bottom_layout.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        view_buttons = QWidget()
        vb_layout = QHBoxLayout(view_buttons)
        vb_layout.setContentsMargins(0, 0, 0, 0)
        vb_layout.setSpacing(8)

        self.btn_view_grid = QPushButton("▦")
        self.btn_view_grid.setFixedSize(48, 48)
        self.btn_view_grid.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_view_grid.setToolTip("Vista en imágenes")
        self.btn_view_grid.setProperty("class", "ViewGrid")

        self.btn_view_list = QPushButton("≡")
        self.btn_view_list.setFixedSize(48, 48)
        self.btn_view_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_view_list.setToolTip("Vista en lista")
        self.btn_view_list.setProperty("class", "ViewList")

        vb_layout.addWidget(self.btn_view_grid)
        vb_layout.addWidget(self.btn_view_list)

        bottom_layout.addWidget(view_buttons, 0, Qt.AlignmentFlag.AlignRight)
        content_layout.addWidget(bottom_bar)

        main_layout.addWidget(content_widget, 4)

        # Conexiones
        self.btn_buscar.clicked.connect(lambda: self.animar_transicion(0))
        self.btn_ver_carpeta.clicked.connect(lambda: self.animar_transicion(1))
        self.btn_mi_coleccion.clicked.connect(lambda: self.animar_transicion(2))
        self.btn_ajustes.clicked.connect(lambda: self.animar_transicion(3))
        self.btn_salir.clicked.connect(self.confirmar_salir)
        self.btn_agregar.clicked.connect(self.agregar_cartas)
        self.btn_eliminar.clicked.connect(self.eliminar_cartas)
        self.btn_vaciar.clicked.connect(self.vaciar_binder)

        ajustes = self.paginas.widget(3)
        ajustes.music_volume_changed.connect(self.actualizar_volumen_musica)
        ajustes.music_track_changed.connect(self.cambiar_musica)
        ajustes.animations_toggled.connect(self.toggle_animaciones)
        ajustes.card_size_changed.connect(self.actualizar_tamano_cartas)
        if hasattr(ajustes, 'logout_requested'):
            ajustes.logout_requested.connect(self.cambiar_cuenta)

        self.actualizar_botones_secundarios(0)

        # Configurar audio
        pista = self.settings.get("pista_musica", 1)
        musica = f"musica_fondo_{pista}.mp3"
        ruta_musica = os.path.join(SOUNDS_DIR, musica)

        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)
        self.player.setSource(QUrl.fromLocalFile(ruta_musica))
        self.player.setLoops(QMediaPlayer.Loops.Infinite)
        vol = self.settings.get("volumen_musica", 20) / 100.0
        self.audio_output.setVolume(vol)
        self.player.play()

    def actualizar_volumen_musica(self, valor):
        self.audio_output.setVolume(valor / 100.0)

    def cambiar_musica(self, pista):
        musica = f"musica_fondo_{pista}.mp3"
        ruta_musica = os.path.join(SOUNDS_DIR, musica)
        was_playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        self.player.setSource(QUrl.fromLocalFile(ruta_musica))
        if was_playing:
            self.player.play()

    def toggle_animaciones(self, estado):
        self.animaciones_activas = estado

    def actualizar_tamano_cartas(self, size):
        try:
            galeria = self.paginas.widget(0)
            if hasattr(galeria, 'actualizar_galeria'):
                galeria.actualizar_galeria()
        except Exception as e:
            print(f"Error actualizando galeria: {e}")
        try:
            inventario = self.paginas.widget(2)
            if hasattr(inventario, 'actualizar_galeria'):
                inventario.actualizar_galeria()
        except Exception as e:
            print(f"Error actualizando inventario: {e}")

    def animar_transicion(self, nuevo_indice):
        indice_actual = self.paginas.currentIndex()
        if nuevo_indice == indice_actual:
            return

        widget_actual = self.paginas.currentWidget()
        widget_nuevo = self.paginas.widget(nuevo_indice)

        if not self.animaciones_activas:
            # Sin animación: cambiar de página al instante
            self.paginas.setCurrentIndex(nuevo_indice)
            widget_nuevo.move(0, 0)
            widget_actual.hide()
            widget_nuevo.show()
            self.actualizar_botones_secundarios(nuevo_indice)
            return

        direccion = 1 if nuevo_indice > indice_actual else -1

        widget_nuevo.move(direccion * self.paginas.width(), 0)
        widget_nuevo.show()

        anim_nuevo = QPropertyAnimation(widget_nuevo, b"pos", self)
        anim_nuevo.setDuration(400)
        anim_nuevo.setStartValue(widget_nuevo.pos())
        anim_nuevo.setEndValue(QPoint(0, 0))
        anim_nuevo.setEasingCurve(QEasingCurve.Type.InOutCubic)

        anim_actual = QPropertyAnimation(widget_actual, b"pos", self)
        anim_actual.setDuration(400)
        anim_actual.setStartValue(widget_actual.pos())
        anim_actual.setEndValue(QPoint(-direccion * self.paginas.width(), 0))
        anim_actual.setEasingCurve(QEasingCurve.Type.InOutCubic)

        # Guardar referencias para evitar recolección de basura
        self._current_animations = [anim_nuevo, anim_actual]

        def on_finish():
            self.paginas.setCurrentIndex(nuevo_indice)
            widget_actual.hide()
            self.actualizar_botones_secundarios(nuevo_indice)
            self._current_animations = []
        anim_nuevo.finished.connect(on_finish)

        anim_nuevo.start()
        anim_actual.start()

    def cambiar_cuenta(self):
        if hasattr(self, 'player') and self.player:
            self.player.stop()
        self.logout_requested.emit()

    def closeEvent(self, event):
        if hasattr(self, 'player') and self.player:
            self.player.stop()
        top_level = self.window()
        if top_level and top_level != self:
            top_level.close()
        super().closeEvent(event)

    def actualizar_botones_secundarios(self, indice):
        try:
            self.btn_agregar.setVisible(indice == 0)
            self.btn_eliminar.setVisible(indice == 2)
            self.btn_vaciar.setVisible(indice == 1)
        except Exception as e:
            print(f"Error en actualizar_botones_secundarios: {e}")

        if indice == 1:
            try:
                binder = self.paginas.widget(1)
                if hasattr(binder, 'refresh_inventory'):
                    binder.refresh_inventory()
            except Exception as e:
                print(f"Error actualizando binder: {e}")

        if indice == 2:
            try:
                inventario = self.paginas.widget(2)
                if hasattr(inventario, 'reset_page_and_actualizar'):
                    inventario.reset_page_and_actualizar()
                else:
                    if hasattr(inventario, 'actualizar_total_cartas'):
                        inventario.actualizar_total_cartas()
                    if hasattr(inventario, 'actualizar_galeria'):
                        inventario.actualizar_galeria()
            except Exception as e:
                print(f"Error actualizando inventario: {e}")

    def confirmar_salir(self):
        self.mostrar_mensaje("¿Seguro que quieres salir del programa?",
                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                             cerrar=True)

    def agregar_cartas(self):
        galeria_busqueda = self.paginas.widget(0)
        cartas_seleccionadas = galeria_busqueda.get_cartas_seleccionadas()

        if not cartas_seleccionadas:
            self.mostrar_mensaje("Selecciona al menos una carta para agregar.")
            return

        cartas_ids = [carta["id_api"] for carta in cartas_seleccionadas]
        exitos = agregar_cartas_usuario(self.usuario, cartas_ids)

        if exitos:
            self.mostrar_mensaje(f"✔️ Se han agregado {exitos} carta(s) a tu colección.")
            try:
                inventario = self.paginas.widget(2)
                if hasattr(inventario, 'reset_page_and_actualizar'):
                    inventario.reset_page_and_actualizar()
                else:
                    if hasattr(inventario, 'actualizar_total_cartas'):
                        inventario.actualizar_total_cartas()
                    if hasattr(inventario, 'actualizar_galeria'):
                        inventario.actualizar_galeria()
            except Exception as e:
                print(f"Error al refrescar inventario tras agregar: {e}")
        else:
            self.mostrar_mensaje("❗Las cartas seleccionadas ya están en tu colección o hubo un error.")

    def mostrar_mensaje(self, texto, botones=QMessageBox.StandardButton.Ok, cerrar=False):
        mensaje = QMessageBox(self)
        mensaje.setWindowTitle("Confirmación" if cerrar else "Información")
        mensaje.setText(texto)
        mensaje.setStandardButtons(botones)
        mensaje.setDefaultButton(QMessageBox.StandardButton.Ok)

        resultado = mensaje.exec()
        if cerrar and resultado == QMessageBox.StandardButton.Yes:
            self.close()

    def eliminar_cartas(self):
        try:
            inventario = self.paginas.widget(2)
        except Exception as e:
            print(f"Error accediendo a widget de inventario: {e}")
            inventario = None

        if inventario is None:
            self.mostrar_mensaje("No se pudo acceder al inventario.")
            return

        try:
            cartas = inventario.get_cartas_seleccionadas()
        except Exception as e:
            print(f"Error obteniendo cartas de inventario: {e}")
            cartas = []

        if not cartas:
            self.mostrar_mensaje("Selecciona al menos una carta de tu inventario para eliminar.")
            return

        nombres = [c.get('nombre', c.get('id_api')) if isinstance(c, dict) else str(c) for c in cartas]
        texto = f"¿Seguro que quieres eliminar {len(nombres)} carta(s) de tu inventario?\n\n"
        texto += ", ".join(nombres[:6])
        if len(nombres) > 6:
            texto += ", ..."

        resp = QMessageBox.question(self, "Confirmar eliminación", texto,
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp != QMessageBox.StandardButton.Yes:
            return

        cartas_ids = [c.get('id_api') if isinstance(c, dict) else c for c in cartas]
        cartas_ids = [cid for cid in cartas_ids if cid]
        
        eliminados = eliminar_cartas_usuario(self.usuario, cartas_ids)

        if eliminados:
            self.mostrar_mensaje(f"✔️ Se han eliminado {eliminados} carta(s) de tu inventario.")
        else:
            self.mostrar_mensaje("❗No se eliminaron cartas (posiblemente ya no existían en la tabla o hubo error).")

        try:
            if hasattr(inventario, 'reset_page_and_actualizar'):
                inventario.reset_page_and_actualizar()
            else:
                if hasattr(inventario, 'actualizar_total_cartas'):
                    inventario.actualizar_total_cartas()
                if hasattr(inventario, 'actualizar_galeria'):
                    inventario.actualizar_galeria()
        except Exception as e:
            print(f"Error refrescando inventario tras eliminar: {e}")

    def vaciar_binder(self):
        resp = QMessageBox.question(self, "Vaciar Carpeta", "¿Estás seguro de que quieres quitar todas las cartas de la carpeta?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.Yes:
            try:
                binder = self.paginas.widget(1)
                binder.clear_binder()
                self.mostrar_mensaje("✔️ Carpeta vaciada correctamente.")
            except Exception as e:
                print(f"Error vaciando binder: {e}")
                self.mostrar_mensaje("Error al vaciar la carpeta.")
