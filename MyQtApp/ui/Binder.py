import json
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, 
    QGridLayout, QFrame, QPushButton, QApplication, QSizePolicy,
    QStackedWidget, QGraphicsOpacityEffect, QLineEdit, QComboBox,
    QDialog, QMessageBox, QColorDialog
)
from PyQt6.QtCore import Qt, QMimeData, QPoint, QSize, QEasingCurve, QPropertyAnimation, QRect, QTimer
from PyQt6.QtGui import QDrag, QPixmap, QCursor, QAction
from sqlalchemy import func

from MyQtApp.config import ASSETS_DIR, IMAGES_DIR
from ..session import SessionLocal
from ..models import Cartas, UsuarioCarta
from ..app.getImgs import get_pixmap_from_zip, get_webp_pixmap
from MyQtApp.i18n import t, language_manager
from MyQtApp.ui.CardWidget import CardZoomOverlay, VariantBadgeButton, LanguageBadgeLabel
from MyQtApp.ui.toast import show_toast




# --- CONSTANTS & CONFIGURATION ---
BINDER_DATA_FILE = os.path.join(ASSETS_DIR, "binder_data.json")

BINDER_MODES = {
    "2x2": {
        "rows": 2,
        "cols": 2,
        "slot_w": 130,
        "slot_h": 180,
        "card_w": 120,
        "card_h": 170
    },
    "3x3": {
        "rows": 3,
        "cols": 3,
        "slot_w": 110,
        "slot_h": 155,
        "card_w": 100,
        "card_h": 145
    },
    "3x4": {
        "rows": 3,
        "cols": 4,
        "slot_w": 85,
        "slot_h": 120,
        "card_w": 75,
        "card_h": 105
    },
    "4x4": {
        "rows": 4,
        "cols": 4,
        "slot_w": 85,
        "slot_h": 120,
        "card_w": 75,
        "card_h": 105
    }
}

