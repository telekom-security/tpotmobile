#!/usr/bin/env python3
"""T-Pot Mobile Qt Quick entry point. Qt is supplied by Raspberry Pi OS."""

import argparse
import logging
from pathlib import Path
import signal
import sys

from PyQt6.QtCore import QCoreApplication, QEvent, QTimer, QUrl
from PyQt6.QtGui import QFont, QFontDatabase, QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtQuick import QQuickWindow

from modules.backend import Backend


def main() -> int:
    parser = argparse.ArgumentParser(description="T-Pot Mobile touch display")
    parser.add_argument("--fixture", action="store_true", help="Synthetic, hardware-isolated development mode")
    parser.add_argument("--scenario", choices=["normal", "empty", "burst", "offline", "partial", "low-battery", "charging"], default="normal")
    parser.add_argument("--size", choices=["800x480", "1280x800"], default="1280x800")
    parser.add_argument("--snapshot", type=Path, help="Save a fixture screenshot and exit")
    parser.add_argument("--quit-after", type=int, help="Exit after this many milliseconds (fixture only)")
    parser.add_argument("--view", choices=["Overview", "Map", "Events", "Tops", "System"], default="Overview", help="Initial fixture view")
    parser.add_argument("--boot", action="store_true", help="Keep the fixture boot preview visible")
    parser.add_argument("--no-animations", action="store_true", help="Disable native map effects")
    args = parser.parse_args()
    if not args.fixture and (args.snapshot or args.quit_after is not None or args.scenario != "normal" or args.view != "Overview" or args.boot):
        parser.error("Development options require --fixture")
    if args.quit_after is not None and args.quit_after <= 0:
        parser.error("--quit-after must be positive")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    application = QGuiApplication([sys.argv[0]])
    application.setApplicationName("T-Pot Mobile")
    application.setOrganizationName("Telekom Security")
    families = QFontDatabase.families()
    ui_font = "DejaVu Sans" if "DejaVu Sans" in families else "Helvetica" if "Helvetica" in families else families[0]
    application.setFont(QFont(ui_font))
    mono_font = next((family for family in ("DejaVu Sans Mono", "Menlo", "Liberation Mono") if family in families), ui_font)
    backend = Backend(args.scenario if args.fixture else None)
    engine = QQmlApplicationEngine()
    width, height = map(int, args.size.split("x"))
    context = engine.rootContext()
    if context is None:
        logging.error("Unable to create the QML context")
        return 1
    context.setContextProperty("backend", backend)
    context.setContextProperty("fixtureWidth", width)
    context.setContextProperty("fixtureHeight", height)
    context.setContextProperty("uiMonoFamily", mono_font)
    context.setContextProperty(
        "uiFontFamily", ui_font,
    )
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / "qml" / "Main.qml")))
    if not engine.rootObjects():
        logging.error("Unable to load the QML frontend")
        return 1
    window = engine.rootObjects()[0]
    window.setProperty("page", ["Overview", "Map", "Events", "Tops", "System"].index(args.view))
    window.setProperty("animationsEnabled", not args.no_animations)
    if args.boot:
        window.setProperty("startupComplete", True)
    backend.start()
    signal.signal(signal.SIGTERM, lambda *_: application.quit())
    signal.signal(signal.SIGINT, lambda *_: application.quit())
    if args.quit_after:
        QTimer.singleShot(args.quit_after, application.quit)
    if args.snapshot:
        def snapshot() -> None:
            window = engine.rootObjects()[0]
            if not isinstance(window, QQuickWindow):
                logging.error("QML root is not a Qt Quick window")
                application.exit(1)
                return
            image = window.grabWindow()
            if image.isNull() or not image.save(str(args.snapshot)):
                logging.error("Could not save screenshot to %s", args.snapshot)
                application.exit(1)
            else:
                application.quit()
        QTimer.singleShot(1800, snapshot)
    try:
        return application.exec()
    finally:
        backend.close()
        engine.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


if __name__ == "__main__":
    raise SystemExit(main())
