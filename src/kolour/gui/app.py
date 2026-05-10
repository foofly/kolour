"""QApplication entrypoint."""
from __future__ import annotations

import logging
import os
import sys

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def run() -> int:
    level = os.environ.get("KOLOUR_LOG", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("kolour")
    app.setOrganizationName("kolour")
    win = MainWindow()
    win.show()
    return app.exec()
