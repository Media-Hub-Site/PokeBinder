import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QScrollArea, QFrame, QSpinBox,
    QInputDialog, QMessageBox, QDialog
)
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal

from MyQtApp.session import SessionLocal
from MyQtApp.models import Mazo, MazoCarta, Cartas
from MyQtApp.app.getImgs import get_webp_pixmap, get_pixmap_from_zip
from MyQtApp.i18n import t, language_manager
from MyQtApp.ui.toast import show_toast
from MyQtApp.ui.PrintView import ImportDecklistDialog, PrintCardItemWidget


class DeckCardRowWidget(QFrame):
    """Fila para una carta en la lista del editor de mazo."""
    quantity_changed = pyqtSignal()
    removed = pyqtSignal(str) # card_key

    def __init__(self, card_data, quantity=1, parent=None):
        super().__init__(parent)
        self.card_data = card_data
        self.card_key = f"{card_data.get('id_api')}:{card_data.get('idioma', 'es')}"

        self.setStyleSheet("""
            DeckCardRowWidget {
                background-color: rgba(15, 23, 42, 0.8);
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 8px;
                padding: 4px;
            }
            DeckCardRowWidget:hover { border-color: #38bdf8; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)

        self.lbl_img = QLabel(self)
        self.lbl_img.setFixedSize(40, 56)
        self.lbl_img.setScaledContents(True)

        lang = card_data.get("idioma", "es")
        id_api = card_data.get("id_api")
        nombre = card_data.get("nombre")

        pix = get_webp_pixmap(id_api, nombre, lang, size=(40, 56))
        if not pix:
            pix = get_pixmap_from_zip(nombre, size=(40, 56), id_api=id_api)
        if pix:
            self.lbl_img.setPixmap(pix)
        else:
            self.lbl_img.setText("🎴")
            self.lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.lbl_img)

        info_vbox = QVBoxLayout()
        info_vbox.setSpacing(2)
        lbl_n = QLabel(nombre or "Carta", self)
        lbl_n.setStyleSheet("font-weight: bold; font-size: 12px; color: #f8fafc;")
        lbl_s = QLabel(f"ID: {id_api} | {card_data.get('edition', '')}", self)
        lbl_s.setStyleSheet("font-size: 10px; color: #94a3b8;")
        info_vbox.addWidget(lbl_n)
        info_vbox.addWidget(lbl_s)
        layout.addLayout(info_vbox, stretch=1)

        # Cantidad
        self.spin_qty = QSpinBox(self)
        self.spin_qty.setRange(1, 99)
        self.spin_qty.setValue(quantity)
        self.spin_qty.setFixedSize(48, 26)
        self.spin_qty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_qty.setStyleSheet("""
            QSpinBox {
                background-color: #0f172a; color: #38bdf8; font-weight: bold;
                border: 1px solid rgba(56, 189, 248, 0.4); border-radius: 4px;
            }
        """)
        self.spin_qty.valueChanged.connect(lambda _: self.quantity_changed.emit())
        layout.addWidget(self.spin_qty)

        btn_del = QPushButton("❌", self)
        btn_del.setFixedSize(26, 26)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 4px;
            }
            QPushButton:hover { background: rgba(239, 68, 68, 0.4); }
        """)
        btn_del.clicked.connect(lambda: self.removed.emit(self.card_key))
        layout.addWidget(btn_del)

    def get_quantity(self):
        return self.spin_qty.value()