class DraggableCardLabel(QLabel):
    def __init__(self, id_api, nombre_archivo, pixmap, parent=None):
        super().__init__(parent)
        self.id_api = id_api
        self.nombre_archivo = nombre_archivo
        self.drag_start_position = QPoint()
        self.setPixmap(pixmap)
        self.setScaledContents(True)
        self.setFixedSize(100, 140)  # Adjust size as needed
        self.setStyleSheet("border: 1px solid #ddd; border-radius: 5px;")
        
        self.long_press_timer = QTimer(self)
        self.long_press_timer.setSingleShot(True)
        self.long_press_timer.timeout.connect(self._on_long_press)

    def mousePressEvent(self, event):
        try:
            if event.button() == Qt.MouseButton.LeftButton:
                self.drag_start_position = event.pos()
                self.long_press_timer.start(260)
            super().mousePressEvent(event)
        except Exception as e:
            print(f"Error en DraggableCardLabel mousePressEvent: {e}")

    def mouseMoveEvent(self, event):
        try:
            if not (event.buttons() & Qt.MouseButton.LeftButton):
                return
            if getattr(self, 'drag_start_position', None) and (event.pos() - self.drag_start_position).manhattanLength() >= QApplication.startDragDistance():
                self.long_press_timer.stop()

                drag = QDrag(self)
                mime_data = QMimeData()
                
                # Pass card ID and source info
                mime_data.setText(self.id_api)
                mime_data.setProperty("source", "inventory")
                mime_data.setProperty("nombre_archivo", self.nombre_archivo)
                mime_data.setProperty("idioma", getattr(self, "idioma", "en") or "en")
                drag.setMimeData(mime_data)

                # Set drag pixmap
                if self.pixmap() and not self.pixmap().isNull():
                    drag.setPixmap(self.pixmap().scaled(80, 112, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                drag.setHotSpot(event.pos())

                drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)
        except Exception as e:
            print(f"Error en DraggableCardLabel mouseMoveEvent: {e}")

    def mouseReleaseEvent(self, event):
        try:
            if self.long_press_timer.isActive():
                self.long_press_timer.stop()
            super().mouseReleaseEvent(event)
        except Exception as e:
            print(f"Error en DraggableCardLabel mouseReleaseEvent: {e}")


    def _on_long_press(self):
        parent_win = self.window()
        pix = self.pixmap()
        idioma = getattr(self, 'idioma', None)
        if not idioma and self.id_api:
            try:
                session = SessionLocal()
                c_db = session.query(Cartas).filter(Cartas.id_api == self.id_api).first()
                session.close()
                if c_db and c_db.idioma:
                    idioma = c_db.idioma
            except Exception:
                pass

        card_lang = idioma or language_manager.current_language
        if self.nombre_archivo:
            hi_pix = get_webp_pixmap(self.id_api, self.nombre_archivo, card_lang, size=(450, 630))
            if not hi_pix:
                hi_pix = get_pixmap_from_zip(self.nombre_archivo, size=(450, 630), id_api=self.id_api)
            if hi_pix:
                pix = hi_pix
        if parent_win and pix and not pix.isNull():
            origin_global = QRect(self.mapToGlobal(QPoint(0, 0)), self.size())
            overlay = CardZoomOverlay(parent_win)
            overlay.show_zoom(pix, origin_global, id_api=self.id_api, nombre_archivo=self.nombre_archivo, idioma=idioma)

class BinderSlot(QLabel):
    def __init__(self, page_index, slot_index, parent=None, binder_view=None, slot_w=120, slot_h=170, card_w=110, card_h=160):
        super().__init__(parent)
        self.page_index = page_index
        self.slot_index = slot_index
        self.binder_view = binder_view
        self.id_api = None
        self.nombre_archivo = None
        self.idioma = None
        self.variante = "Normal"
        self.selected = False
        self.slot_w = slot_w
        self.slot_h = slot_h
        self.card_w = card_w
        self.card_h = card_h
        self.drag_start_position = QPoint()
        self.variant_badge = None
        self.lang_badge = None
        
        self.setFixedSize(slot_w, slot_h)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        self.update_style()

        self.long_press_timer = QTimer(self)
        self.long_press_timer.setSingleShot(True)
        self.long_press_timer.timeout.connect(self._on_long_press)

    def set_selected(self, val: bool):
        if not self.id_api:
            self.selected = False
        else:
            self.selected = val
        self.update_style()
        if self.binder_view and hasattr(self.binder_view, 'update_selection_state'):
            self.binder_view.update_selection_state()

    def _on_long_press(self):
        if not self.id_api:
            return
        parent_win = self.window()
        pix = self.pixmap()
        idioma = getattr(self, 'idioma', None)
        if not idioma and self.id_api:
            try:
                session = SessionLocal()
                c_db = session.query(Cartas).filter(Cartas.id_api == self.id_api).first()
                session.close()
                if c_db and c_db.idioma:
                    idioma = c_db.idioma
            except Exception:
                pass

        card_lang = idioma or language_manager.current_language
        if self.nombre_archivo:
            hi_pix = get_webp_pixmap(self.id_api, self.nombre_archivo, card_lang, size=(450, 630))
            if not hi_pix:
                hi_pix = get_pixmap_from_zip(self.nombre_archivo, size=(450, 630), id_api=self.id_api)
            if hi_pix:
                pix = hi_pix
        if parent_win and pix and not pix.isNull():
            origin_global = QRect(self.mapToGlobal(QPoint(0, 0)), self.size())
            overlay = CardZoomOverlay(parent_win)
            overlay.show_zoom(pix, origin_global, id_api=self.id_api, nombre_archivo=self.nombre_archivo, idioma=idioma)

    def update_style(self):
        if self.id_api:
            if self.selected:
                self.setStyleSheet("""
                    QLabel {
                        background-color: rgba(225, 29, 72, 0.22);
                        border: 3.5px solid #e11d48;
                        border-radius: 8px;
                    }
                """)
            else:
                self.setStyleSheet("""
                    QLabel {
                        background-color: transparent;
                        border: 2px solid #f29ca4;
                        border-radius: 8px;
                    }
                """)
        else:
            self.selected = False
            self.setStyleSheet("""
                QLabel {
                    background-color: white;
                    border: 2px dashed #f29ca4;
                    border-radius: 8px;
                }
            """)
            self.clear()

    def set_card(self, id_api, nombre_archivo, pixmap, idioma=None, variante="Normal"):
        self.id_api = id_api
        self.nombre_archivo = nombre_archivo
        self.idioma = idioma
        self.variante = variante or "Normal"
        self.selected = False
        if pixmap:
            self.setPixmap(pixmap.scaled(self.card_w, self.card_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        # Botón vertical de variante (arriba a la izquierda)
        if not self.variant_badge:
            self.variant_badge = VariantBadgeButton(self.id_api, self.variante, self)
            self.variant_badge.variant_changed.connect(self._on_slot_variant_changed)
        else:
            self.variant_badge.id_api = self.id_api
            self.variant_badge.set_variante(self.variante)

        self.variant_badge.move(3, 3)
        self.variant_badge.show()
        self.variant_badge.raise_()

        # Insignia de idioma (abajo a la izquierda)
        if self.idioma:
            if not self.lang_badge:
                self.lang_badge = LanguageBadgeLabel(self.idioma, self)
            else:
                self.lang_badge.setText(self.idioma)
            
            bh = self.lang_badge.height()
            self.lang_badge.move(3, self.slot_h - bh - 3)
            self.lang_badge.show()
            self.lang_badge.raise_()
        elif self.lang_badge:
            self.lang_badge.hide()

        self.update_style()

    def _on_slot_variant_changed(self, id_api, nueva_variante):
        self.variante = nueva_variante
        if self.binder_view and hasattr(self.binder_view, 'update_slot_variant'):
            self.binder_view.update_slot_variant(self.page_index, self.slot_index, nueva_variante)

    def clear_card(self):
        self.id_api = None
        self.nombre_archivo = None
        self.idioma = None
        self.variante = "Normal"
        self.selected = False
        if self.variant_badge:
            self.variant_badge.hide()
        if self.lang_badge:
            self.lang_badge.hide()
        self.clear()
        self.update_style()


    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        try:
            card_id = event.mimeData().text()
            source = event.mimeData().property("source")
            source_slot = event.mimeData().property("source_slot")
            nombre_archivo = event.mimeData().property("nombre_archivo")
            idioma = event.mimeData().property("idioma")
            
            if card_id:
                # Tell the main view to handle the drop (update logic and UI)
                if self.binder_view:
                    self.binder_view.handle_drop(
                        self.page_index, self.slot_index, card_id, 
                        source_slot=source_slot, nombre_archivo=nombre_archivo, idioma=idioma
                    )
                event.accept()
        except Exception as e:
            print(f"Error en BinderSlot dropEvent: {e}")
     
    # Allow dragging FROM the slot too
    def mousePressEvent(self, event):
        try:
            if event.button() == Qt.MouseButton.LeftButton and self.id_api:
                self.drag_start_position = event.pos()
                self.long_press_timer.start(260)
        except Exception as e:
            print(f"Error en BinderSlot mousePressEvent: {e}")

    def mouseMoveEvent(self, event):
        try:
            if not self.id_api:
                return
            if not (event.buttons() & Qt.MouseButton.LeftButton):
                return
            if getattr(self, 'drag_start_position', None) and (event.pos() - self.drag_start_position).manhattanLength() >= QApplication.startDragDistance():
                self.long_press_timer.stop()

                drag = QDrag(self)
                mime_data = QMimeData()
                mime_data.setText(self.id_api)
                mime_data.setProperty("source", "binder")
                mime_data.setProperty("source_slot", f"{self.page_index}_{self.slot_index}")
                mime_data.setProperty("nombre_archivo", self.nombre_archivo)
                mime_data.setProperty("idioma", getattr(self, "idioma", "en") or "en")
                drag.setMimeData(mime_data)
                
                if self.pixmap() and not self.pixmap().isNull():
                    drag.setPixmap(self.pixmap().scaled(80, 112, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    drag.setHotSpot(event.pos())
                
                drag.exec(Qt.DropAction.CopyAction)
        except Exception as e:
            print(f"Error en BinderSlot mouseMoveEvent: {e}")


    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.long_press_timer.isActive():
                self.long_press_timer.stop()
                if self.id_api:
                    self.set_selected(not self.selected)
        super().mouseReleaseEvent(event)


class InventorySidebar(QWidget):
    def __init__(self, usuario, parent=None):
        super().__init__(parent)
        self.usuario = usuario

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header Title
        self.header = QLabel(t("Colección"))
        self.header.setStyleSheet(
            "font-weight: bold; color: #5a2a3a; font-size: 15px;"
            " border: none; background: transparent;"
        )
        layout.addWidget(self.header)

        # 1. Buscador (usa clase SearchInput del QSS global)
        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText(t("Buscar carta por nombre..."))
        self.buscador.setProperty("class", "SearchInput")
        self.timer_busqueda = QTimer()
        self.timer_busqueda.setSingleShot(True)
        self.timer_busqueda.setInterval(300)
        self.timer_busqueda.timeout.connect(self.load_cards)
        self.buscador.textChanged.connect(lambda: self.timer_busqueda.start())
        layout.addWidget(self.buscador)

        # 2. Botón Filtros (usa clase BinderNavBtn del QSS global)
        self.btn_toggle_filtros = QPushButton("⚙️ Filtros ▼")
        self.btn_toggle_filtros.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_filtros.setProperty("class", "BinderNavBtn")
        self.btn_toggle_filtros.clicked.connect(self.toggle_filters_panel)
        layout.addWidget(self.btn_toggle_filtros)

        # 3. Panel desplegable de filtros
        self.filters_panel = QWidget()
        self.filters_panel.setObjectName("binder_filters_panel")
        self.filters_panel.setStyleSheet("""
            QWidget#binder_filters_panel {
                background-color: #fff0f3;
                border: 1.5px solid #f2c4ce;
                border-radius: 10px;
            }
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #703043;
                border: none;
                background: transparent;
            }
            QComboBox {
                background-color: white;
                border: 1.5px solid #f29ca4;
                border-radius: 8px;
                padding: 3px 8px;
                font-size: 12px;
                min-height: 30px;
            }
        """)
        self.filters_panel.setVisible(False)

        panel_layout = QVBoxLayout(self.filters_panel)
        panel_layout.setContentsMargins(10, 10, 10, 10)
        panel_layout.setSpacing(6)

        self.filtros = {}
        campos = {
            "Idioma": "idioma",
            "Rareza": "rarity",
            "Tipo": "type",
            "Edición": "edition",
            "Etapa": "stage",
            "Entrenador": "trainer",
            "Especial": "especial_type"
        }

        for label_text, col_name in campos.items():
            lbl = QLabel(label_text)
            panel_layout.addWidget(lbl)
            combo = QComboBox()
            combo.addItem("Todos")
            self.filtros[col_name] = combo
            panel_layout.addWidget(combo)

        # Botón Aplicar (usa clase pill del QSS global)
        self.btn_aplicar_filtros = QPushButton("✅ Aplicar Filtros")
        self.btn_aplicar_filtros.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_aplicar_filtros.setProperty("class", "pill")
        self.btn_aplicar_filtros.clicked.connect(self.load_cards)
        panel_layout.addWidget(self.btn_aplicar_filtros)

        layout.addWidget(self.filters_panel)

        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background-color: #fff7f8; border: none;")

        self.container = QWidget()
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setSpacing(12)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        self.cargar_opciones_filtros()
        self.load_cards()

    def retranslate_ui(self):
        self.header.setText(t("Colección"))
        self.buscador.setPlaceholderText(t("Buscar carta por nombre..."))
        if hasattr(self, 'btn_aplicar_filtros'):
            self.btn_aplicar_filtros.setText(f"✅ {t('Aplicar')}")


    def toggle_filters_panel(self):
        visible = not self.filters_panel.isVisible()
        self.filters_panel.setVisible(visible)
        if visible:
            self.btn_toggle_filtros.setText("⚙️ Filtros ▲")
        else:
            self.btn_toggle_filtros.setText("⚙️ Filtros ▼")

    def cargar_opciones_filtros(self):
        session = SessionLocal()
        try:
            for col_name, combo in self.filtros.items():
                combo.clear()
                combo.addItem("Todos")
                valores = (
                    session.query(getattr(Cartas, col_name))
                    .join(UsuarioCarta, Cartas.id_api == UsuarioCarta.carta_id)
                    .filter(UsuarioCarta.usuario_nombre == self.usuario)
                    .filter(getattr(Cartas, col_name).isnot(None))
                    .distinct()
                    .all()
                )
                sorted_vals = sorted(v[0] for v in valores if v[0])
                for val in sorted_vals:
                    combo.addItem(val)
        finally:
            session.close()

    def _create_card_row_widget(self, id_api, map_idiomas):
        idiomas_disponibles = list(map_idiomas.keys())
        if not idiomas_disponibles:
            return None

        lang_upper_map = {"es": "ES", "en": "EN", "ja": "JA", "fr": "FR", "pt": "PT", "zh": "ZH", "zh-tw": "ZH"}
        flag_emoji_map = {"es": "🇪🇸", "en": "🇬🇧", "ja": "🇯🇵", "fr": "🇫🇷", "pt": "🇵🇹", "zh": "🇨🇳", "zh-tw": "🇨🇳"}

        item_container = QWidget()
        item_layout = QHBoxLayout(item_container)
        item_layout.setContentsMargins(4, 2, 4, 2)
        item_layout.setSpacing(8)

        lang_badge_btn = QPushButton()
        lang_badge_btn.setFixedWidth(44)
        lang_badge_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        first_lang = idiomas_disponibles[0]
        first_carta = map_idiomas[first_lang]
        nombre_archivo = first_carta.nombre.lower().replace(" ", "_")

        pixmap = get_webp_pixmap(id_api, first_carta.nombre, first_lang, size=(100, 140))
        if not pixmap:
            pixmap = get_pixmap_from_zip(nombre_archivo, size=(100, 140), id_api=id_api)
        if not pixmap:
            ruta_alt = os.path.join(IMAGES_DIR, f"{nombre_archivo}_{id_api}.webp")
            if os.path.exists(ruta_alt):
                pixmap = QPixmap(ruta_alt)

        card_lbl = DraggableCardLabel(id_api, nombre_archivo, pixmap or QPixmap())
        card_lbl.idioma = first_lang

        state = {
            "index": 0,
            "idiomas": idiomas_disponibles
        }

        def update_display(idx_val):
            state["index"] = idx_val
            current_l = state["idiomas"][idx_val]
            c_obj = map_idiomas[current_l]
            n_arch = c_obj.nombre.lower().replace(" ", "_")

            l_upper = lang_upper_map.get(current_l.lower(), current_l.upper())
            f_emoji = flag_emoji_map.get(current_l.lower(), "🌐")

            if len(state["idiomas"]) > 1:
                lang_badge_btn.setText(f"{l_upper} 🔄\n{f_emoji}")
                lang_badge_btn.setToolTip(f"Idioma actual: {l_upper}\n(Haz clic para cambiar entre idiomas en tu colección)")
            else:
                lang_badge_btn.setText(f"{l_upper}\n{f_emoji}")
                lang_badge_btn.setToolTip(f"Idioma disponible: {l_upper}")

            lang_badge_btn.setStyleSheet("""
                QPushButton {
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f43f5e, stop:1 #e11d48);
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 11px;
                    border: 1.5px solid #fda4af;
                    border-radius: 8px;
                    padding: 4px 2px;
                }
                QPushButton:hover {
                    background-color: #be123c;
                    border-color: #ffffff;
                }
            """)

            pix = get_webp_pixmap(id_api, c_obj.nombre, current_l, size=(100, 140))
            if not pix:
                pix = get_pixmap_from_zip(n_arch, size=(100, 140), id_api=id_api)
            if not pix:
                r_alt = os.path.join(IMAGES_DIR, f"{n_arch}_{id_api}.webp")
                if os.path.exists(r_alt):
                    pix = QPixmap(r_alt)

            if pix and not pix.isNull():
                card_lbl.setPixmap(pix)

            card_lbl.idioma = current_l
            card_lbl.nombre_archivo = n_arch
            price_val = f"${c_obj.price:.2f}" if (c_obj.price and c_obj.price > 0) else "N/A"
            card_lbl.setToolTip(f"<b>{c_obj.nombre}</b> [{f_emoji}]<br/>ID: {id_api}<br/>Idioma: {l_upper}<br/>Tipo: {c_obj.type or 'N/A'}<br/>Rareza: {c_obj.rarity or 'N/A'}<br/>Precio: {price_val} USD")

        def cycle_language(checked=False):
            if len(state["idiomas"]) > 1:
                next_idx = (state["index"] + 1) % len(state["idiomas"])
                update_display(next_idx)

        lang_badge_btn.clicked.connect(cycle_language)
        update_display(0)

        item_layout.addWidget(lang_badge_btn)
        item_layout.addWidget(card_lbl)
        return item_container

    def load_cards(self):
        session = SessionLocal()
        try:
            from sqlalchemy import and_, func
            query = (
                session.query(Cartas)
                .join(UsuarioCarta, and_(
                    Cartas.id_api == UsuarioCarta.carta_id,
                    func.coalesce(Cartas.idioma, 'es') == func.coalesce(UsuarioCarta.idioma, 'es')
                ))
                .filter(UsuarioCarta.usuario_nombre == self.usuario)
            )

            # 1. Buscar por nombre
            texto = self.buscador.text().strip().lower()
            if texto:
                query = query.filter(func.lower(Cartas.nombre).like(f"%{texto}%"))

            # 2. Filtros desplegables
            for col_name, combo in self.filtros.items():
                if combo.currentIndex() > 0:
                    val = combo.currentText()
                    query = query.filter(getattr(Cartas, col_name) == val)

            todas_cartas = query.all()

            # Agrupar cartas por id_api y registrar idiomas que el usuario realmente posee
            cartas_por_id = {}
            for carta in todas_cartas:
                id_api = carta.id_api
                card_lang = getattr(carta, 'idioma', 'es') or 'es'
                if id_api not in cartas_por_id:
                    cartas_por_id[id_api] = {}
                cartas_por_id[id_api][card_lang] = carta

            # Limpiar área de cartas
            for i in reversed(range(self.cards_layout.count())):
                item = self.cards_layout.itemAt(i)
                if item and item.widget():
                    item.widget().deleteLater()

            for id_api, map_idiomas in cartas_por_id.items():
                item_widget = self._create_card_row_widget(id_api, map_idiomas)
                if item_widget:
                    self.cards_layout.addWidget(item_widget)
        finally:
            session.close()

    def refresh(self):
        self.cargar_opciones_filtros()
        self.load_cards()


class BinderPage(QWidget):
    def __init__(self, page_index, binder_view, rows, cols, slot_w, slot_h, card_w, card_h, parent=None):
        super().__init__(parent)
        self.page_index = page_index
        self.binder_view = binder_view
        
        layout = QGridLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.slots = []
        for r in range(rows):
            for c in range(cols):
                slot_idx = r * cols + c
                slot = BinderSlot(
                    page_index, 
                    slot_idx, 
                    binder_view=binder_view, 
                    slot_w=slot_w, 
                    slot_h=slot_h, 
                    card_w=card_w, 
                    card_h=card_h
                )
                layout.addWidget(slot, r, c)
                self.slots.append(slot)
                
    def get_slot(self, slot_index):
        if 0 <= slot_index < len(self.slots):
            return self.slots[slot_index]
        return None


class BinderView(QWidget):
    def __init__(self, usuario, parent=None):
        super().__init__(parent)
        self.usuario = usuario
        self.binder_data = {}
        self.current_folder_id = "default"
        self.current_spread_index = 0 # 0 means pages 0 and 1
        self.current_mode = "3x3" # default mode
        
        self.load_binder_data()
        
        # Main Layout: Splitter logic or simple HBox
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- Left Panel: Inventory ---
        left_container = QWidget()
        left_container.setFixedWidth(240) # Sidebar width
        left_container.setStyleSheet("""
            background-color: #ffeef2; 
            border-right: 2px solid #f3c8d1;
        """)
        left_layout = QVBoxLayout(left_container)
        
        self.inventory = InventorySidebar(usuario)
        left_layout.addWidget(self.inventory)
        
        main_layout.addWidget(left_container)
        
        # --- Right Panel: Binder Pages ---
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(20, 20, 20, 10)
        
        # Header layout for Title, Folder Selector and Mode Selector
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        self.title_lbl = QLabel(t("Binder"))
        self.title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #5a2a3a;")
        header_layout.addWidget(self.title_lbl)

        # Selector de Carpetas / Binders
        self.lbl_folder_icon = QLabel("📁")
        self.lbl_folder_icon.setStyleSheet("font-size: 16px; margin-left: 10px;")
        header_layout.addWidget(self.lbl_folder_icon)

        self.combo_folders = QComboBox()
        self.combo_folders.setFixedHeight(30)
        self.combo_folders.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 1.5px solid #f29ca4;
                border-radius: 8px;
                padding: 2px 10px;
                font-weight: 600;
                color: #5a2a3a;
                min-width: 140px;
            }
        """)
        self.combo_folders.currentIndexChanged.connect(self.on_folder_selected)
        header_layout.addWidget(self.combo_folders)

        self.btn_new_folder = QPushButton(f"✨ +{t('Carpeta')}")
        self.btn_new_folder.setFixedHeight(30)
        self.btn_new_folder.setProperty("class", "pill")
        self.btn_new_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_folder.clicked.connect(self.abrir_dialogo_crear_carpeta)
        header_layout.addWidget(self.btn_new_folder)

        self.btn_manage_folders = QPushButton("⚙️")
        self.btn_manage_folders.setFixedHeight(30)
        self.btn_manage_folders.setFixedWidth(34)
        self.btn_manage_folders.setProperty("class", "pill")
        self.btn_manage_folders.setToolTip(t("Administrar o eliminar carpetas"))
        self.btn_manage_folders.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_manage_folders.clicked.connect(self.abrir_dialogo_administrar_carpetas)
        header_layout.addWidget(self.btn_manage_folders)

        header_layout.addStretch()

        # Mode Selector Buttons
        self.mode_buttons = {}
        mode_container = QWidget()
        mode_btn_layout = QHBoxLayout(mode_container)
        mode_btn_layout.setContentsMargins(2, 2, 2, 2)
        mode_btn_layout.setSpacing(6)

        for mode in ["2x2", "3x3", "3x4", "4x4"]:
            btn = QPushButton(mode)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("class", "pill selected" if mode == self.current_mode else "pill")
            btn.setFixedSize(58, 30)
            btn.clicked.connect(lambda checked, m=mode: self.change_mode(m))
            mode_btn_layout.addWidget(btn)
            self.mode_buttons[mode] = btn

        header_layout.addWidget(mode_container)
        right_layout.addLayout(header_layout)

        # Spread Stack Container (Stacked Widget to allow transition animations)
        self.spread_stack = QStackedWidget()
        right_layout.addWidget(self.spread_stack, 1) # Expand

        # References to current visible pages
        self.page_left = None
        self.page_right = None

        # Pagination Controls
        controls_layout = QHBoxLayout()
        self.btn_prev = QPushButton(t("Anterior"))
        self.btn_next = QPushButton(t("Siguiente"))
        self.lbl_pages = QLabel(f"{t('Página')} 1 - 2")

        self.btn_quitar = QPushButton("🗑️ Quitar")
        self.btn_quitar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_quitar.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                font-weight: bold;
                font-size: 13px;
                border-radius: 12px;
                padding: 6px 16px;
                border: none;
            }
            QPushButton:disabled {
                background-color: #e2e8f0;
                color: #94a3b8;
            }
            QPushButton:hover:enabled {
                background-color: #dc2626;
            }
        """)
        self.btn_quitar.setEnabled(False)
        self.btn_quitar.clicked.connect(self.quitar_cartas_seleccionadas)

        for btn in [self.btn_prev, self.btn_next]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("class", "BinderNavBtn")
            
        self.btn_prev.clicked.connect(self.prev_spread)
        self.btn_next.clicked.connect(self.next_spread)
        
        controls_layout.addStretch()
        controls_layout.addWidget(self.btn_prev)
        controls_layout.addWidget(self.lbl_pages)
        controls_layout.addWidget(self.btn_next)
        controls_layout.addSpacing(24)
        controls_layout.addWidget(self.btn_quitar)
        controls_layout.addStretch()
        
        right_layout.addLayout(controls_layout)
        
        main_layout.addWidget(right_container)
        
        # Initialize pages
        self.update_folder_combo()
        self.update_spread(direction=0)
        language_manager.language_changed.connect(self.retranslate_ui)

    def update_folder_combo(self):
        """Llena el combo de carpetas del usuario."""
        self.combo_folders.blockSignals(True)
        self.combo_folders.clear()
        folders = self.get_user_folders()
        for f_id, f_data in folders.items():
            f_name = f_data.get("name", f_id)
            self.combo_folders.addItem(f"📁 {f_name}", f_id)

        # Seleccionar la carpeta actual
        idx = self.combo_folders.findData(self.current_folder_id)
        if idx >= 0:
            self.combo_folders.setCurrentIndex(idx)
        else:
            if self.combo_folders.count() > 0:
                self.combo_folders.setCurrentIndex(0)
                self.current_folder_id = self.combo_folders.currentData()
        self.combo_folders.blockSignals(False)
        self.aplicar_estilo_carpeta_actual()

    def get_user_folders(self) -> dict:
        """Devuelve el diccionario de carpetas del usuario actual."""
        user_data = self.binder_data.setdefault(self.usuario, {})
        folders = user_data.setdefault("folders", {})
        if not folders:
            # Crear carpeta por defecto si no tiene ninguna
            folders["default"] = {
                "name": "Mi Carpeta",
                "color": "#ffeef2",
                "design": "Clásico",
                "mode": "3x3",
                "cards": {
                    "2x2": {},
                    "3x3": {},
                    "3x4": {},
                    "4x4": {}
                }
            }
            self.save_binder_data()
        return folders

    def aplicar_estilo_carpeta_actual(self):
        """Aplica el color y estilo visual definido para la carpeta actual."""
        folders = self.get_user_folders()
        folder = folders.get(self.current_folder_id, {})
        color = folder.get("color", "#ffeef2")
        # Actualizar modo si la carpeta tiene uno guardado
        folder_mode = folder.get("mode")
        if folder_mode and folder_mode in BINDER_MODES and folder_mode != self.current_mode:
            self.current_mode = folder_mode
            for m, btn in self.mode_buttons.items():
                btn.setProperty("class", "pill selected" if m == folder_mode else "pill")
                btn.style().unpolish(btn)
                btn.style().polish(btn)

    def on_folder_selected(self, index):
        folder_id = self.combo_folders.currentData()
        if not folder_id or folder_id == self.current_folder_id:
            return
        self.current_folder_id = folder_id
        self.current_spread_index = 0
        self.aplicar_estilo_carpeta_actual()
        self.update_spread(direction=0)

    def abrir_dialogo_crear_carpeta(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(t("Crear Nueva Carpeta / Binder"))
        dlg.setFixedSize(380, 360)
        dlg.setStyleSheet("""
            QDialog {
                background-color: #fff5f7;
            }
            QLabel {
                font-weight: 600;
                color: #5a2a3a;
                font-size: 12px;
            }
            QLineEdit, QComboBox {
                border: 1.5px solid #f29ca4;
                border-radius: 8px;
                padding: 6px;
                background-color: white;
                font-size: 12px;
            }
        """)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(QLabel(t("Nombre de la carpeta:")))
        txt_nombre = QLineEdit()
        txt_nombre.setPlaceholderText(t("Ej: Vintage Charizards, Set 151..."))
        layout.addWidget(txt_nombre)

        layout.addWidget(QLabel(t("Tamaño / Distribución de cartas:")))
        combo_tamano = QComboBox()
        combo_tamano.addItems(["3x3", "2x2", "3x4", "4x4"])
        layout.addWidget(combo_tamano)

        layout.addWidget(QLabel(t("Diseño de la carpeta:")))
        combo_diseno = QComboBox()
        combo_diseno.addItems(["Clásico Rosa", "Ultra Pro Negro", "Pokéball Rojo", "Master Ball Púrpura", "Pikachu Amarillo"])
        layout.addWidget(combo_diseno)

        layout.addWidget(QLabel(t("Color de portada / fondo:")))
        btn_color = QPushButton(t("Elegir Color Personalizado"))
        btn_color.setProperty("class", "pill")
        btn_color.setFixedHeight(30)
        selected_color = ["#ffeef2"]

        def choose_color():
            c = QColorDialog.getColor(initial=selected_color[0], parent=dlg, title=t("Color de Carpeta"))
            if c.isValid():
                selected_color[0] = c.name()
                btn_color.setText(f"🎨 {selected_color[0]}")
                btn_color.setStyleSheet(f"background-color: {selected_color[0]}; color: #333; font-weight: bold;")

        btn_color.clicked.connect(choose_color)
        layout.addWidget(btn_color)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_cancel = QPushButton(t("Cancelar"))
        btn_cancel.setFixedHeight(34)
        btn_cancel.clicked.connect(dlg.reject)

        btn_crear = QPushButton(f"✨ {t('Crear Carpeta')}")
        btn_crear.setProperty("class", "pill")
        btn_crear.setFixedHeight(34)
        btn_crear.setCursor(Qt.CursorShape.PointingHandCursor)

        def on_crear():
            nombre = txt_nombre.text().strip()
            if not nombre:
                QMessageBox.warning(dlg, t("Error"), t("Debes ingresar un nombre para la carpeta."))
                return
            import time
            new_id = f"folder_{int(time.time() * 1000)}"
            folders = self.get_user_folders()
            folders[new_id] = {
                "name": nombre,
                "color": selected_color[0],
                "design": combo_diseno.currentText(),
                "mode": combo_tamano.currentText(),
                "cards": {
                    "2x2": {},
                    "3x3": {},
                    "3x4": {},
                    "4x4": {}
                }
            }
            self.save_binder_data()
            self.current_folder_id = new_id
            self.current_mode = combo_tamano.currentText()
            self.current_spread_index = 0
            self.update_folder_combo()
            self.update_spread(direction=0)
            show_toast(f"Carpeta '{nombre}' creada con éxito", "info")
            dlg.accept()

        btn_crear.clicked.connect(on_crear)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_crear)
        layout.addLayout(btn_row)

        dlg.exec()

    def abrir_dialogo_administrar_carpetas(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(t("Administrar Carpetas"))
        dlg.setFixedSize(360, 240)
        dlg.setStyleSheet("""
            QDialog {
                background-color: #fff5f7;
            }
            QLabel {
                font-weight: 600;
                color: #5a2a3a;
                font-size: 12px;
            }
            QComboBox {
                border: 1.5px solid #f29ca4;
                border-radius: 8px;
                padding: 6px;
                background-color: white;
            }
        """)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(QLabel(t("Selecciona una carpeta para eliminar:")))
        combo = QComboBox()
        folders = self.get_user_folders()
        for f_id, f_data in folders.items():
            combo.addItem(f"📁 {f_data.get('name', f_id)}", f_id)
        layout.addWidget(combo)

        btn_del = QPushButton(f"🗑️ {t('Eliminar Carpeta')}")
        btn_del.setStyleSheet("""
            QPushButton {
                background-color: #fee2e2;
                color: #dc2626;
                border: 1.5px solid #fca5a5;
                font-weight: bold;
                border-radius: 8px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #fecaca;
                border-color: #ef4444;
            }
        """)
        btn_del.setFixedHeight(34)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)

        def on_eliminar():
            if combo.count() <= 1:
                QMessageBox.warning(dlg, t("Error"), t("Debes tener al menos una carpeta."))
                return
            target_id = combo.currentData()
            target_name = combo.currentText()
            resp = QMessageBox.question(
                dlg,
                t("Confirmar Eliminación"),
                f"{t('¿Seguro que deseas eliminar la carpeta')} {target_name}? {t('Las cartas que contenía dejarán de estar asignadas a este binder (seguirán en tu colección general).')}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resp == QMessageBox.StandardButton.Yes:
                del folders[target_id]
                self.save_binder_data()
                if self.current_folder_id == target_id:
                    self.current_folder_id = next(iter(folders.keys()))
                self.update_folder_combo()
                self.update_spread(direction=0)
                show_toast(t("Carpeta eliminada"), "info")
                dlg.accept()

        btn_del.clicked.connect(on_eliminar)
        layout.addWidget(btn_del)

        btn_close = QPushButton(t("Cerrar"))
        btn_close.setProperty("class", "pill")
        btn_close.setFixedHeight(32)
        btn_close.clicked.connect(dlg.accept)
        layout.addStretch()
        layout.addWidget(btn_close)

        dlg.exec()

    def get_selected_slots(self):
        selected = []
        for page_w in [self.page_left, self.page_right]:
            if page_w and hasattr(page_w, 'slots'):
                for slot in page_w.slots:
                    if slot.id_api and slot.selected:
                        selected.append(slot)
        return selected

    def update_selection_state(self):
        selected_slots = self.get_selected_slots()
        count = len(selected_slots)
        if count > 0:
            self.btn_quitar.setText(f"🗑️ Quitar ({count})")
            self.btn_quitar.setEnabled(True)
        else:
            self.btn_quitar.setText("🗑️ Quitar")
            self.btn_quitar.setEnabled(False)

    def quitar_cartas_seleccionadas(self):
        selected_slots = self.get_selected_slots()
        if not selected_slots:
            return

        for slot in selected_slots:
            # 1. Eliminar la carta del Binder (solo de la carpeta json, NO de la colección en BD)
            self.set_card_at(slot.page_index, slot.slot_index, None)
            # 2. Desactivar selección y limpiar casilla visualmente
            slot.set_selected(False)
            slot.clear_card()

        self.update_selection_state()

    def retranslate_ui(self):
        self.title_lbl.setText(t("Binder"))
        self.btn_prev.setText(t("Anterior"))
        self.btn_next.setText(t("Siguiente"))
        self.btn_quitar.setText("🗑️ Quitar" if not self.get_selected_slots() else f"🗑️ Quitar ({len(self.get_selected_slots())})")
        p_idx_1 = self.current_spread_index * 2
        p_idx_2 = p_idx_1 + 1
        self.lbl_pages.setText(f"{t('Página')} {p_idx_1 + 1} - {p_idx_2 + 1}")
        if hasattr(self.inventory, 'retranslate_ui'):
            self.inventory.retranslate_ui()
        
    def load_binder_data(self):
        if os.path.exists(BINDER_DATA_FILE):
            try:
                with open(BINDER_DATA_FILE, 'r', encoding='utf-8') as f:
                    self.binder_data = json.load(f)
            except:
                self.binder_data = {}
        
        # Ensure user section exists
        if self.usuario not in self.binder_data:
            self.binder_data[self.usuario] = {}
            
        user_data = self.binder_data[self.usuario]
        
        # Si no tiene estructura de folders, migrar datos existentes
        if "folders" not in user_data:
            # Comprobar si tenía modos directamente
            existing_cards = {
                "2x2": user_data.get("2x2", {}),
                "3x3": user_data.get("3x3", {}),
                "3x4": user_data.get("3x4", user_data.get("4x3", {})),
                "4x4": user_data.get("4x4", {})
            }
            user_data["folders"] = {
                "default": {
                    "name": "Mi Carpeta",
                    "color": "#ffeef2",
                    "design": "Clásico Rosa",
                    "mode": "3x3",
                    "cards": existing_cards
                }
            }
            self.save_binder_data()

    def save_binder_data(self):
        with open(BINDER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.binder_data, f, indent=4)
            
    def _get_current_cards_dict(self, mode=None) -> dict:
        folders = self.get_user_folders()
        folder = folders.setdefault(self.current_folder_id, {})
        cards_by_mode = folder.setdefault("cards", {})
        target_mode = mode if mode else self.current_mode
        return cards_by_mode.setdefault(target_mode, {})

    def get_card_at(self, page, slot, mode=None):
        cards_dict = self._get_current_cards_dict(mode)
        key = f"{page}_{slot}"
        return cards_dict.get(key)
        
    def set_card_at(self, page, slot, card_id):
        cards_dict = self._get_current_cards_dict(self.current_mode)
        key = f"{page}_{slot}"
        if card_id is None:
            if key in cards_dict:
                del cards_dict[key]
        else:
            cards_dict[key] = card_id
        self.save_binder_data()

    def change_mode(self, mode):
        if self.current_mode == mode:
            return
        
        # Respect global animation setting
        from MyQtApp.config import load_settings
        settings = load_settings()
        animaciones_activas = settings.get("animaciones", True)
        
        if not animaciones_activas:
            self.current_mode = mode
            # Update buttons styling
            for m, btn in self.mode_buttons.items():
                btn.setProperty("class", "pill selected" if m == mode else "pill")
                btn.style().unpolish(btn)
                btn.style().polish(btn)
            self.update_spread(direction=0)
        else:
            self.fade_zoom_transition(mode)

    def fade_zoom_transition(self, new_mode):
        current_spread = self.spread_stack.currentWidget()
        if not current_spread:
            self.current_mode = new_mode
            # Update buttons styling
            for m, btn in self.mode_buttons.items():
                btn.setProperty("class", "pill selected" if m == new_mode else "pill")
                btn.style().unpolish(btn)
                btn.style().polish(btn)
            self.update_spread(direction=0)
            return

        # Create new spread for the new mode
        new_spread, new_left, new_right = self.create_spread_widget(self.current_spread_index, mode=new_mode)
        self.spread_stack.addWidget(new_spread)
        
        # Determine current stack geometry
        width = self.spread_stack.width()
        height = self.spread_stack.height()
        if width <= 0 or height <= 0:
            width = 750
            height = 550
            
        normal_rect = current_spread.geometry()
        if normal_rect.width() <= 0:
            normal_rect = QRect(0, 0, width, height)
            
        # Old shrink target: slightly smaller
        shrink_rect = QRect(
            int(normal_rect.x() + normal_rect.width() * 0.05),
            int(normal_rect.y() + normal_rect.height() * 0.05),
            int(normal_rect.width() * 0.9),
            int(normal_rect.height() * 0.9)
        )
        
        # New start rect: start from 0.9 scale
        grow_start_rect = QRect(
            int(normal_rect.x() + normal_rect.width() * 0.05),
            int(normal_rect.y() + normal_rect.height() * 0.05),
            int(normal_rect.width() * 0.9),
            int(normal_rect.height() * 0.9)
        )
        
        new_spread.setGeometry(grow_start_rect)
        new_spread.show()
        
        # Disable buttons temporarily during transition
        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)
        for btn in self.mode_buttons.values():
            btn.setEnabled(False)
            
        # Set up opacity effects
        eff_old = QGraphicsOpacityEffect(current_spread)
        current_spread.setGraphicsEffect(eff_old)
        
        eff_new = QGraphicsOpacityEffect(new_spread)
        new_spread.setGraphicsEffect(eff_new)
        
        eff_old.setOpacity(1.0)
        eff_new.setOpacity(0.0)
        
        duration = 220
        
        # Create animations
        self.anim_opacity_old = QPropertyAnimation(eff_old, b"opacity", self)
        self.anim_opacity_old.setDuration(duration)
        self.anim_opacity_old.setStartValue(1.0)
        self.anim_opacity_old.setEndValue(0.0)
        self.anim_opacity_old.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.anim_opacity_new = QPropertyAnimation(eff_new, b"opacity", self)
        self.anim_opacity_new.setDuration(duration)
        self.anim_opacity_new.setStartValue(0.0)
        self.anim_opacity_new.setEndValue(1.0)
        self.anim_opacity_new.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.anim_geom_old = QPropertyAnimation(current_spread, b"geometry", self)
        self.anim_geom_old.setDuration(duration)
        self.anim_geom_old.setStartValue(normal_rect)
        self.anim_geom_old.setEndValue(shrink_rect)
        self.anim_geom_old.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.anim_geom_new = QPropertyAnimation(new_spread, b"geometry", self)
        self.anim_geom_new.setDuration(duration)
        self.anim_geom_new.setStartValue(grow_start_rect)
        self.anim_geom_new.setEndValue(normal_rect)
        self.anim_geom_new.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Start animations
        self.anim_opacity_old.start()
        self.anim_opacity_new.start()
        self.anim_geom_old.start()
        self.anim_geom_new.start()
        
        # Update references and state
        self.current_mode = new_mode
        self.page_left = new_left
        self.page_right = new_right
        
        def on_finished():
            self.spread_stack.setCurrentWidget(new_spread)
            self.spread_stack.removeWidget(current_spread)
            current_spread.deleteLater()
            
            # Reset geometry constraints to normal
            new_spread.setGeometry(normal_rect)
            
            # Remove graphics effects so normal rendering behaves correctly
            new_spread.setGraphicsEffect(None)
            
            # Re-enable controls
            self.btn_prev.setEnabled(self.current_spread_index > 0)
            self.btn_next.setEnabled(True)
            for btn in self.mode_buttons.values():
                btn.setEnabled(True)
                
            # Update mode buttons selected style
            for m, btn in self.mode_buttons.items():
                btn.setProperty("class", "pill selected" if m == new_mode else "pill")
                btn.style().unpolish(btn)
                btn.style().polish(btn)
                
        self.anim_opacity_new.finished.connect(on_finished)
        
    def create_spread_widget(self, spread_index, mode=None):
        spread_widget = QWidget()
        spread_layout = QHBoxLayout(spread_widget)
        spread_layout.setSpacing(40) # Gap between pages
        spread_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spread_layout.setContentsMargins(0, 0, 0, 0)
        
        p_idx_1 = spread_index * 2
        p_idx_2 = p_idx_1 + 1
        
        target_mode = mode if mode else self.current_mode
        cfg = BINDER_MODES[target_mode]
        
        page_left = BinderPage(
            p_idx_1, self,
            rows=cfg["rows"],
            cols=cfg["cols"],
            slot_w=cfg["slot_w"],
            slot_h=cfg["slot_h"],
            card_w=cfg["card_w"],
            card_h=cfg["card_h"]
        )
        page_right = BinderPage(
            p_idx_2, self,
            rows=cfg["rows"],
            cols=cfg["cols"],
            slot_w=cfg["slot_w"],
            slot_h=cfg["slot_h"],
            card_w=cfg["card_w"],
            card_h=cfg["card_h"]
        )
        
        # Populate slots
        self.populate_page(page_left, p_idx_1, target_mode)
        self.populate_page(page_right, p_idx_2, target_mode)
        
        spread_layout.addWidget(page_left)
        spread_layout.addWidget(page_right)
        
        return spread_widget, page_left, page_right

    def update_spread(self, direction=0):
        new_spread, new_left, new_right = self.create_spread_widget(self.current_spread_index)
        
        # UI controls update
        p_idx_1 = self.current_spread_index * 2
        p_idx_2 = p_idx_1 + 1
        self.lbl_pages.setText(f"{t('Página')} {p_idx_1 + 1} - {p_idx_2 + 1}")
        self.btn_prev.setEnabled(self.current_spread_index > 0)
        self.btn_next.setEnabled(True)
        
        # Respect global animation setting
        from MyQtApp.config import load_settings
        settings = load_settings()
        animaciones_activas = settings.get("animaciones", True)
        
        if direction == 0 or not animaciones_activas:
            # Clear old spreads
            while self.spread_stack.count() > 0:
                widget = self.spread_stack.widget(0)
                self.spread_stack.removeWidget(widget)
                widget.deleteLater()
                
            self.spread_stack.addWidget(new_spread)
            self.spread_stack.setCurrentWidget(new_spread)
            self.page_left = new_left
            self.page_right = new_right
        else:
            self.slide_transition(new_spread, direction, new_left, new_right)

    def slide_transition(self, new_spread, direction, new_left, new_right):
        current_spread = self.spread_stack.currentWidget()
        if not current_spread:
            self.spread_stack.addWidget(new_spread)
            self.spread_stack.setCurrentWidget(new_spread)
            self.page_left = new_left
            self.page_right = new_right
            return
            
        self.spread_stack.addWidget(new_spread)
        
        # Determine width of the stacked widget
        width = self.spread_stack.width()
        if width <= 0:
            width = 750 # Fallback width
            
        # Position the new spread offscreen
        new_spread.move(direction * width, 0)
        new_spread.show()
        
        # Disable buttons temporarily during animation to prevent rapid clicks
        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)
        
        # Update references immediately so drag-and-drop resolves to correct page
        self.page_left = new_left
        self.page_right = new_right
        
        # Create animations
        self.anim_old = QPropertyAnimation(current_spread, b"pos", self)
        self.anim_old.setDuration(220)
        self.anim_old.setStartValue(current_spread.pos())
        self.anim_old.setEndValue(QPoint(-direction * width, 0))
        self.anim_old.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.anim_new = QPropertyAnimation(new_spread, b"pos", self)
        self.anim_new.setDuration(220)
        self.anim_new.setStartValue(new_spread.pos())
        self.anim_new.setEndValue(QPoint(0, 0))
        self.anim_new.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Start animations
        self.anim_old.start()
        self.anim_new.start()
        
        def on_finished():
            self.spread_stack.setCurrentWidget(new_spread)
            self.spread_stack.removeWidget(current_spread)
            current_spread.deleteLater()
            
            # Re-enable pagination controls correctly
            self.btn_prev.setEnabled(self.current_spread_index > 0)
            self.btn_next.setEnabled(True)
            
        self.anim_new.finished.connect(on_finished)

    def populate_page(self, page_widget, page_idx, mode=None):
        session = SessionLocal()
        try:
            target_mode = mode if mode else self.current_mode
            cfg = BINDER_MODES[target_mode]
            slots_per_page = cfg["rows"] * cfg["cols"]
            for i in range(slots_per_page):
                card_info = self.get_card_at(page_idx, i, target_mode)
                slot = page_widget.get_slot(i)
                if card_info and slot:
                    card_id = None
                    card_lang = "en"
                    card_var = "Normal"
                    if isinstance(card_info, dict):
                        card_id = card_info.get("id_api")
                        card_lang = card_info.get("idioma", "en")
                        card_var = card_info.get("variante", "Normal")
                    elif isinstance(card_info, str):
                        if ":" in card_info:
                            card_id, card_lang = card_info.split(":", 1)
                        else:
                            card_id = card_info

                    if card_id:
                        carta = session.query(Cartas).filter(Cartas.id_api == card_id, Cartas.idioma == card_lang).first()
                        if not carta:
                            carta = session.query(Cartas).filter(Cartas.id_api == card_id).first()

                        if carta:
                            c_lang = carta.idioma or card_lang
                            nombre = carta.nombre
                            nombre_archivo = nombre.lower().replace(" ", "_")

                            pixmap = get_webp_pixmap(card_id, nombre, c_lang, size=(cfg["card_w"], cfg["card_h"]))
                            if not pixmap:
                                pixmap = get_pixmap_from_zip(nombre_archivo, size=(cfg["card_w"], cfg["card_h"]), id_api=card_id)
                            if not pixmap:
                                ruta_alt = os.path.join(IMAGES_DIR, f"{nombre_archivo}_{card_id}.webp")
                                if os.path.exists(ruta_alt):
                                    pixmap = QPixmap(ruta_alt)

                            if pixmap:
                                slot.set_card(card_id, nombre_archivo, pixmap, idioma=c_lang, variante=card_var)
        finally:
            session.close()

    def update_slot_variant(self, page, slot, nueva_variante):
        target_mode = self.current_mode
        if self.usuario not in self.binder_data:
            self.binder_data[self.usuario] = {}
        if target_mode not in self.binder_data[self.usuario]:
            self.binder_data[self.usuario][target_mode] = {}
        
        key = f"{page}_{slot}"
        existing = self.binder_data[self.usuario][target_mode].get(key)
        
        if isinstance(existing, dict):
            existing["variante"] = nueva_variante
            self.binder_data[self.usuario][target_mode][key] = existing
        elif isinstance(existing, str):
            self.binder_data[self.usuario][target_mode][key] = {
                "id_api": existing,
                "variante": nueva_variante
            }
        else:
            return

        self.save_binder_data()
        show_toast(f"Variante en Binder guardada: {nueva_variante}", "info")


    def handle_drop(self, page_idx, slot_idx, card_id, source_slot=None, nombre_archivo=None, idioma=None, variante="Normal"):
        if not idioma:
            idioma = "en"

        card_data_entry = {"id_api": card_id, "idioma": idioma, "variante": variante or "Normal"}

        # If the drag came from another slot in the binder
        if source_slot:
            try:
                src_page_str, src_slot_str = source_slot.split('_')
                src_page = int(src_page_str)
                src_slot = int(src_slot_str)
                
                # If target is different from source
                if src_page != page_idx or src_slot != slot_idx:
                    # Clear old slot in data
                    self.set_card_at(src_page, src_slot, None)
                    
                    # Clear old slot in UI (if it's on the currently visible pages)
                    src_page_widget = None
                    if src_page == self.current_spread_index * 2:
                        src_page_widget = self.page_left
                    elif src_page == self.current_spread_index * 2 + 1:
                        src_page_widget = self.page_right
                        
                    if src_page_widget:
                        slot = src_page_widget.get_slot(src_slot)
                        if slot:
                            slot.clear_card()
            except Exception as e:
                print(f"Error resolving source slot during move: {e}")

        # Update data
        self.set_card_at(page_idx, slot_idx, card_data_entry)
        
        # Find the specific slot widget
        target_page_widget = None
        if page_idx == self.current_spread_index * 2:
            target_page_widget = self.page_left
        elif page_idx == self.current_spread_index * 2 + 1:
            target_page_widget = self.page_right
            
        if target_page_widget:
            slot = target_page_widget.get_slot(slot_idx)
            if slot:
                cfg = BINDER_MODES[self.current_mode]
                session = SessionLocal()
                try:
                    carta = session.query(Cartas).filter(Cartas.id_api == card_id, Cartas.idioma == idioma).first()
                    if not carta:
                        carta = session.query(Cartas).filter(Cartas.id_api == card_id).first()

                    if carta:
                        n_archivo = carta.nombre.lower().replace(" ", "_")
                        c_lang = carta.idioma or idioma
                        pixmap = get_webp_pixmap(card_id, carta.nombre, c_lang, size=(cfg["card_w"], cfg["card_h"]))
                        if not pixmap:
                            pixmap = get_pixmap_from_zip(n_archivo, size=(cfg["card_w"], cfg["card_h"]), id_api=card_id)
                        if not pixmap:
                            ruta_alt = os.path.join(IMAGES_DIR, f"{n_archivo}_{card_id}.webp")
                            if os.path.exists(ruta_alt):
                                pixmap = QPixmap(ruta_alt)
                        slot.set_card(card_id, n_archivo, pixmap, idioma=c_lang, variante=variante)
                finally:
                    session.close()


    def prev_spread(self):
        if self.current_spread_index > 0:
            self.current_spread_index -= 1
            self.update_spread(direction=-1)
            
    def clear_binder(self):
        # Clear data for this user for the current mode in the current folder
        cards_dict = self._get_current_cards_dict(self.current_mode)
        cards_dict.clear()
        self.save_binder_data()
        self.update_spread(direction=0)
        
    def next_spread(self):
        self.current_spread_index += 1
        self.update_spread(direction=1)

    # Should be called if Inventory changes (e.g. from Index)
    def refresh_inventory(self):
        self.inventory.refresh()
