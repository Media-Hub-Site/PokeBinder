import json
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, 
    QGridLayout, QFrame, QPushButton, QApplication, QSizePolicy,
    QStackedWidget, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QMimeData, QPoint, QSize, QEasingCurve, QPropertyAnimation, QRect
from PyQt6.QtGui import QDrag, QPixmap, QCursor, QAction

from MyQtApp.config import ASSETS_DIR, IMAGES_DIR
from ..session import SessionLocal
from ..models import Cartas, UsuarioCarta
from ..app.getImgs import get_pixmap_from_zip

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
        self.setPixmap(pixmap)
        self.setScaledContents(True)
        self.setFixedSize(100, 140)  # Adjust size as needed
        self.setStyleSheet("border: 1px solid #ddd; border-radius: 5px;")
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Pass card ID and source info
        mime_data.setText(self.id_api)
        mime_data.setProperty("source", "inventory")
        mime_data.setProperty("nombre_archivo", self.nombre_archivo)
        drag.setMimeData(mime_data)

        # Set drag pixmap
        drag.setPixmap(self.pixmap().scaled(80, 112, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        drag.setHotSpot(event.pos())

        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)

class BinderSlot(QLabel):
    def __init__(self, page_index, slot_index, parent=None, binder_view=None, slot_w=120, slot_h=170, card_w=110, card_h=160):
        super().__init__(parent)
        self.page_index = page_index
        self.slot_index = slot_index
        self.binder_view = binder_view
        self.id_api = None
        self.nombre_archivo = None
        self.slot_w = slot_w
        self.slot_h = slot_h
        self.card_w = card_w
        self.card_h = card_h
        
        self.setFixedSize(slot_w, slot_h)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        self.update_style()

    def update_style(self):
        if self.id_api:
            self.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    border: 2px solid #f29ca4;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    background-color: white;
                    border: 2px dashed #f29ca4;
                    border-radius: 8px;
                }
            """)
            self.clear()

    def set_card(self, id_api, nombre_archivo, pixmap):
        self.id_api = id_api
        self.nombre_archivo = nombre_archivo
        if pixmap:
            self.setPixmap(pixmap.scaled(self.card_w, self.card_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.update_style()
        
    def clear_card(self):
        self.id_api = None
        self.nombre_archivo = None
        self.clear()
        self.update_style()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        card_id = event.mimeData().text()
        source = event.mimeData().property("source")
        source_slot = event.mimeData().property("source_slot")
        nombre_archivo = event.mimeData().property("nombre_archivo")
        
        if card_id:
            # Tell the main view to handle the drop (update logic and UI)
            if self.binder_view:
                self.binder_view.handle_drop(
                    self.page_index, self.slot_index, card_id, 
                    source_slot=source_slot, nombre_archivo=nombre_archivo
                )
            event.accept()
     
    # Allow dragging FROM the slot too
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.id_api:
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event):
        if not self.id_api:
            return
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.id_api)
        mime_data.setProperty("source", "binder")
        mime_data.setProperty("source_slot", f"{self.page_index}_{self.slot_index}")
        mime_data.setProperty("nombre_archivo", self.nombre_archivo)
        drag.setMimeData(mime_data)
        
        if self.pixmap():
            drag.setPixmap(self.pixmap().scaled(80, 112, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            drag.setHotSpot(event.pos()) # Roughly center?
        
        drag.exec(Qt.DropAction.CopyAction)


class InventorySidebar(QWidget):
    def __init__(self, usuario, parent=None):
        super().__init__(parent)
        self.usuario = usuario
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Search/Header
        self.header = QLabel("Mi Colección")
        self.header.setStyleSheet("font-weight: bold; color: #5a2a3a; font-size: 14px; margin-bottom: 5px;")
        layout.addWidget(self.header)
        
        # Scroll Area for cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background-color: #fff7f8; border: none;")
        
        self.container = QWidget()
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setSpacing(15)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        
        self.load_cards()
        
    def load_cards(self):
        session = SessionLocal()
        try:
            # Query distinct cards owned by user
            cartas = (
                session.query(Cartas.nombre, Cartas.id_api)
                .join(UsuarioCarta)
                .filter(UsuarioCarta.usuario_nombre == self.usuario)
                .group_by(Cartas.id_api) # distinct items
                .all()
            )
            
            # Clear existing
            for i in reversed(range(self.cards_layout.count())):
                self.cards_layout.itemAt(i).widget().deleteLater()
                
            for nombre, id_api in cartas:
                nombre_archivo = nombre.lower().replace(" ", "_")
                pixmap = get_pixmap_from_zip(nombre_archivo, size=(100, 140), id_api=id_api)
                
                if not pixmap:
                     # Fallback if needed, logic from Inventario.py
                     ruta_alt = os.path.join(IMAGES_DIR, f"{nombre_archivo}_{id_api}.webp")
                     if os.path.exists(ruta_alt):
                         pixmap = QPixmap(ruta_alt)

                if pixmap:
                    card_lbl = DraggableCardLabel(id_api, nombre_archivo, pixmap)
                    self.cards_layout.addWidget(card_lbl)
        finally:
            session.close()

    def refresh(self):
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
        
        # Header layout for Title and Mode Selector
        header_layout = QHBoxLayout()
        title = QLabel("Mi Carpeta Física")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #5a2a3a;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Mode Selector Buttons
        self.mode_buttons = {}
        mode_container = QWidget()
        mode_btn_layout = QHBoxLayout(mode_container)
        mode_btn_layout.setContentsMargins(0, 0, 0, 0)
        mode_btn_layout.setSpacing(6)
        
        for mode in ["2x2", "3x3", "3x4", "4x4"]:
            btn = QPushButton(mode)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("class", "pill selected" if mode == self.current_mode else "pill")
            btn.setFixedSize(65, 36)
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
        self.btn_prev = QPushButton("◀ Anterior")
        self.btn_next = QPushButton("Siguiente ▶")
        self.lbl_pages = QLabel("Páginas 1 - 2")
        
        for btn in [self.btn_prev, self.btn_next]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("class", "BinderNavBtn")
            
        self.btn_prev.clicked.connect(self.prev_spread)
        self.btn_next.clicked.connect(self.next_spread)
        
        controls_layout.addStretch()
        controls_layout.addWidget(self.btn_prev)
        controls_layout.addWidget(self.lbl_pages)
        controls_layout.addWidget(self.btn_next)
        controls_layout.addStretch()
        
        right_layout.addLayout(controls_layout)
        
        main_layout.addWidget(right_container)
        
        # Initialize pages
        self.update_spread(direction=0)
        
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
        
        # Migration: if user_data has a flat format (direct keys of page_slot mapped to card_ids)
        # instead of a dictionary of modes.
        has_flat_format = False
        for val in user_data.values():
            if not isinstance(val, dict):
                has_flat_format = True
                break
                
        if has_flat_format or not user_data:
            old_cards = {k: v for k, v in user_data.items() if isinstance(v, str)}
            self.binder_data[self.usuario] = {
                "2x2": {},
                "3x3": old_cards,
                "3x4": {},
                "4x4": {}
            }
            self.save_binder_data()
        else:
            # Rename legacy "4x3" mode to "3x4" if present
            if "4x3" in user_data:
                user_data["3x4"] = user_data.pop("4x3")
                self.save_binder_data()

            # Ensure all standard modes exist
            for mode in ["2x2", "3x3", "3x4", "4x4"]:
                if mode not in user_data:
                    user_data[mode] = {}
            
    def save_binder_data(self):
        with open(BINDER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.binder_data, f, indent=4)
            
    def get_card_at(self, page, slot, mode=None):
        target_mode = mode if mode else self.current_mode
        mode_data = self.binder_data[self.usuario].get(target_mode, {})
        key = f"{page}_{slot}"
        return mode_data.get(key)
        
    def set_card_at(self, page, slot, card_id):
        if self.current_mode not in self.binder_data[self.usuario]:
            self.binder_data[self.usuario][self.current_mode] = {}
        key = f"{page}_{slot}"
        if card_id is None:
            if key in self.binder_data[self.usuario][self.current_mode]:
                del self.binder_data[self.usuario][self.current_mode][key]
        else:
            self.binder_data[self.usuario][self.current_mode][key] = card_id
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
        
        duration = 350
        
        # Create animations
        self.anim_opacity_old = QPropertyAnimation(eff_old, b"opacity", self)
        self.anim_opacity_old.setDuration(duration)
        self.anim_opacity_old.setStartValue(1.0)
        self.anim_opacity_old.setEndValue(0.0)
        
        self.anim_opacity_new = QPropertyAnimation(eff_new, b"opacity", self)
        self.anim_opacity_new.setDuration(duration)
        self.anim_opacity_new.setStartValue(0.0)
        self.anim_opacity_new.setEndValue(1.0)
        
        self.anim_geom_old = QPropertyAnimation(current_spread, b"geometry", self)
        self.anim_geom_old.setDuration(duration)
        self.anim_geom_old.setStartValue(normal_rect)
        self.anim_geom_old.setEndValue(shrink_rect)
        self.anim_geom_old.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self.anim_geom_new = QPropertyAnimation(new_spread, b"geometry", self)
        self.anim_geom_new.setDuration(duration)
        self.anim_geom_new.setStartValue(grow_start_rect)
        self.anim_geom_new.setEndValue(normal_rect)
        self.anim_geom_new.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
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
        self.lbl_pages.setText(f"Páginas {p_idx_1 + 1} - {p_idx_2 + 1}")
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
        self.anim_old.setDuration(400)
        self.anim_old.setStartValue(current_spread.pos())
        self.anim_old.setEndValue(QPoint(-direction * width, 0))
        self.anim_old.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self.anim_new = QPropertyAnimation(new_spread, b"pos", self)
        self.anim_new.setDuration(400)
        self.anim_new.setStartValue(new_spread.pos())
        self.anim_new.setEndValue(QPoint(0, 0))
        self.anim_new.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
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
                card_id = self.get_card_at(page_idx, i, target_mode)
                slot = page_widget.get_slot(i)
                if card_id and slot:
                     # Fetch card name to get image
                     carta = session.query(Cartas).filter(Cartas.id_api == card_id).first()
                     if carta:
                          nombre_archivo = carta.nombre.lower().replace(" ", "_")
                          pixmap = get_pixmap_from_zip(nombre_archivo, size=(cfg["card_w"], cfg["card_h"]), id_api=card_id)
                          if not pixmap:
                              # fallback
                              ruta_alt = os.path.join(IMAGES_DIR, f"{nombre_archivo}_{card_id}.webp")
                              if os.path.exists(ruta_alt):
                                  pixmap = QPixmap(ruta_alt)
                          
                          if pixmap:
                              slot.set_card(card_id, nombre_archivo, pixmap)
        finally:
            session.close()

    def handle_drop(self, page_idx, slot_idx, card_id, source_slot=None, nombre_archivo=None):
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
        self.set_card_at(page_idx, slot_idx, card_id)
        
        # Find the specific slot widget
        target_page_widget = None
        if page_idx == self.current_spread_index * 2:
            target_page_widget = self.page_left
        elif page_idx == self.current_spread_index * 2 + 1:
            target_page_widget = self.page_right
            
        if target_page_widget:
            slot = target_page_widget.get_slot(slot_idx)
            if slot:
                if nombre_archivo:
                    cfg = BINDER_MODES[self.current_mode]
                    pixmap = get_pixmap_from_zip(nombre_archivo, size=(cfg["card_w"], cfg["card_h"]), id_api=card_id)
                    if not pixmap:
                        ruta_alt = os.path.join(IMAGES_DIR, f"{nombre_archivo}_{card_id}.webp")
                        if os.path.exists(ruta_alt):
                            pixmap = QPixmap(ruta_alt)
                    slot.set_card(card_id, nombre_archivo, pixmap)
                else:
                    # Fallback database query with correct session close
                    session = SessionLocal()
                    try:
                        carta = session.query(Cartas).filter(Cartas.id_api == card_id).first()
                        if carta:
                            n_archivo = carta.nombre.lower().replace(" ", "_")
                            cfg = BINDER_MODES[self.current_mode]
                            pixmap = get_pixmap_from_zip(n_archivo, size=(cfg["card_w"], cfg["card_h"]), id_api=card_id)
                            if not pixmap:
                                ruta_alt = os.path.join(IMAGES_DIR, f"{n_archivo}_{card_id}.webp")
                                if os.path.exists(ruta_alt):
                                    pixmap = QPixmap(ruta_alt)
                            slot.set_card(card_id, n_archivo, pixmap)
                    finally:
                        session.close()

    def prev_spread(self):
        if self.current_spread_index > 0:
            self.current_spread_index -= 1
            self.update_spread(direction=-1)
            
    def clear_binder(self):
        # Clear data for this user for the current mode
        if self.usuario in self.binder_data:
            self.binder_data[self.usuario][self.current_mode] = {}
        self.save_binder_data()
        self.update_spread(direction=0)
        
    def next_spread(self):
        self.current_spread_index += 1
        self.update_spread(direction=1)

    # Should be called if Inventory changes (e.g. from Index)
    def refresh_inventory(self):
        self.inventory.refresh()
