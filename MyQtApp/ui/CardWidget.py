import os
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QToolTip
)
from PyQt6.QtGui import QPixmap, QCursor, QColor, QPainter, QPainterPath, QTransform, QRadialGradient, QLinearGradient, QPen, QBrush
from PyQt6.QtCore import (
    Qt, pyqtSignal, QPropertyAnimation, QParallelAnimationGroup,
    QPoint, QRect, QRectF, QEasingCurve, QTimer, QDateTime, pyqtProperty
)
from MyQtApp.config import ICONS_DIR, IMAGES_DIR, EXE_DIR, VARIANT_COLOR_MAP, normalize_lang_code
from MyQtApp.i18n import t, language_manager
from MyQtApp.app.getImgs import get_pixmap_from_zip, get_webp_pixmap, get_hd_pixmap, HDImageDownloaderThread
from MyQtApp.session import SessionLocal
from MyQtApp.models import Cartas


class LanguageBadgeLabel(QLabel):
    """Etiqueta distintiva con el idioma de la carta (ej. ES, EN, JA, FR, PT, ZH)."""
    def __init__(self, idioma="es", parent=None):
        super().__init__(parent)
        lang_code = normalize_lang_code(idioma).upper()
        flag_map = {
            "ES": "🇪🇸 ES",
            "EN": "🇬🇧 EN",
            "JA": "🇯🇵 JA",
            "FR": "🇫🇷 FR",
            "PT": "🇵🇹 PT",
            "ZH": "🇨🇳 ZH"
        }
        display_text = flag_map.get(lang_code, f"🌐 {lang_code}")
        self.setText(display_text)
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(15, 23, 42, 0.88);
                color: #f8fafc;
                font-weight: bold;
                font-size: 10px;
                border: 1px solid rgba(56, 189, 248, 0.6);
                border-radius: 4px;
                padding: 1px 5px;
            }
        """)
        self.adjustSize()


class VariantBadgeButton(QPushButton):

    """Boton/Badge rectangular vertical distintivo para cambiar o mostrar la variante de la carta."""
    variant_changed = pyqtSignal(str, str)  # (id_api, nueva_variante)

    def __init__(self, id_api, variante_actual="Normal", parent=None):
        super().__init__(parent)
        self.id_api = id_api
        self.variante_actual = variante_actual or "Normal"
        self.setFixedSize(14, 38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_appearance()
        self.clicked.connect(self.cycle_variant)

    def update_appearance(self):
        info = VARIANT_COLOR_MAP.get(self.variante_actual, VARIANT_COLOR_MAP["Normal"])
        color = info["color"]
        border = info["border"]
        name = info["name"]
        self.setToolTip(f"Variante: {name}\n(Haz clic para cambiar variante)")
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: 1.5px solid {border};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #ffffff;
            }}
        """)

    def set_variante(self, variante: str):
        self.variante_actual = variante or "Normal"
        self.update_appearance()

    def cycle_variant(self):
        variantes = list(VARIANT_COLOR_MAP.keys())
        idx = variantes.index(self.variante_actual) if self.variante_actual in variantes else 4
        proxima = variantes[(idx + 1) % len(variantes)]
        self.variante_actual = proxima
        self.update_appearance()
        self.variant_changed.emit(self.id_api, proxima)


class VariantLegendBar(QWidget):
    """Barra horizontal explicativa de la leyenda de colores de variaciones."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(14)

        lbl_title = QLabel("🎨 Leyenda de Variantes:", self)
        lbl_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #38bdf8;")
        layout.addWidget(lbl_title)

        for key, info in VARIANT_COLOR_MAP.items():
            item_widget = QWidget(self)
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(5)

            badge = QLabel(self)
            badge.setFixedSize(10, 18)
            badge.setStyleSheet(f"background-color: {info['color']}; border: 1px solid {info['border']}; border-radius: 3px;")
            
            txt = QLabel(f"{info['name']}", self)
            txt.setStyleSheet("font-size: 11px; color: #f8fafc; font-weight: 500;")

            item_layout.addWidget(badge)
            item_layout.addWidget(txt)
            layout.addWidget(item_widget)

        layout.addStretch()
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(15, 23, 42, 0.75);
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 10px;
            }
        """)


