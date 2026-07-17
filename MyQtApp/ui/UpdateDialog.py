import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextBrowser, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from MyQtApp.app.updater import FileDownloaderThread
from MyQtApp.config import APP_VERSION

class UpdateDialog(QDialog):
    def __init__(self, new_version, release_notes, download_url, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Actualización Disponible")
        self.setFixedSize(500, 420)
        self.setObjectName("UpdateDialog")
        
        self.download_url = download_url
        self.new_version = new_version
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Título
        self.lbl_title = QLabel("¡Nueva actualización disponible!")
        self.lbl_title.setObjectName("UpdateTitle")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Comparativa de versiones
        self.lbl_versiones = QLabel(f"Versión actual: {APP_VERSION}   ➔   Nueva versión: {new_version}")
        self.lbl_versiones.setObjectName("UpdateVersions")
        self.lbl_versiones.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Notas de la versión
        self.lbl_notes_title = QLabel("Notas de la versión:")
        self.lbl_notes_title.setObjectName("UpdateNotesTitle")
        
        self.txt_notes = QTextBrowser()
        self.txt_notes.setObjectName("UpdateNotesBrowser")
        self.txt_notes.setPlainText(release_notes)
        self.txt_notes.setMinimumHeight(150)
        
        # Barra de progreso (oculta al inicio)
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("UpdateProgressBar")
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        
        # Etiqueta de estado de la descarga
        self.lbl_status = QLabel("Descargando actualización...")
        self.lbl_status.setObjectName("UpdateStatusLabel")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.hide()
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.btn_later = QPushButton("Actualizar más tarde")
        self.btn_later.setObjectName("UpdateLaterBtn")
        self.btn_later.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_later.setFixedHeight(38)
        self.btn_later.clicked.connect(self.reject)
        
        self.btn_now = QPushButton("Actualizar ahora")
        self.btn_now.setObjectName("UpdateNowBtn")
        self.btn_now.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_now.setFixedHeight(38)
        self.btn_now.clicked.connect(self.iniciar_actualizacion)
        
        btn_layout.addWidget(self.btn_later)
        btn_layout.addWidget(self.btn_now)
        
        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_versiones)
        layout.addWidget(self.lbl_notes_title)
        layout.addWidget(self.txt_notes)
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.progress_bar)
        layout.addLayout(btn_layout)
        
    def iniciar_actualizacion(self):
        if not self.download_url:
            QMessageBox.warning(self, "Error", "No se encontró el enlace de descarga para el instalador.")
            return
            
        if not self.download_url.lower().endswith(".exe"):
            # Si no es un instalador ejecutable directo (.exe), redirigir al navegador de GitHub
            QDesktopServices.openUrl(QUrl(self.download_url))
            self.accept()
            return
            
        # Ocultar botón "más tarde" y deshabilitar "actualizar ahora"
        self.btn_later.setEnabled(False)
        self.btn_now.setEnabled(False)
        self.btn_later.hide()
        
        # Mostrar progreso
        self.lbl_status.show()
        self.progress_bar.show()
        
        # Iniciar hilo de descarga en segundo plano
        self.downloader = FileDownloaderThread(self.download_url)
        self.downloader.progress_changed.connect(self.actualizar_progreso)
        self.downloader.finished.connect(self.al_finalizar_descarga)
        self.downloader.start()
        
    def actualizar_progreso(self, porcentaje):
        self.progress_bar.setValue(porcentaje)
        self.lbl_status.setText(f"Descargando actualización... {porcentaje}%")
        
    def al_finalizar_descarga(self, ruta_archivo, exito):
        if exito:
            self.lbl_status.setText("¡Descarga completa! Iniciando instalador...")
            try:
                # Lanzar el instalador ejecutable
                os.startfile(ruta_archivo)
                # Cerrar aplicación completa de forma segura
                from PyQt6.QtWidgets import QApplication
                QApplication.quit()
            except Exception as e:
                QMessageBox.critical(
                    self, 
                    "Error", 
                    f"No se pudo iniciar el instalador automáticamente:\n{str(e)}\n\nEl archivo se descargó en:\n{ruta_archivo}"
                )
                self.restaurar_botones()
        else:
            QMessageBox.critical(
                self, 
                "Error de Descarga", 
                "No se pudo descargar la actualización. Por favor, comprueba tu conexión y vuelve a intentarlo."
            )
            self.restaurar_botones()
            
    def restaurar_botones(self):
        self.btn_later.setEnabled(True)
        self.btn_later.show()
        self.btn_now.setEnabled(True)
        self.lbl_status.hide()
        self.progress_bar.hide()
