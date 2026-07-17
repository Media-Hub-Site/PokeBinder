# TCG Inventory Manager (v1.0)

Una aplicación de escritorio moderna y fluida desarrollada con **Python**, **PyQt6** y **SQLAlchemy** (SQLite) diseñada para catalogar y administrar inventarios de cartas coleccionables del Pokémon TCG.

---

## 🌟 Características Principales

* **Transiciones Premium:** Animación de destello blanco ("flash") coordinado y redimensionamiento dinámico y centrado de la ventana al cambiar del inicio de sesión a la pantalla principal.
* **Efectos Micro-Interactivos:** Animación de burbuja expansiva y desvanecimiento al seleccionar cualquier carta en la galería.
* **Persistencia de Ajustes en Tiempo Real:** Configuración persistente de audio (música/efectos), activación de animaciones, tamaño de fuente dinámico y alternancia de tema Claro/Oscuro guardados en un archivo JSON.
* **Actualizador Automático:** Chequeo en segundo plano conectado a la API de GitHub Releases. Si detecta una nueva versión, muestra un diálogo integrado con las notas de la versión, descarga el nuevo instalador en segundo plano y lo ejecuta al cerrar la app.
* **Base de Datos Local Optimizada:** Integración segura con SQLAlchemy y SQLite con cierre automático de sesiones inactivas.

---

## 🚀 Instalación y Desarrollo Local

### Requisitos Previos
* Python 3.11 o posterior instalado en el sistema.

### Configuración del Entorno
1. Clona este repositorio en tu máquina local.
2. Crea e inicia un entorno virtual de Python:
   ```powershell
   # En Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. Instala las dependencias necesarias:
   ```bash
   pip install -r requirements.txt
   ```
4. Ejecuta la aplicación:
   ```bash
   python main.py
   ```

---

## 📦 Compilación y Distribución (Windows)

### 1. Crear el Ejecutable con PyInstaller
Para compilar la aplicación en un paquete independiente ejecutable, incluyendo los sonidos, iconos y estilos, pero **excluyendo la carpeta de imágenes** (para que el ejecutable no pese 250MB):

```powershell
pyinstaller --noconsole --name "TCG_Inventory" --add-data "assets/sounds;assets/sounds" --add-data "assets/icons;assets/icons" --add-data "assets/style.qss;assets" --add-data "assets/style_dark.qss;assets" --add-data "PokeDatabase.db;." main.py
```
Esto creará el ejecutable y sus recursos dentro de la carpeta `dist/TCG_Inventory`.

---

## 🖼️ Gestión y Descarga de las Imágenes (Modo Offline)

Dado que las imágenes de las cartas (WebP/PNG) superan los **250 MB** (más de 19,000 archivos), **no se deben subir al repositorio de GitHub**. En su lugar, el instalador de **Inno Setup** las descarga y descomprime automáticamente al instalar el software.

### Paso 1: Subir las Imágenes a GitHub Releases
1. Comprime tu carpeta `assets/images` en un archivo llamado `images.zip`.
2. Cuando publiques tu Release `v1.0` en GitHub, adjunta el archivo `images.zip` y el ejecutable del instalador compilado como assets de la release. Tu enlace de descarga directo será:
   `https://github.com/Alan-Dave/TCG-Inventory/releases/download/v1.0/images.zip`

### Paso 2: Configurar Inno Setup con Descarga Automática
Utiliza el siguiente script de Inno Setup (`installer.iss`) incorporando el plugin `Inno Download Plugin` (IDP) para automatizar la descarga y descompresión del paquete de imágenes durante la instalación:

```pascal
[Setup]
AppName=TCG Inventory Manager
AppVersion=1.0
DefaultDirName={autopf}\TCG Inventory Manager
DefaultGroupName=TCG Inventory Manager
OutputDir=Output
OutputBaseFilename=TCG_Inventory_Installer

#include <idp.iss>

[Files]
; Copiar los archivos compilados de PyInstaller
Source: "dist\TCG_Inventory\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Dirs]
; Crear el directorio destino de imágenes
Name: "{app}\assets\images"

[Code]
procedure InitializeWizard;
begin
  // Descargar el zip de imágenes directamente desde los Assets de tu Release de GitHub
  idpAddFile('https://github.com/Alan-Dave/TCG-Inventory/releases/download/v1.0/images.zip', ExpandConstant('{tmp}\images.zip'));
  idpDownloadAfter(wpReady);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssInstall then
  begin
    // Extraer el zip de imágenes usando PowerShell nativo de Windows silenciosamente
    Exec('powershell.exe', 
         ExpandConstant('-Command "Expand-Archive -Path ''{tmp}\images.zip'' -DestinationPath ''{app}\assets\images'' -Force"'), 
         '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;
```