class CardItemWidget(QWidget):
    def __init__(self, carta, pixmap, size, variante="Normal", parent=None):
        super().__init__(parent)
        self.carta = carta
        self.id_api = getattr(carta, 'id_api', None)
        self.idioma = getattr(carta, 'idioma', None) or language_manager.current_language
        self.setFixedSize(size[0], size[1])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.image_label = ClickableLabel(self.id_api, self)
        self.image_label.setScaledContents(True)
        self.image_label.setPixmap(pixmap)
        self.image_label.setFixedSize(size[0], size[1])
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)

        # Botón rectangular vertical de variante (arriba a la izquierda)
        self.variant_badge = VariantBadgeButton(self.id_api, variante, self)
        self.variant_badge.move(3, 3)
        self.variant_badge.raise_()

        # Botón de información (arriba a la derecha)
        self.info_btn = InfoIconLabel(carta, self)
        self.info_btn.move(size[0] - 26, 3)
        self.info_btn.raise_()

        # Insignia distintiva de idioma (abajo a la izquierda)
        self.lang_badge = LanguageBadgeLabel(self.idioma, self)
        badge_h = self.lang_badge.height()
        self.lang_badge.move(3, size[1] - badge_h - 3)
        self.lang_badge.raise_()



class InteractiveCard3DWidget(QWidget):
    """Widget de carta 3D física con canto de grosor, brillo espectral prismático y física de inercia."""

    def __init__(self, parent=None):

        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")

        self._front_pixmap = QPixmap()
        self._back_pixmap = QPixmap()
        self._load_back_pixmap()

        self._rot_x = 0.0
        self._rot_y = 0.0
        self._target_rot_x = 0.0
        self._target_rot_y = 0.0
        self._flip_angle = 0.0

        self._card_w = 340
        self._card_h = 476
        self._is_dragging = False

        # Temporizador a 60 FPS para suavizado de inercia y física de masa
        self._physics_timer = QTimer(self)
        self._physics_timer.setInterval(16)
        self._physics_timer.timeout.connect(self._update_physics)
        self._physics_timer.start()

    def _load_back_pixmap(self):
        candidate_paths = [
            os.path.join(ICONS_DIR, "carta.jpg"),
            os.path.join(ICONS_DIR, "carta.png"),
            os.path.join(EXE_DIR, "assets", "card_back.png"),
        ]
        for path in candidate_paths:
            if os.path.exists(path):
                pix = QPixmap(path)
                if not pix.isNull():
                    self._back_pixmap = pix
                    return

    def set_card_size(self, w: int, h: int):
        self._card_w = w
        self._card_h = h
        padding = 80
        self.setFixedSize(w + padding * 2, h + padding * 2)
        self.update()

    @pyqtProperty(float)
    def flipAngle(self):
        return self._flip_angle

    @flipAngle.setter
    def flipAngle(self, val):
        self._flip_angle = float(val)
        self.update()

    def set_front_pixmap(self, pixmap: QPixmap):
        self._front_pixmap = pixmap
        self.update()

    def flip_card(self):
        target = 180.0 if self._flip_angle < 90.0 else 0.0
        self.anim_flip = QPropertyAnimation(self, b"flipAngle", self)
        self.anim_flip.setDuration(600)
        self.anim_flip.setStartValue(self._flip_angle)
        self.anim_flip.setEndValue(target)
        self.anim_flip.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim_flip.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._update_tilt_target(event.pos())

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            self._update_tilt_target(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self._target_rot_x = 0.0
            self._target_rot_y = 0.0

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.flip_card()

    def _update_tilt_target(self, pos: QPoint):
        w = max(1, self.width())
        h = max(1, self.height())

        nx = max(-1.0, min(1.0, (pos.x() - w / 2.0) / (w / 2.0)))
        ny = max(-1.0, min(1.0, (pos.y() - h / 2.0) / (h / 2.0)))

        self._target_rot_y = nx * 34.0
        self._target_rot_x = -ny * 34.0

    def _update_physics(self):
        diff_x = self._target_rot_x - self._rot_x
        diff_y = self._target_rot_y - self._rot_y

        if abs(diff_x) > 0.01 or abs(diff_y) > 0.01:
            self._rot_x += diff_x * 0.20
            self._rot_y += diff_y * 0.20
            self.update()
        elif self._rot_x != self._target_rot_x or self._rot_y != self._target_rot_y:
            self._rot_x = self._target_rot_x
            self._rot_y = self._target_rot_y
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        current_flip = self._flip_angle % 360
        is_back = (90.0 <= current_flip <= 270.0)

        pix = self._back_pixmap if is_back else self._front_pixmap
        if not pix or pix.isNull():
            return

        w = float(self.width())
        h = float(self.height())
        cw = float(self._card_w)
        ch = float(self._card_h)
        cx = (w - cw) / 2.0
        cy = (h - ch) / 2.0

        effective_flip = current_flip if not is_back else (current_flip - 180.0)

        # 1. SOMBRA PROYECTADA DINÁMICA (Sin bordes duros)
        shadow_dx = -self._rot_y * 0.75 + 10.0
        shadow_dy = self._rot_x * 0.75 + 16.0

        shadow_transform = QTransform()
        shadow_transform.translate(w / 2.0 + shadow_dx, h / 2.0 + shadow_dy)
        shadow_transform.rotate((self._rot_y + effective_flip) * 0.9, Qt.Axis.YAxis)
        shadow_transform.rotate(self._rot_x * 0.9, Qt.Axis.XAxis)
        shadow_transform.setMatrix(
            shadow_transform.m11(), shadow_transform.m12(), shadow_transform.m13(),
            shadow_transform.m21(), shadow_transform.m22(), shadow_transform.m23(),
            shadow_transform.m31(), shadow_transform.m32(), shadow_transform.m33() - 0.0012
        )
        shadow_transform.translate(-w / 2.0, -h / 2.0)

        painter.setTransform(shadow_transform)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 150))
        painter.drawRoundedRect(QRectF(cx, cy, cw, ch), 16, 16)

        # 2. CANTO FÍSICO 3D (Grosor lateral de cartón)
        thickness = 5.0
        for i in range(int(thickness), 0, -1):
            edge_dx = (self._rot_y / 34.0) * i * 0.85
            edge_dy = (-self._rot_x / 34.0) * i * 0.85

            edge_transform = QTransform()
            edge_transform.translate(w / 2.0 + edge_dx, h / 2.0 + edge_dy)
            edge_transform.rotate(self._rot_y + effective_flip, Qt.Axis.YAxis)
            edge_transform.rotate(self._rot_x, Qt.Axis.XAxis)
            edge_transform.setMatrix(
                edge_transform.m11(), edge_transform.m12(), edge_transform.m13(),
                edge_transform.m21(), edge_transform.m22(), edge_transform.m23(),
                edge_transform.m31(), edge_transform.m32(), edge_transform.m33() - 0.0012
            )
            edge_transform.translate(-w / 2.0, -h / 2.0)

            painter.setTransform(edge_transform)
            edge_color = QColor(230, 235, 245) if not is_back else QColor(35, 25, 55)
            painter.setBrush(edge_color)
            painter.setPen(QPen(QColor(15, 23, 42, 140), 1))
            painter.drawRoundedRect(QRectF(cx, cy, cw, ch), 16, 16)

        # 3. CARTA 3D PRINCIPAL CON RECORTE REDONDEADO PERFECTO
        card_transform = QTransform()
        card_transform.translate(w / 2.0, h / 2.0)
        card_transform.rotate(self._rot_y + effective_flip, Qt.Axis.YAxis)
        card_transform.rotate(self._rot_x, Qt.Axis.XAxis)
        card_transform.setMatrix(
            card_transform.m11(), card_transform.m12(), card_transform.m13(),
            card_transform.m21(), card_transform.m22(), card_transform.m23(),
            card_transform.m31(), card_transform.m32(), card_transform.m33() - 0.0012
        )
        card_transform.translate(-w / 2.0, -h / 2.0)

        painter.setTransform(card_transform)

        # Path de esquinas redondeadas impecable
        clip_path = QPainterPath()
        clip_path.addRoundedRect(QRectF(cx, cy, cw, ch), 14, 14)

        painter.save()
        painter.setClipPath(clip_path)
        scaled_pix = pix.scaled(int(cw), int(ch), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        painter.drawPixmap(int(cx), int(cy), scaled_pix)
        painter.restore()

        # Borde exterior blanco fino alrededor de la carta
        border_pen = QPen(QColor(255, 255, 255, 180), 2)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(cx, cy, cw, ch), 14, 14)

        # 4. CAPA HOLOGRÁFICA PRISMÁTICA (FOIL RAINBOW & SPECULAR GLARE)
        if not is_back:
            tilt_magnitude = (abs(self._rot_x) + abs(self._rot_y)) / 48.0
            tilt_magnitude = min(1.0, tilt_magnitude)

            # Destello radial
            glare_x = cx + (0.5 + (self._rot_y / 70.0)) * cw
            glare_y = cy + (0.5 - (self._rot_x / 70.0)) * ch

            glare_grad = QRadialGradient(glare_x, glare_y, max(cw, ch) * 0.75)
            glare_grad.setColorAt(0.0, QColor(255, 255, 255, int(140 * tilt_magnitude + 30)))
            glare_grad.setColorAt(0.45, QColor(255, 255, 255, int(45 * tilt_magnitude)))
            glare_grad.setColorAt(1.0, QColor(255, 255, 255, 0))

            painter.save()
            painter.setClipPath(clip_path)
            painter.setBrush(glare_grad)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(cx, cy, cw, ch), 14, 14)

            # Arcoíris holográfico
            if tilt_magnitude > 0.05:
                rainbow_grad = QLinearGradient(cx, cy, cx + cw, cy + ch)
                alpha = int(80 * tilt_magnitude)
                rainbow_grad.setColorAt(0.0, QColor(236, 72, 153, alpha))
                rainbow_grad.setColorAt(0.25, QColor(56, 189, 248, alpha))
                rainbow_grad.setColorAt(0.5, QColor(74, 222, 128, alpha))
                rainbow_grad.setColorAt(0.75, QColor(250, 204, 21, alpha))
                rainbow_grad.setColorAt(1.0, QColor(244, 114, 182, alpha))

                painter.setBrush(rainbow_grad)
                painter.drawRoundedRect(QRectF(cx, cy, cw, ch), 14, 14)

            painter.restore()


