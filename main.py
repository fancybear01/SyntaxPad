"""SyntaxPad – launcher."""

import sys
from PyQt5.QtWidgets import QApplication
from SyntaxPadWindow import SyntaxPadWindow


def run() -> None:
    app = QApplication(sys.argv)
    window = SyntaxPadWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run()