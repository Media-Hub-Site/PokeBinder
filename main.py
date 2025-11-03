import sys
from PyQt6.QtWidgets import QApplication
from MyQtApp.ui.Index import MainWindow
from MyQtApp.ui.Login import LoginWindow  # importa tu Login


def main():
    app = QApplication(sys.argv)

    Login = LoginWindow()
    Login.show()
    app.exec()  # Aquí se ejecuta el loop, cuando cierras Login sigue el código

    usuario = Login.get_usuario()

    if usuario is None:
        print("No se inició sesión, cerrando programa.")
        sys.exit()

    ventana = MainWindow(usuario)
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