class CardZoomOverlay(QWidget):
    """Overlay de pantalla completa con manipulación interactiva 3D."""
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.setObjectName("CardZoomOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setGeometry(parent_window.rect())

        self._bg_alpha = 0
        self.setStyleSheet("QWidget#CardZoomOverlay { background-color: rgba(8, 12, 20, 0); }")

        # Contenedor interactivo 3D de la carta (Totalmente transparente sin recuadros negros)
        self.card_3d = InteractiveCard3DWidget(self)

        # Barra de botones de control flotantes
        self.controls_widget = QWidget(self)
        self.controls_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(15, 23, 42, 220);
                border: 1.5px solid rgba(255, 255, 255, 0.2);
                border-radius: 20px;
            }
            QPushButton {
                background-color: rgba(30, 41, 59, 230);
                color: #f8fafc;
                font-weight: bold;
                font-size: 13px;
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 12px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #0284c7;
                border-color: #38bdf8;
            }
            QLabel {
                color: #94a3b8;
                font-size: 12px;
            }
        """)
        controls_layout = QHBoxLayout(self.controls_widget)
        controls_layout.setContentsMargins(12, 6, 12, 6)
        controls_layout.setSpacing(12)

        self.btn_flip = QPushButton("🔄 Voltear Carta", self.controls_widget)
        self.btn_flip.clicked.connect(self.card_3d.flip_card)
        controls_layout.addWidget(self.btn_flip)

        self.hint_label = QLabel("💡 Arrastra la carta para inclinar en 3D • Doble clic para voltear", self.controls_widget)
        controls_layout.addWidget(self.hint_label)

        self.btn_close = QPushButton("❌ Cerrar", self.controls_widget)
        self.btn_close.clicked.connect(self.close_zoom)
        controls_layout.addWidget(self.btn_close)

        self.controls_widget.adjustSize()

        # Cartel de estado de carga HD
        self.lbl_loading = QLabel("⏳ Cargando carta en HD...", self)
        self.lbl_loading.setStyleSheet("""
            QLabel {
                background-color: rgba(14, 165, 233, 0.90);
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                border: 1.5px solid rgba(255, 255, 255, 0.4);
                border-radius: 14px;
                padding: 6px 18px;
            }
        """)
        self.lbl_loading.adjustSize()
        self.lbl_loading.hide()

        self._closing = False
        self.origin_rect = QRect()
        self._opened_timestamp = 0
        self._current_id_api = None

        self.hide()

    @pyqtProperty(int)
    def bgAlpha(self):
        return self._bg_alpha

    @bgAlpha.setter
    def bgAlpha(self, val):
        self._bg_alpha = int(val)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self._bg_alpha > 0:
            painter.fillRect(self.rect(), QColor(8, 12, 20, self._bg_alpha))
        super().paintEvent(event)

    def show_zoom(self, pixmap: QPixmap, origin_global_rect: QRect, id_api: str = None, nombre_archivo: str = None, set_id: str = None, number: str = None, idioma: str = None):
        if not self.parent_window or pixmap.isNull():
            return

        self._current_id_api = id_api
        self._opened_timestamp = QDateTime.currentMSecsSinceEpoch()
        self._closing = False
        self.setGeometry(self.parent_window.rect())
        self.show()
        self.raise_()

        # Mostrar indicador flotante "Cargando carta en HD..."
        self.lbl_loading.setText("⏳ Cargando carta en HD...")
        self.lbl_loading.adjustSize()
        lbl_w = self.lbl_loading.width()
        lbl_h = self.lbl_loading.height()
        lbl_x = (self.width() - lbl_w) // 2
        lbl_y = 16
        self.lbl_loading.setGeometry(lbl_x, lbl_y, lbl_w, lbl_h)
        self.lbl_loading.show()

        # Calcular tamaño proporcional enfocado con espacio adecuado para botones
        avail_h = max(300, self.height() - 120)
        max_h = min(int(avail_h * 0.82), 450)
        max_w = int(max_h * (2.5 / 3.5))

        self.card_3d.set_front_pixmap(pixmap)
        self.card_3d.set_card_size(max_w, max_h)

        # Mapear posición de inicio a coordenadas locales de este overlay
        top_left = self.mapFromGlobal(origin_global_rect.topLeft())
        self.origin_rect = QRect(top_left, origin_global_rect.size())

        # Mapear posición de destino centrada (calculando offset de la carta visual)
        total_w = self.card_3d.width()
        total_h = self.card_3d.height()

        visual_card_top = (self.height() - max_h - 40) // 2
        visual_card_left = (self.width() - max_w) // 2

        center_x = visual_card_left - 80
        center_y = visual_card_top - 80

        self.target_rect = QRect(center_x, center_y, total_w, total_h)

        # Posicionar barra de botones abajo centrada sin superponerse con la carta
        ctrl_w = self.controls_widget.sizeHint().width()
        ctrl_h = self.controls_widget.sizeHint().height()
        ctrl_x = (self.width() - ctrl_w) // 2
        ctrl_y = visual_card_top + max_h + 14
        if ctrl_y + ctrl_h > self.height() - 10:
            ctrl_y = self.height() - ctrl_h - 10

        self.controls_widget.setGeometry(ctrl_x, ctrl_y, ctrl_w, ctrl_h)

        self.card_3d.setGeometry(self.origin_rect)
        self.bgAlpha = 0

        # Animación de entrada
        self.anim_geom_in = QPropertyAnimation(self.card_3d, b"geometry", self)
        self.anim_geom_in.setDuration(320)
        self.anim_geom_in.setStartValue(self.origin_rect)
        self.anim_geom_in.setEndValue(self.target_rect)
        self.anim_geom_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.anim_bg_in = QPropertyAnimation(self, b"bgAlpha", self)
        self.anim_bg_in.setDuration(300)
        self.anim_bg_in.setStartValue(0)
        self.anim_bg_in.setEndValue(225)
        self.anim_bg_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.group_in = QParallelAnimationGroup(self)
        self.group_in.addAnimation(self.anim_geom_in)
        self.group_in.addAnimation(self.anim_bg_in)

        def on_in_finished():
            if not self._closing:
                self.bgAlpha = 225
                self.card_3d.setGeometry(self.target_rect)

        self.group_in.finished.connect(on_in_finished)
        self.group_in.start()

        # Iniciar carga/descarga de imagen Full HD (.png) en segundo plano en assets/images_hd
        if id_api:
            card_lang = idioma
            if not card_lang:
                try:
                    session = SessionLocal()
                    c_db = session.query(Cartas).filter(Cartas.id_api == id_api).first()
                    session.close()
                    if c_db and c_db.idioma:
                        card_lang = c_db.idioma
                except Exception:
                    pass

            if not card_lang:
                card_lang = language_manager.current_language

            # 1. Comprobar si ya existe la versión HD en PNG guardada localmente en assets/images_hd
            existing_hd = get_hd_pixmap(id_api, nombre_archivo, card_lang)
            if existing_hd and not existing_hd.isNull():
                self.card_3d.set_front_pixmap(existing_hd)
                if hasattr(self, 'lbl_loading'):
                    self.lbl_loading.hide()
            else:
                # 2. Si no existe en HD, mostrar "Cargando carta en HD..." e iniciar descarga
                if hasattr(self, 'lbl_loading'):
                    self.lbl_loading.setText("⏳ Cargando carta en HD...")
                    self.lbl_loading.adjustSize()
                    lbl_w = self.lbl_loading.width()
                    lbl_h = self.lbl_loading.height()
                    lbl_x = (self.width() - lbl_w) // 2
                    lbl_y = 20
                    self.lbl_loading.setGeometry(lbl_x, lbl_y, lbl_w, lbl_h)
                    self.lbl_loading.show()

                if hasattr(self, 'hd_thread') and self.hd_thread:
                    try:
                        self.hd_thread.image_loaded.disconnect()
                    except Exception:
                        pass

                self.hd_thread = HDImageDownloaderThread(
                    id_api, set_id=set_id, number=number, nombre_archivo=nombre_archivo, idioma=card_lang, parent=None
                )
                self.hd_thread.image_loaded.connect(self._on_hd_loaded)
                self.hd_thread.finished.connect(self.hd_thread.deleteLater)
                self.hd_thread.start()

    def _on_hd_loaded(self, hd_pixmap: QPixmap, returned_id_api: str):
        if self._closing or returned_id_api != self._current_id_api or hd_pixmap.isNull():
            return

        self.card_3d.set_front_pixmap(hd_pixmap)
        if hasattr(self, 'lbl_loading'):
            self.lbl_loading.hide()

    def mousePressEvent(self, event):
        # Ignorar toques/soltadas que ocurran durante el primer toque (350 ms) o en el widget 3d/controles
        if (QDateTime.currentMSecsSinceEpoch() - self._opened_timestamp) < 350:
            return
        if self.card_3d.geometry().contains(event.pos()) or self.controls_widget.geometry().contains(event.pos()):
            return
        self.close_zoom()

    def close_zoom(self):
        if self._closing:
            return
        self._closing = True

        if hasattr(self, 'lbl_loading'):
            self.lbl_loading.hide()

        if hasattr(self, 'hd_thread') and self.hd_thread:
            try:
                self.hd_thread.image_loaded.disconnect()
            except Exception:
                pass

        if hasattr(self, 'group_in') and self.group_in:
            self.group_in.stop()

        # Animación lenta y fluida de regreso (Fade Out)
        self.anim_geom_out = QPropertyAnimation(self.card_3d, b"geometry", self)
        self.anim_geom_out.setDuration(380)
        self.anim_geom_out.setStartValue(self.card_3d.geometry())
        self.anim_geom_out.setEndValue(self.origin_rect)
        self.anim_geom_out.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.anim_bg_out = QPropertyAnimation(self, b"bgAlpha", self)
        self.anim_bg_out.setDuration(380)
        self.anim_bg_out.setStartValue(self.bgAlpha)
        self.anim_bg_out.setEndValue(0)
        self.anim_bg_out.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.group_out = QParallelAnimationGroup(self)
        self.group_out.addAnimation(self.anim_geom_out)
        self.group_out.addAnimation(self.anim_bg_out)

        def al_completar():
            self.hide()
            self.deleteLater()

        self.group_out.finished.connect(al_completar)
        self.group_out.start()


class ClickableLabel(QLabel):
    clicked = pyqtSignal(object, str)

    def __init__(self, id_carta, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id_carta = id_carta
        self.seleccionada = False
        self._press_pos = None
        self._press_timer = QTimer(self)
        self._press_timer.setSingleShot(True)
        self._press_timer.timeout.connect(self._on_long_press)
        self._is_long_press = False

    def mousePressEvent(self, event):
        try:
            if event.button() == Qt.MouseButton.LeftButton:
                self._is_long_press = False
                self._press_pos = event.pos()
                self._press_timer.start(450)
            super().mousePressEvent(event)
        except Exception as e:
            print(f"Error en mousePressEvent: {e}")

    def mouseMoveEvent(self, event):
        try:
            if self._press_timer.isActive() and self._press_pos is not None:
                if (event.pos() - self._press_pos).manhattanLength() > 10:
                    self._press_timer.stop()
            super().mouseMoveEvent(event)
        except Exception as e:
            print(f"Error en mouseMoveEvent: {e}")

    def mouseReleaseEvent(self, event):
        try:
            if event.button() == Qt.MouseButton.LeftButton:
                if self._press_timer.isActive():
                    self._press_timer.stop()
                    self.ejecutar_animacion_burbuja()
                    self.clicked.emit(self, self.id_carta)
                elif self._is_long_press:
                    self._is_long_press = False
            super().mouseReleaseEvent(event)
        except Exception as e:
            print(f"Error en mouseReleaseEvent: {e}")

    def _on_long_press(self):
        self._is_long_press = True
        parent_win = self.window()
        if not parent_win:
            return

        pix = self.pixmap()
        nombre_archivo = None
        set_id = None
        number = None
        idioma = None

        if self.id_carta:
            parent_widget = self.parent()
            carta_obj = getattr(parent_widget, 'carta', None) if parent_widget else None
            nombre = getattr(carta_obj, 'nombre', None)
            idioma = getattr(carta_obj, 'idioma', None)
            if nombre:
                nombre_archivo = nombre.lower().replace(" ", "_")
                set_id = getattr(carta_obj, 'set_id', None)
                number = getattr(carta_obj, 'number', None)
                card_lang = idioma or language_manager.current_language
                hi_pix = get_hd_pixmap(self.id_carta, nombre, card_lang, size=(450, 630))
                if not hi_pix:
                    hi_pix = get_webp_pixmap(self.id_carta, nombre, card_lang, size=(450, 630))
                if not hi_pix:
                    hi_pix = get_pixmap_from_zip(nombre_archivo, size=(450, 630), id_api=self.id_carta)
                if hi_pix:
                    pix = hi_pix
                    pix = hi_pix

        if pix and not pix.isNull():
            origin_global = QRect(self.mapToGlobal(QPoint(0, 0)), self.size())
            overlay = CardZoomOverlay(parent_win)
            overlay.show_zoom(
                pix, origin_global,
                id_api=self.id_carta,
                nombre_archivo=nombre_archivo,
                set_id=set_id,
                number=number,
                idioma=idioma
            )

    def ejecutar_animacion_burbuja(self):
        parent = self.window()
        if not parent:
            return

        burbuja = QWidget(parent)
        burbuja.setStyleSheet("""
            background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                stop:0 rgba(255, 255, 255, 220),
                stop:0.5 rgba(243, 200, 209, 130),
                stop:0.8 rgba(255, 182, 193, 60),
                stop:1 rgba(255, 255, 255, 0));
            border: 2px solid rgba(255, 255, 255, 200);
            border-radius: 999px;
        """)

        pos_global = self.mapTo(parent, QPoint(0, 0))
        w = self.width()
        h = self.height()
        centro = QPoint(pos_global.x() + w // 2, pos_global.y() + h // 2)

        tam_inicial = 8
        r_inicial = QRect(centro.x() - tam_inicial // 2, centro.y() - tam_inicial // 2, tam_inicial, tam_inicial)
        burbuja.setGeometry(r_inicial)
        burbuja.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        burbuja.show()

        opacidad = QGraphicsOpacityEffect(burbuja)
        burbuja.setGraphicsEffect(opacidad)

        tam_final = max(w, h) + 30
        r_final = QRect(centro.x() - tam_final // 2, centro.y() - tam_final // 2, tam_final, tam_final)

        anim_geom = QPropertyAnimation(burbuja, b"geometry", self)
        anim_geom.setDuration(350)
        anim_geom.setStartValue(r_inicial)
        anim_geom.setEndValue(r_final)
        anim_geom.setEasingCurve(QEasingCurve.Type.OutQuad)

        anim_opac = QPropertyAnimation(opacidad, b"opacity", self)
        anim_opac.setDuration(350)
        anim_opac.setStartValue(1.0)
        anim_opac.setEndValue(0.0)
        anim_opac.setEasingCurve(QEasingCurve.Type.InQuad)

        grupo = QParallelAnimationGroup(self)
        grupo.addAnimation(anim_geom)
        grupo.addAnimation(anim_opac)

        if not hasattr(self, '_burbujas_activas'):
            self._burbujas_activas = []
        item_ref = (burbuja, opacidad, grupo)
        self._burbujas_activas.append(item_ref)

        def limpiar():
            burbuja.deleteLater()
            if item_ref in self._burbujas_activas:
                self._burbujas_activas.remove(item_ref)

        grupo.finished.connect(limpiar)
        grupo.start()


class InfoIconLabel(QLabel):
    def __init__(self, carta, parent=None):
        super().__init__(parent)
        self.carta = carta
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        info_icon_path = os.path.join(ICONS_DIR, "info.png")
        if os.path.exists(info_icon_path):
            pix = QPixmap(info_icon_path).scaled(
                16, 16,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(pix)
            self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            self.setText("i")
            self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setStyleSheet("""
            QLabel {
                background-color: rgba(15, 23, 42, 220);
                border: 1.5px solid rgba(56, 189, 248, 200);
                border-radius: 12px;
                padding: 2px;
            }
            QLabel:hover {
                background-color: rgba(56, 189, 248, 240);
                border: 1.5px solid #ffffff;
            }
        """)

        self.tooltip_html = self.build_tooltip_html(carta)
        self.setToolTip(self.tooltip_html)

    def build_tooltip_html(self, carta):
        nombre = getattr(carta, 'nombre', 'Desconocido')
        id_api = getattr(carta, 'id_api', 'N/A')
        price = getattr(carta, 'price', None)
        precio_fmt = f"${price:.2f}" if (price is not None and price > 0) else t("No disponible")
        tipo = getattr(carta, 'type', None) or t("No disponible")
        set_nombre = getattr(carta, 'set_name', None) or t("No disponible")
        set_id = getattr(carta, 'set_id', None) or ""
        set_str = f"{set_nombre} ({set_id})" if set_id else set_nombre
        numero = getattr(carta, 'number', None) or t("No disponible")
        rareza = getattr(carta, 'rarity', None) or t("No disponible")
        etapa = getattr(carta, 'stage', None) or t("No disponible")
        edicion = getattr(carta, 'edition', None) or t("No disponible")
        entrenador = getattr(carta, 'trainer', None) or t("No disponible")
        especial = getattr(carta, 'especial_type', None) or t("No disponible")

        lbl_tipo = t("Tipo")
        lbl_set = t("Set / Serie:")
        lbl_num = t("Número:")
        lbl_rar = t("Rareza")
        lbl_eta = t("Etapa")
        lbl_pre = t("Precio mercado:")
        lbl_esp = t("Especial")
        lbl_ent = t("Entrenador")
        lbl_edi = t("Edición")

        html = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; min-width: 220px; padding: 4px; color: #f8fafc;">
            <div style="font-size: 14px; font-weight: bold; color: #38bdf8; margin-bottom: 4px; border-bottom: 2px solid #0284c7; padding-bottom: 4px;">
                {nombre}
            </div>
            <div style="font-size: 11px; color: #94a3b8; margin-bottom: 6px;">
                ID: <span style="color: #cbd5e1;">{id_api}</span>
            </div>
            <table style="width: 100%; border-spacing: 0px 4px; font-size: 12px;">
                <tr>
                    <td style="color: #94a3b8; padding-right: 10px;"><b>{lbl_tipo}:</b></td>
                    <td style="color: #f8fafc; font-weight: 500;">{tipo}</td>
                </tr>
                <tr>
                    <td style="color: #94a3b8; padding-right: 10px;"><b>{lbl_set}</b></td>
                    <td style="color: #f8fafc;">{set_str}</td>
                </tr>
                <tr>
                    <td style="color: #94a3b8; padding-right: 10px;"><b>{lbl_num}</b></td>
                    <td style="color: #f8fafc;">{numero}</td>
                </tr>
                <tr>
                    <td style="color: #94a3b8; padding-right: 10px;"><b>{lbl_rar}:</b></td>
                    <td style="color: #f8fafc;">{rareza}</td>
                </tr>
                <tr>
                    <td style="color: #94a3b8; padding-right: 10px;"><b>{lbl_eta}:</b></td>
                    <td style="color: #f8fafc;">{etapa}</td>
                </tr>
                {"<tr><td style='color: #94a3b8; padding-right: 10px;'><b>" + lbl_esp + ":</b></td><td style='color: #f8fafc;'>" + especial + "</td></tr>" if especial not in ("Normal", "N/A", "Ninguno") else ""}
                {"<tr><td style='color: #94a3b8; padding-right: 10px;'><b>" + lbl_ent + ":</b></td><td style='color: #f8fafc;'>" + entrenador + "</td></tr>" if entrenador not in ("Desconocido", "N/A", "Ninguno") else ""}
                {"<tr><td style='color: #94a3b8; padding-right: 10px;'><b>" + lbl_edi + ":</b></td><td style='color: #f8fafc;'>" + edicion + "</td></tr>" if edicion not in ("Ninguno", "N/A") else ""}
                <tr>
                    <td style="color: #94a3b8; padding-right: 10px; padding-top: 6px;"><b>{lbl_pre}</b></td>
                    <td style="color: #4ade80; font-size: 13px; font-weight: bold; padding-top: 6px;">{precio_fmt}</td>
                </tr>
            </table>
        </div>
        """
        return html.strip()

    def enterEvent(self, event):
        pos = QCursor.pos()
        pos.setX(pos.x() + 12)
        pos.setY(pos.y() + 12)
        QToolTip.showText(pos, self.tooltip_html, self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        QToolTip.hideText()
        super().leaveEvent(event)




