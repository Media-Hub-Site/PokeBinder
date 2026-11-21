from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QScrollArea, QGridLayout,
    QHBoxLayout, QLineEdit, QComboBox, QPushButton, QGraphicsOpacityEffect,
    QSizePolicy, QDialog, QInputDialog, QMessageBox, QFrame
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QUrl, QEasingCurve
from PyQt6.QtMultimedia import QSoundEffect
import os

from ..session import SessionLocal
from ..models import Cartas, UsuarioCarta
from ..app.getImgs import (
    get_pixmap_from_zip, get_webp_pixmap, get_card_placeholder_pixmap,
    CardImageLoaderManager
)
from MyQtApp.ui.CardWidget import ClickableLabel, CardItemWidget, VariantLegendBar
from MyQtApp.ui.toast import show_toast
from sqlalchemy import func, and_
from MyQtApp.config import SOUNDS_DIR
from MyQtApp.i18n import t, language_manager


class GaleriaCartasInventario(QWidget):
    CARTAS_POR_PAGINA = 30

    def __init__(self, path_imagenes, nombre_usuario):
        super().__init__()
        self.nombre_usuario = nombre_usuario
        self.path_imagenes = path_imagenes
        self.session = SessionLocal()
        self.labels_por_id = {}
        self.card_widgets_por_key = {}
        self._current_card_size = (120, 170)
        self.cartas_seleccionadas = set()
        self.carpeta_activa = None
        self.current_page = 0
        self.total_cartas = 0

        self.image_loader = CardImageLoaderManager(max_threads=6, parent=self)
        self.image_loader.image_ready.connect(self._on_async_image_ready)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        header_vbox = QVBoxLayout()
        header_vbox.setSpacing(8)

        row1 = QHBoxLayout()
        row1.setSpacing(10)

        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText(t("BuscadorPlaceholder"))
        self.buscador.setProperty("class", "SearchInput")
        row1.addWidget(self.buscador)

        self.timer_busqueda = QTimer()
        self.timer_busqueda.setSingleShot(True)
        self.timer_busqueda.timeout.connect(self.reset_page_and_actualizar)
        self.buscador.textChanged.connect(self.on_text_changed)

        self.btn_limpiar = QPushButton(t("Limpiar Filtros"))
        self.btn_limpiar.setProperty("class", "CleanBtn")
        self.btn_limpiar.clicked.connect(self.limpiar_filtros)
        row1.addWidget(self.btn_limpiar)

        self.lbl_valor_total = QLabel(f"{t('Valor Inventario')} $0.00 USD")
        self.lbl_valor_total.setProperty("class", "ValorTotalLabel")
        row1.addWidget(self.lbl_valor_total)

        self.btn_sync_precios = QPushButton(t("Precios Real-Time"))
        self.btn_sync_precios.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sync_precios.setProperty("class", "SyncBtn")
        self.btn_sync_precios.clicked.connect(self.iniciar_sincronizacion_precios)
        row1.addWidget(self.btn_sync_precios)

        header_vbox.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(6)

        self.filtros = {}
        campos = {
            "Rareza": "rarity",
            "Tipo": "type",
            "Edición": "edition",
            "Etapa": "stage",
            "Entrenador": "trainer",
            "Especial": "especial_type"
        }

        for etiqueta, columna in campos.items():
            combo = QComboBox()
            combo.addItem(f"{t(etiqueta)}: {t('Todos')}")
            combo.setProperty("class", "FilterCombo")
            combo.currentIndexChanged.connect(self.reset_page_and_actualizar)
            self.filtros[columna] = combo
            row2.addWidget(combo, stretch=1)

        # Filtro de Idioma
        self.combo_idioma = QComboBox()
        self.combo_idioma.setProperty("class", "FilterCombo")
        self.combo_idioma.addItem(f"{t('Idioma')}: {t('Todos')}", None)
        self.combo_idioma.addItem("Español", "es")
        self.combo_idioma.addItem("English", "en")
        self.combo_idioma.addItem("日本語", "ja")
        self.combo_idioma.addItem("Français", "fr")
        self.combo_idioma.addItem("Português", "pt")
        self.combo_idioma.addItem("繁體中文", "zh")
        self.combo_idioma.currentIndexChanged.connect(self.reset_page_and_actualizar)
        row2.addWidget(self.combo_idioma, stretch=1)

        header_vbox.addLayout(row2)

        # Barra dedicada y vistosa de Carpetas de Colección (Issue #12 y #15, sin emojis)
        self.carpetas_bar = QFrame()
        self.carpetas_bar.setObjectName("CarpetasBar")
        self.carpetas_bar.setStyleSheet("""
            QFrame#CarpetasBar {
                background-color: #ffeef2;
                border: 2px solid #f3c8d1;
                border-radius: 12px;
            }
        """)
        carpetas_bar_layout = QHBoxLayout(self.carpetas_bar)
        carpetas_bar_layout.setContentsMargins(12, 7, 12, 7)
        carpetas_bar_layout.setSpacing(8)

        self.lbl_carpetas_titulo = QLabel(t("Carpetas"))
        self.lbl_carpetas_titulo.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #5a2a3a; border: none; background: transparent;"
        )
        carpetas_bar_layout.addWidget(self.lbl_carpetas_titulo)

        # Contenedor horizontal desplazable de pastillas de carpetas
        self.carpetas_scroll = QScrollArea()
        self.carpetas_scroll.setWidgetResizable(True)
        self.carpetas_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.carpetas_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.carpetas_scroll.setFixedHeight(36)
        self.carpetas_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.carpetas_pills_widget = QWidget()
        self.carpetas_pills_widget.setStyleSheet("background: transparent;")
        self.carpetas_pills_layout = QHBoxLayout(self.carpetas_pills_widget)
        self.carpetas_pills_layout.setContentsMargins(0, 2, 0, 2)
        self.carpetas_pills_layout.setSpacing(6)
        self.carpetas_scroll.setWidget(self.carpetas_pills_widget)
        carpetas_bar_layout.addWidget(self.carpetas_scroll, stretch=1)

        self.btn_nueva_cat = QPushButton(f"+ {t('Nueva Carpeta')}")
        self.btn_nueva_cat.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_nueva_cat.setFixedHeight(32)
        self.btn_nueva_cat.setStyleSheet("""
            QPushButton {
                background-color: #f7a8b8;
                color: #ffffff;
                font-weight: 700;
                font-size: 13px;
                border: 2px solid #f29ca4;
                border-radius: 10px;
                padding: 4px 16px;
            }
            QPushButton:hover {
                background-color: #f56b7b;
                border-color: #f5475c;
            }
            QPushButton:pressed {
                background-color: #d44854;
            }
        """)
        self.btn_nueva_cat.clicked.connect(self.abrir_creador_categorias)
        carpetas_bar_layout.addWidget(self.btn_nueva_cat)

        header_vbox.addWidget(self.carpetas_bar)
        self.main_layout.addLayout(header_vbox)

        self.scroll = QScrollArea()


        self.scroll.setWidgetResizable(True)
        self.scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        self.container = QWidget()
        self.container.setObjectName("InventarioContainer")
        self.grid = QGridLayout(self.container)
        self.scroll.setWidget(self.container)
        self.main_layout.addWidget(self.scroll)

        paginacion_layout = QHBoxLayout()
        self.btn_anterior = QPushButton(t("Anterior"))
        self.btn_anterior.setProperty("class", "PaginationBtn")
        self.btn_siguiente = QPushButton(t("Siguiente"))
        self.btn_siguiente.setProperty("class", "PaginationBtn")
        self.lbl_pagina = QLabel("")
        self.lbl_pagina.setProperty("class", "PaginationLabel")
        self.lbl_pagina.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_anterior.clicked.connect(self.pagina_anterior)
        self.btn_siguiente.clicked.connect(self.pagina_siguiente)
        paginacion_layout.addWidget(self.btn_anterior)
        paginacion_layout.addWidget(self.lbl_pagina)
        paginacion_layout.addWidget(self.btn_siguiente)
        self.main_layout.addLayout(paginacion_layout)

        self.sonido_pagina = QSoundEffect()
        self.sonido_pagina.setSource(QUrl.fromLocalFile(os.path.join(SOUNDS_DIR, "paginas.wav")))
        self.sonido_pagina.setVolume(0.5)

        self.cargar_filtros()
        self.actualizar_total_cartas()
        self.actualizar_valor_total()
        self.actualizar_galeria()
        language_manager.language_changed.connect(self.retranslate_ui)


    # ✅ SQLAlchemy: cargar combos
    def cargar_filtros(self):
        for columna, combo in self.filtros.items():
            valores = (
                self.session.query(getattr(Cartas, columna))
                .filter(getattr(Cartas, columna).isnot(None))
                .distinct()
                .all()
            )
            valores = sorted(v[0] for v in valores if v[0])
            for val in valores:
                combo.addItem(val)

        self.cargar_categorias_combo()

    def cargar_categorias_combo(self):
        """Refresca las pastillas interactivas de carpetas de la colección."""
        from MyQtApp.app.db_services import obtener_categorias_usuario
        cats = obtener_categorias_usuario(self.nombre_usuario)
        if self.carpeta_activa and self.carpeta_activa not in cats:
            self.carpeta_activa = None

        while self.carpetas_pills_layout.count():
            item = self.carpetas_pills_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        def _make_pill(label_text, cat_value):
            btn = QPushButton(label_text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(28)
            is_active = (self.carpeta_activa == cat_value)
            if is_active:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f56b7b;
                        color: #ffffff;
                        font-weight: 700;
                        font-size: 12px;
                        border: 1.5px solid #e05263;
                        border-radius: 12px;
                        padding: 2px 14px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ffffff;
                        color: #5a2a3a;
                        font-weight: 600;
                        font-size: 12px;
                        border: 1.5px solid #f2b8c3;
                        border-radius: 12px;
                        padding: 2px 14px;
                    }
                    QPushButton:hover {
                        background-color: #ffdfe6;
                        border-color: #f56b7b;
                    }
                """)
            btn.clicked.connect(lambda ch, val=cat_value: self._seleccionar_carpeta_pill(val))
            return btn

        self.carpetas_pills_layout.addWidget(_make_pill(t("Todas"), None))
        for cat in cats:
            self.carpetas_pills_layout.addWidget(_make_pill(cat, cat))
        self.carpetas_pills_layout.addStretch()

    def _seleccionar_carpeta_pill(self, cat_value):
        if self.carpeta_activa == cat_value:
            return
        self.carpeta_activa = cat_value
        self.cargar_categorias_combo()
        self.reset_page_and_actualizar()

    def abrir_creador_categorias(self):
        from MyQtApp.app.db_services import obtener_categorias_usuario, crear_categoria_usuario, eliminar_categoria_usuario
        dlg = QDialog(self)
        dlg.setWindowTitle(t("Carpetas de Colección"))
        dlg.setFixedSize(400, 340)
        dlg.setStyleSheet("""
            QDialog {
                background-color: #fff5f7;
            }
            QLabel {
                font-weight: 600;
                color: #5a2a3a;
                font-size: 13px;
            }
            QLineEdit, QComboBox {
                border: 2px solid #f7a8b8;
                border-radius: 10px;
                padding: 7px 10px;
                background-color: #ffffff;
                color: #5a2a3a;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #f56b7b;
            }
        """)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(10)

        lbl_head = QLabel(t("Crear nueva carpeta"))
        lbl_head.setStyleSheet("font-size: 15px; font-weight: 700; color: #5a2a3a;")
        layout.addWidget(lbl_head)

        txt_nueva = QLineEdit()
        txt_nueva.setPlaceholderText(t("Nombre de carpeta (ej: Favoritas, Charizards...)"))
        layout.addWidget(txt_nueva)

        btn_crear = QPushButton(t("Crear Carpeta"))
        btn_crear.setFixedHeight(36)
        btn_crear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_crear.setStyleSheet("""
            QPushButton {
                background-color: #f7a8b8;
                color: #ffffff;
                font-weight: 700;
                font-size: 13px;
                border: 2px solid #f29ca4;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #f56b7b;
                border-color: #f5475c;
            }
        """)
        layout.addWidget(btn_crear)

        layout.addSpacing(8)
        layout.addWidget(QLabel(t("Carpetas existentes")))
        combo_existentes = QComboBox()
        layout.addWidget(combo_existentes)

        btn_eliminar_cat = QPushButton(t("Eliminar Carpeta Seleccionada"))
        btn_eliminar_cat.setFixedHeight(34)
        btn_eliminar_cat.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eliminar_cat.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #dc2626;
                border: 1.5px solid #fca5a5;
                font-weight: 600;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #fee2e2;
                border-color: #ef4444;
            }
            QPushButton:disabled {
                color: #94a3b8;
                border-color: #e2e8f0;
                background-color: #f8fafc;
            }
        """)
        layout.addWidget(btn_eliminar_cat)

        def refrescar_dialog_combo():
            combo_existentes.clear()
            cats = obtener_categorias_usuario(self.nombre_usuario)
            if not cats:
                combo_existentes.addItem(t("No tienes carpetas creadas"))
                btn_eliminar_cat.setEnabled(False)
            else:
                btn_eliminar_cat.setEnabled(True)
                for c in cats:
                    combo_existentes.addItem(c)

        refrescar_dialog_combo()

        def on_crear():
            nombre = txt_nueva.text().strip()
            if not nombre:
                QMessageBox.warning(dlg, t("Aviso"), t("Ingresa un nombre para la carpeta."))
                return
            if crear_categoria_usuario(self.nombre_usuario, nombre):
                txt_nueva.clear()
                refrescar_dialog_combo()
                self.cargar_categorias_combo()
                show_toast(f"Carpeta '{nombre}' creada", "info")
            else:
                QMessageBox.warning(dlg, t("Aviso"), t("Ya existe una carpeta con ese nombre."))

        def on_eliminar():
            nombre = combo_existentes.currentText()
            if not nombre or nombre == t("No tienes carpetas creadas"):
                return
            resp = QMessageBox.question(
                dlg,
                t("Eliminar Carpeta"),
                f"{t('¿Deseas eliminar la carpeta')} '{nombre}'? {t('Las cartas seguirán en tu colección general.')}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resp == QMessageBox.StandardButton.Yes:
                eliminar_categoria_usuario(self.nombre_usuario, nombre)
                refrescar_dialog_combo()
                self.cargar_categorias_combo()
                self.reset_page_and_actualizar()
                show_toast(f"Carpeta '{nombre}' eliminada", "info")

        btn_crear.clicked.connect(on_crear)
        btn_eliminar_cat.clicked.connect(on_eliminar)

        btn_cerrar = QPushButton(t("Cerrar"))
        btn_cerrar.setFixedHeight(34)
        btn_cerrar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cerrar.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #703043;
                border: 2px solid #f2c4ce;
                border-radius: 10px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #ffeef2; }
        """)
        btn_cerrar.clicked.connect(dlg.accept)
        layout.addStretch()
        layout.addWidget(btn_cerrar)

        dlg.exec()

    def limpiar_filtros(self):
        self.buscador.blockSignals(True)
        self.buscador.clear()
        self.buscador.blockSignals(False)

        for combo in self.filtros.values():
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)

        if hasattr(self, 'combo_idioma'):
            self.combo_idioma.blockSignals(True)
            self.combo_idioma.setCurrentIndex(0)
            self.combo_idioma.blockSignals(False)

        self.carpeta_activa = None
        self.cargar_categorias_combo()

        self.reset_page_and_actualizar()

    def on_text_changed(self):
        self.timer_busqueda.start(300)

    def reset_page_and_actualizar(self):
        self.current_page = 0
        self.actualizar_total_cartas()
        self.actualizar_con_transicion()

    def _get_filter_value(self, combo):
        if combo.currentIndex() <= 0:
            return None
        return combo.currentText().strip()

    # ✅ SQLAlchemy conteo
    def actualizar_total_cartas(self):
        q = self.session.query(func.count(Cartas.id_api)).join(UsuarioCarta).filter(
            UsuarioCarta.usuario_nombre == self.nombre_usuario
        )

        selected_lang = self.combo_idioma.currentData()
        if selected_lang:
            q = q.filter(Cartas.idioma == selected_lang)

        if self.carpeta_activa:
            q = q.filter(UsuarioCarta.categoria == self.carpeta_activa)

        texto = self.buscador.text().lower().strip()
        if texto:
            q = q.filter(func.lower(Cartas.nombre).like(f"%{texto}%"))

        for columna, combo in self.filtros.items():
            if val := self._get_filter_value(combo):
                q = q.filter(getattr(Cartas, columna) == val)

        self.total_cartas = q.scalar()

    def actualizar_con_transicion(self):
        self.actualizar_galeria()
        self.container.update()
        self.scroll.viewport().update()

    # ✅ SQLAlchemy mostrar cartas
    def actualizar_galeria(self):
        # Limpiar sincrónicamente la estructura de la cuadrícula
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        texto = self.buscador.text().lower().strip()

        # Obtener dimensiones de carta desde ajustes
        from MyQtApp.config import load_settings
        settings = load_settings()
        tam = settings.get("tamano_cartas", "Normal")
        if tam == "Pequeño":
            size = (90, 127)
        elif tam == "Grande":
            size = (150, 212)
        else: # Normal
            size = (120, 170)
        self._current_card_size = size

        q = self.session.query(Cartas, UsuarioCarta.variante).join(
            UsuarioCarta,
            and_(
                Cartas.id_api == UsuarioCarta.carta_id,
                func.coalesce(Cartas.idioma, 'es') == func.coalesce(UsuarioCarta.idioma, 'es')
            )
        ).filter(
            UsuarioCarta.usuario_nombre == self.nombre_usuario
        )

        selected_lang = self.combo_idioma.currentData()
        if selected_lang:
            q = q.filter(Cartas.idioma == selected_lang)

        if self.carpeta_activa:
            q = q.filter(UsuarioCarta.categoria == self.carpeta_activa)

        if texto:
            q = q.filter(func.lower(Cartas.nombre).like(f"%{texto}%"))

        for columna, combo in self.filtros.items():
            if val := self._get_filter_value(combo):
                q = q.filter(getattr(Cartas, columna) == val)

        q = q.limit(self.CARTAS_POR_PAGINA).offset(self.current_page * self.CARTAS_POR_PAGINA)
        cartas_tuples = q.all()

        row, col = 0, 0
        self.labels_por_id.clear()
        self.card_widgets_por_key.clear()

        for carta, variante_db in cartas_tuples:
            nombre = carta.nombre
            id_api = carta.id_api
            card_lang = carta.idioma or language_manager.current_language
            card_key = f"{id_api}:{card_lang}"
            nombre_archivo = nombre.lower().replace(" ", "_")
            needs_download = False

            # 1. Intentar cargar versión .webp exacta por idioma de la carta
            pixmap = get_webp_pixmap(id_api, nombre, card_lang, size=size, allow_lang_fallback=False)
            if not pixmap:
                needs_download = True
                pixmap = get_webp_pixmap(id_api, nombre, card_lang, size=size, allow_lang_fallback=True)
            if not pixmap:
                pixmap = get_pixmap_from_zip(nombre_archivo, size=size, id_api=id_api)
            if not pixmap:
                ruta_alt = os.path.join(self.path_imagenes, f"{nombre_archivo}_{id_api}.webp")
                if os.path.exists(ruta_alt):
                    pixmap = QPixmap(ruta_alt).scaled(size[0], size[1], Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

            if not pixmap or pixmap.isNull():
                pixmap = get_card_placeholder_pixmap(size, nombre)
                needs_download = True

            card_widget = CardItemWidget(carta, pixmap, size, variante=variante_db or "Normal")
            card_widget.image_label.card_key = card_key
            card_widget.image_label.clicked.connect(self.seleccionar_carta)
            card_widget.variant_badge.variant_changed.connect(self.cambiar_variante_carta)

            if card_key in self.cartas_seleccionadas:
                card_widget.image_label.setStyleSheet("border: 2.5px solid #00cccc; border-radius: 6px; background-color: rgba(0, 255, 200, 0.25);")
            else:
                card_widget.image_label.setStyleSheet("border: none; background-color: transparent;")

            self.labels_por_id.setdefault(card_key, []).append(card_widget.image_label)
            self.card_widgets_por_key.setdefault(card_key, []).append(card_widget)
            self.grid.addWidget(card_widget, row, col)

            if needs_download:
                self.image_loader.request_image(
                    card_key,
                    id_api,
                    nombre,
                    idioma=card_lang,
                    set_id=getattr(carta, "set_id", None),
                    number=getattr(carta, "number", None),
                )

            col += 1
            if col == 5:
                col = 0
                row += 1

        total_pages = max(1, (self.total_cartas + self.CARTAS_POR_PAGINA - 1) // self.CARTAS_POR_PAGINA)
        self.lbl_pagina.setText(f"{t('Página')} {self.current_page + 1} {t('de')} {total_pages}")
        self.btn_anterior.setEnabled(self.current_page > 0)
        self.btn_siguiente.setEnabled(self.current_page < total_pages - 1)

    def _on_async_image_ready(self, card_key: str, local_path: str):
        widgets = self.card_widgets_por_key.get(card_key)
        if not widgets or not os.path.exists(local_path):
            return
        pix = QPixmap(local_path)
        if pix.isNull():
            return
        w, h = self._current_card_size
        scaled = pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        for cw in list(widgets):
            try:
                cw.set_card_pixmap(scaled)
            except RuntimeError:
                pass

    def cambiar_variante_carta(self, id_api, nueva_variante):
        try:
            rel = self.session.query(UsuarioCarta).filter(
                UsuarioCarta.usuario_nombre == self.nombre_usuario,
                UsuarioCarta.carta_id == id_api
            ).first()
            if rel:
                rel.variante = nueva_variante
                self.session.commit()
                show_toast(f"Variante actualizada: {nueva_variante}", "info")

        except Exception as e:
            print(f"Error cambiando variante en BD: {e}")

    def retranslate_ui(self):
        self.buscador.setPlaceholderText(t("Buscar carta por nombre..."))
        self.btn_sync_precios.setText(t("Precios Real-Time"))
        self.btn_anterior.setText(t("Anterior"))
        self.btn_siguiente.setText(t("Siguiente"))
        total_pages = max(1, (self.total_cartas + self.CARTAS_POR_PAGINA - 1) // self.CARTAS_POR_PAGINA)
        self.lbl_pagina.setText(f"{t('Página')} {self.current_page + 1} {t('de')} {total_pages}")
        self.actualizar_valor_total()

        campos_labels = [("Rareza", "rarity"), ("Tipo", "type"), ("Edición", "edition"),
                         ("Etapa", "stage"), ("Entrenador", "trainer"), ("Especial", "especial_type")]
        for etiqueta, columna in campos_labels:
            if columna in self.filtros:
                cb = self.filtros[columna]
                if cb.count() > 0:
                    cb.setItemText(0, f"{t(etiqueta)}: {t('Todos')}")

    def pagina_anterior(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.actualizar_con_transicion()
            from MyQtApp.config import load_settings
            settings = load_settings()
            vol = (settings.get("volumen_sonido", 80) / 100.0) * 0.5
            self.sonido_pagina.setVolume(vol)
            self.sonido_pagina.play()

    def pagina_siguiente(self):
        total = max(1, (self.total_cartas + self.CARTAS_POR_PAGINA - 1) // self.CARTAS_POR_PAGINA)
        if self.current_page < total - 1:
            self.current_page += 1
            self.actualizar_con_transicion()
            from MyQtApp.config import load_settings
            settings = load_settings()
            vol = (settings.get("volumen_sonido", 80) / 100.0) * 0.5
            self.sonido_pagina.setVolume(vol)
            self.sonido_pagina.play()

    def seleccionar_carta(self, label_obj, id_carta):
        card_key = getattr(label_obj, 'card_key', None) or id_carta

        if card_key in self.cartas_seleccionadas:
            self.cartas_seleccionadas.remove(card_key)
            style = "border: none; background-color: transparent;"
        else:
            self.cartas_seleccionadas.add(card_key)
            style = "border: 2.5px solid #00cccc; border-radius: 6px; background-color: rgba(0, 255, 200, 0.25);"

        labels = self.labels_por_id.get(card_key, [])
        if isinstance(labels, list):
            if label_obj and label_obj not in labels:
                labels.append(label_obj)
            for lbl in labels:
                lbl.setStyleSheet(style)
        elif label_obj:
            label_obj.setStyleSheet(style)

    def get_cartas_seleccionadas(self):
        if not self.cartas_seleccionadas:
            return []

        resultado = []
        for key in self.cartas_seleccionadas:
            if ":" in key:
                id_api, lang = key.split(":", 1)
            else:
                id_api, lang = key, language_manager.current_language

            c = self.session.query(Cartas.id_api, Cartas.nombre, Cartas.idioma)\
                .filter(Cartas.id_api == id_api, Cartas.idioma == lang).first()
            if not c:
                c = self.session.query(Cartas.id_api, Cartas.nombre, Cartas.idioma)\
                    .filter(Cartas.id_api == id_api).first()

            if c:
                resultado.append({"id_api": c[0], "nombre": c[1], "idioma": c[2]})

        return resultado

    def limpiar_seleccion(self):
        self.cartas_seleccionadas.clear()
        for key, labels in self.labels_por_id.items():
            if isinstance(labels, list):
                for lbl in labels:
                    lbl.setStyleSheet("border: none; background-color: transparent;")
            elif labels:
                labels.setStyleSheet("border: none; background-color: transparent;")

    def iniciar_sincronizacion_precios(self):
        from MyQtApp.app.price_updater import PriceUpdaterThread

        cartas_usuario = self.session.query(UsuarioCarta.carta_id, UsuarioCarta.idioma).filter(
            UsuarioCarta.usuario_nombre == self.nombre_usuario
        ).all()

        id_list = [(c[0], c[1] or "en") for c in cartas_usuario if c[0]]
        if not id_list:
            return

        self.btn_sync_precios.setEnabled(False)
        self.btn_sync_precios.setText("Conectando...")

        self.price_thread = PriceUpdaterThread(id_list, parent=self)
        self.price_thread.progress.connect(self.on_precio_progreso)
        self.price_thread.finished.connect(self.on_precio_finalizado)
        self.price_thread.start()

    def on_precio_progreso(self, actual, total):
        self.btn_sync_precios.setText(f"Cargando ({actual}/{total})...")

    def on_precio_finalizado(self, actualizadas):
        self.session.expire_all()
        self.btn_sync_precios.setEnabled(True)
        self.btn_sync_precios.setText(t("Precios Real-Time"))
        self.actualizar_valor_total()
        self.actualizar_galeria()

    def actualizar_valor_total(self):
        res = (
            self.session.query(func.sum(Cartas.price))
            .join(
                UsuarioCarta,
                and_(
                    Cartas.id_api == UsuarioCarta.carta_id,
                    func.coalesce(Cartas.idioma, 'es') == func.coalesce(UsuarioCarta.idioma, 'es'),
                ),
            )
            .filter(
                UsuarioCarta.usuario_nombre == self.nombre_usuario,
                Cartas.price > 0,
            )
            .scalar()
        )
        total_val = float(res) if res else 0.0
        self.lbl_valor_total.setText(f"{t('Valor Inventario')} ${total_val:,.2f} USD")
