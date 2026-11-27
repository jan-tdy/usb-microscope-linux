import sys

from PyQt5.QtWidgets import QApplication

from microscope.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1000, 600)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