class MazosView(QWidget):
    """Sección de Gestión y Creación de Mazos."""
    def __init__(self, usuario, parent=None):
        super().__init__(parent)
        self.usuario = usuario
        self.session = SessionLocal()

        self.mazo_actual = None # Mazo ORM actual seleccionado
        self.card_rows = {}    # card_key -> DeckCardRowWidget

        self.init_ui()
        self.cargar_mazos()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # ── Columna Izquierda: Mis Mazos ──
        left_panel = QWidget(self)
        left_panel.setFixedWidth(280)
        left_vbox = QVBoxLayout(left_panel)
        left_vbox.setContentsMargins(0, 0, 0, 0)
        left_vbox.setSpacing(10)

        lbl_title = QLabel("🃏 " + t("Mis Mazos"), self)
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #38bdf8;")
        left_vbox.addWidget(lbl_title)

        btn_nuevo_mazo = QPushButton("➕ " + t("Nuevo Mazo"), self)
        btn_nuevo_mazo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nuevo_mazo.setStyleSheet("""
            QPushButton {
                background-color: #0284c7; color: white; font-weight: bold;
                border-radius: 8px; padding: 10px; font-size: 13px;
            }
            QPushButton:hover { background-color: #0369a1; }
        """)
        btn_nuevo_mazo.clicked.connect(self.crear_nuevo_mazo)
        left_vbox.addWidget(btn_nuevo_mazo)

        self.list_mazos = QListWidget(self)
        self.list_mazos.setStyleSheet("""
            QListWidget {
                background-color: rgba(15, 23, 42, 0.7);
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 10px;
                color: #f8fafc;
                padding: 6px;
            }
            QListWidget::item {
                padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); border-radius: 6px;
            }
            QListWidget::item:hover { background-color: rgba(56, 189, 248, 0.15); }
            QListWidget::item:selected { background-color: #0284c7; color: white; font-weight: bold; }
        """)
        self.list_mazos.itemClicked.connect(self.on_mazo_selected)
        left_vbox.addWidget(self.list_mazos)

        # Botones de acción del mazo seleccionado
        row_actions = QHBoxLayout()
        btn_renombrar = QPushButton("✏️ " + t("Renombrar"), self)
        btn_renombrar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_renombrar.setStyleSheet("background: #334155; color: white; border-radius: 6px; padding: 6px;")
        btn_renombrar.clicked.connect(self.renombrar_mazo)

        btn_eliminar = QPushButton("🗑️ " + t("Eliminar"), self)
        btn_eliminar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eliminar.setStyleSheet("background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 6px; padding: 6px;")
        btn_eliminar.clicked.connect(self.eliminar_mazo)

        row_actions.addWidget(btn_renombrar)
        row_actions.addWidget(btn_eliminar)
        left_vbox.addLayout(row_actions)

        main_layout.addWidget(left_panel)

        # ── Columna Derecha: Editor del Mazo ──
        right_panel = QWidget(self)
        right_vbox = QVBoxLayout(right_panel)
        right_vbox.setContentsMargins(0, 0, 0, 0)
        right_vbox.setSpacing(10)

        # Header del Mazo activo
        header_box = QHBoxLayout()
        self.lbl_mazo_nombre = QLabel(t("Selecciona un mazo"), self)
        self.lbl_mazo_nombre.setStyleSheet("font-size: 18px; font-weight: bold; color: #f8fafc;")

        self.lbl_card_count = QLabel("0 / 60 cartas", self)
        self.lbl_card_count.setStyleSheet("font-size: 14px; font-weight: bold; color: #f59e0b;")

        header_box.addWidget(self.lbl_mazo_nombre)
        header_box.addStretch()
        header_box.addWidget(self.lbl_card_count)
        right_vbox.addLayout(header_box)

        # Fila de Búsqueda para agregar cartas al mazo + Importar
        row_search = QHBoxLayout()
        self.input_card_search = QLineEdit(self)
        self.input_card_search.setPlaceholderText("🔍 " + t("Buscar en mi colección..."))
        self.input_card_search.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a; color: white; border: 1px solid #334155; border-radius: 6px; padding: 8px;
            }
            QLineEdit:focus { border-color: #38bdf8; }
        """)
        self.input_card_search.textChanged.connect(self.on_card_search_text_changed)
        row_search.addWidget(self.input_card_search, stretch=1)

        btn_import = QPushButton("📋 " + t("Importar Mazo"), self)
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import.setStyleSheet("""
            QPushButton {
                background-color: #0284c7; color: white; font-weight: bold; border-radius: 6px; padding: 8px 12px;
            }
            QPushButton:hover { background-color: #0369a1; }
        """)
        btn_import.clicked.connect(self.importar_mazo_texto)
        row_search.addWidget(btn_import)

        right_vbox.addLayout(row_search)

        # Lista emergente de sugerencias de cartas
        self.list_card_suggestions = QListWidget(self)
        self.list_card_suggestions.setMaximumHeight(130)
        self.list_card_suggestions.hide()
        self.list_card_suggestions.setStyleSheet("""
            QListWidget {
                background-color: #0f172a; color: #f8fafc; border: 1px solid #38bdf8; border-radius: 6px;
            }
            QListWidget::item:hover { background-color: #1e293b; color: #38bdf8; }
            QListWidget::item:selected { background-color: #0284c7; color: white; }
        """)
        self.list_card_suggestions.itemClicked.connect(self.on_suggestion_clicked)
        right_vbox.addWidget(self.list_card_suggestions)

        # Scroll Area con las cartas del mazo
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea {
                background-color: rgba(15, 23, 42, 0.5);
                border: 1px solid rgba(56, 189, 248, 0.2);
                border-radius: 10px;
            }
        """)

        self.cards_container = QWidget()
        self.cards_vbox = QVBoxLayout(self.cards_container)
        self.cards_vbox.setContentsMargins(10, 10, 10, 10)
        self.cards_vbox.setSpacing(6)
        self.cards_vbox.addStretch()

        self.scroll.setWidget(self.cards_container)
        right_vbox.addWidget(self.scroll)

        # Botón para Guardar Mazo
        self.btn_guardar = QPushButton("💾 " + t("Guardar Mazo"), self)
        self.btn_guardar.setFixedHeight(40)
        self.btn_guardar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_guardar.setStyleSheet("""
            QPushButton {
                background-color: #10b981; color: white; font-weight: bold; font-size: 14px; border-radius: 8px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        self.btn_guardar.clicked.connect(self.guardar_mazo_actual)
        right_vbox.addWidget(self.btn_guardar)

        main_layout.addWidget(right_panel, stretch=1)

    def cargar_mazos(self):
        self.list_mazos.clear()
        mazos = self.session.query(Mazo).filter(Mazo.usuario_nombre == self.usuario).all()

        for m in mazos:
            total_qty = sum(mc.cantidad for mc in m.cartas)
            item = QListWidgetItem(f"🃏 {m.nombre} ({total_qty} cartas)")
            item.setData(Qt.ItemDataRole.UserRole, m.id)
            self.list_mazos.addItem(item)

        if mazos and not self.mazo_actual:
            self.list_mazos.setCurrentRow(0)
            self.on_mazo_selected(self.list_mazos.item(0))

    def crear_nuevo_mazo(self):
        nombre, ok = QInputDialog.getText(self, t("Nuevo Mazo"), "Ingresa el nombre del mazo:")
        if ok and nombre.strip():
            nuevo = Mazo(usuario_nombre=self.usuario, nombre=nombre.strip())
            self.session.add(nuevo)
            self.session.commit()
            self.cargar_mazos()

            # Seleccionar el recién creado
            for i in range(self.list_mazos.count()):
                item = self.list_mazos.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == nuevo.id:
                    self.list_mazos.setCurrentItem(item)
                    self.on_mazo_selected(item)
                    break
            show_toast("✔️ Mazo creado con éxito.", "success", 2500)

    def renombrar_mazo(self):
        if not self.mazo_actual:
            return
        nuevo_nombre, ok = QInputDialog.getText(self, t("Renombrar Mazo"), "Nuevo nombre:", text=self.mazo_actual.nombre)
        if ok and nuevo_nombre.strip():
            self.mazo_actual.nombre = nuevo_nombre.strip()
            self.session.commit()
            self.cargar_mazos()
            self.lbl_mazo_nombre.setText(self.mazo_actual.nombre)
            show_toast("✔️ Nombre de mazo actualizado.", "success", 2000)

    def eliminar_mazo(self):
        if not self.mazo_actual:
            return
        resp = QMessageBox.question(self, t("Eliminar Mazo"), f"¿Seguro que deseas eliminar '{self.mazo_actual.nombre}'?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.Yes:
            self.session.delete(self.mazo_actual)
            self.session.commit()
            self.mazo_actual = None
            self.limpiar_editor()
            self.cargar_mazos()
            show_toast("✔️ Mazo eliminado.", "info", 2000)

    def on_mazo_selected(self, item):
        if not item:
            return
        mazo_id = item.data(Qt.ItemDataRole.UserRole)
        self.mazo_actual = self.session.query(Mazo).filter(Mazo.id == mazo_id).first()

        if self.mazo_actual:
            self.lbl_mazo_nombre.setText(self.mazo_actual.nombre)
            self.cargar_cartas_de_mazo(self.mazo_actual)

    def limpiar_editor(self):
        for widget in list(self.card_rows.values()):
            self.cards_vbox.removeWidget(widget)
            widget.deleteLater()
        self.card_rows.clear()
        self.lbl_mazo_nombre.setText(t("Selecciona un mazo"))
        self.lbl_card_count.setText("0 / 60 cartas")

    def cargar_cartas_de_mazo(self, mazo):
        self.limpiar_editor()
        self.lbl_mazo_nombre.setText(mazo.nombre)

        for mc in mazo.cartas:
            data = {
                "id_api": mc.id_api,
                "nombre": mc.nombre_carta,
                "idioma": mc.idioma,
                "edition": mc.edition or ""
            }
            self.agregar_carta_row(data, quantity=mc.cantidad)

        self.actualizar_conteo()

    def agregar_carta_row(self, card_data, quantity=1):
        card_key = f"{card_data.get('id_api')}:{card_data.get('idioma', 'es')}"

        if card_key in self.card_rows:
            widget = self.card_rows[card_key]
            widget.spin_qty.setValue(widget.spin_qty.value() + quantity)
        else:
            widget = DeckCardRowWidget(card_data, quantity=quantity, parent=self)
            widget.quantity_changed.connect(self.actualizar_conteo)
            widget.removed.connect(self.remover_carta_row)

            count = self.cards_vbox.count()
            self.cards_vbox.insertWidget(max(0, count - 1), widget)
            self.card_rows[card_key] = widget

        self.actualizar_conteo()

    def remover_carta_row(self, card_key):
        if card_key in self.card_rows:
            widget = self.card_rows.pop(card_key)
            self.cards_vbox.removeWidget(widget)
            widget.deleteLater()
            self.actualizar_conteo()

    def actualizar_conteo(self):
        total = sum(w.get_quantity() for w in self.card_rows.values())
        self.lbl_card_count.setText(f"{total} / 60 cartas")
        if total == 60:
            self.lbl_card_count.setStyleSheet("font-size: 14px; font-weight: bold; color: #10b981;") # verde
        else:
            self.lbl_card_count.setStyleSheet("font-size: 14px; font-weight: bold; color: #f59e0b;") # naranja

    def on_card_search_text_changed(self, text):
        text = text.strip()
        if len(text) < 2:
            self.list_card_suggestions.hide()
            return

        from MyQtApp.models import UsuarioCarta

        # Buscar únicamente cartas presentes en la colección del usuario
        resultados = self.session.query(Cartas)\
            .join(UsuarioCarta, (Cartas.id_api == UsuarioCarta.carta_id) & (Cartas.idioma == UsuarioCarta.idioma))\
            .filter(UsuarioCarta.usuario_nombre == self.usuario)\
            .filter(Cartas.nombre.ilike(f"%{text}%"))\
            .limit(10).all()

        if not resultados:
            # Si no hay coincidencia exacta con idioma, probar por id_api general en la colección
            resultados = self.session.query(Cartas)\
                .join(UsuarioCarta, Cartas.id_api == UsuarioCarta.carta_id)\
                .filter(UsuarioCarta.usuario_nombre == self.usuario)\
                .filter(Cartas.nombre.ilike(f"%{text}%"))\
                .limit(10).all()

        if not resultados:
            self.list_card_suggestions.clear()
            item = QListWidgetItem("⚠️ No tienes esta carta en tu colección")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_card_suggestions.addItem(item)
            self.list_card_suggestions.show()
            return

        self.list_card_suggestions.clear()
        for c in resultados:
            item_text = f"📦 {c.nombre} ({c.edition or c.id_api}) [{c.idioma or 'es'}]"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, {
                "id_api": c.id_api,
                "nombre": c.nombre,
                "idioma": c.idioma or "es",
                "edition": c.edition or ""
            })
            self.list_card_suggestions.addItem(item)

        self.list_card_suggestions.show()

    def on_suggestion_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data and self.mazo_actual:
            self.agregar_carta_row(data, quantity=1)
        self.input_card_search.clear()
        self.list_card_suggestions.hide()

    def importar_mazo_texto(self):
        if not self.mazo_actual:
            QMessageBox.warning(self, t("Error"), "Debes seleccionar o crear un mazo primero.")
            return

        dialog = ImportDecklistDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            texto = dialog.get_text()
            if not texto:
                return

            lineas = texto.splitlines()
            agregadas = 0

            for linea in lineas:
                linea = linea.strip()
                if not linea or linea.startswith("#"):
                    continue

                match = re.match(r"^(\d+)\s+(.+)$", linea)
                if match:
                    qty = int(match.group(1))
                    card_search = match.group(2).strip()
                else:
                    qty = 1
                    card_search = linea

                from MyQtApp.models import UsuarioCarta

                # Probar primero en la colección del usuario
                carta = self.session.query(Cartas)\
                    .join(UsuarioCarta, (Cartas.id_api == UsuarioCarta.carta_id) & (Cartas.idioma == UsuarioCarta.idioma))\
                    .filter(UsuarioCarta.usuario_nombre == self.usuario)\
                    .filter(Cartas.nombre.ilike(f"%{card_search}%")).first()

                if not carta:
                    # Probar catálogo global
                    carta = self.session.query(Cartas).filter(Cartas.nombre.ilike(f"%{card_search}%")).first()
                if not carta:
                    first_word = card_search.split()[0]
                    carta = self.session.query(Cartas).filter(Cartas.nombre.ilike(f"%{first_word}%")).first()

                if carta:
                    self.agregar_carta_row({
                        "id_api": carta.id_api,
                        "nombre": carta.nombre,
                        "idioma": carta.idioma or "es",
                        "edition": carta.edition or ""
                    }, quantity=qty)
                    agregadas += qty

            if agregadas > 0:
                show_toast(f"✔️ Se importaron {agregadas} cartas al mazo.", "success", 2500)
            else:
                QMessageBox.warning(self, "Importar Mazo", "No se encontraron coincidencias para la lista.")

    def guardar_mazo_actual(self):
        if not self.mazo_actual:
            return

        try:
            # Borrar cartas antiguas y reinsertar
            self.session.query(MazoCarta).filter(MazoCarta.mazo_id == self.mazo_actual.id).delete()

            for widget in self.card_rows.values():
                d = widget.card_data
                mc = MazoCarta(
                    mazo_id=self.mazo_actual.id,
                    id_api=d.get("id_api"),
                    nombre_carta=d.get("nombre"),
                    cantidad=widget.get_quantity(),
                    idioma=d.get("idioma", "es"),
                    edition=d.get("edition", "")
                )
                self.session.add(mc)

            self.session.commit()
            self.cargar_mazos()
            show_toast("✔️ Mazo guardado correctamente.", "success", 2500)
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Error guardando mazo: {e}")
