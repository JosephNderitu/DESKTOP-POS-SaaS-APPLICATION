# desktop_client/barcode_scanner.py  (new file)
from PyQt6.QtCore import QObject, pyqtSignal, QElapsedTimer, QEvent, Qt
from PyQt6.QtGui import QKeyEvent


class BarcodeScannerFilter(QObject):
    """
    Global event filter that detects USB HID ("keyboard wedge") barcode
    scanner input. These devices fire keystrokes far faster than a human
    can type and terminate the scan with Enter. We use the inter-keystroke
    gap rather than which widget has focus - cashiers shouldn't need to
    click into a box before every scan.
    """
    barcode_scanned = pyqtSignal(str)

    MAX_INTERVAL_MS = 50
    MIN_BARCODE_LENGTH = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buffer = ""
        self._timer = QElapsedTimer()
        self._timer.start()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            elapsed = self._timer.elapsed()
            self._timer.restart()

            key_event: QKeyEvent = event

            if key_event.isAutoRepeat():
                # The phone's injected keystrokes land slightly slower than
                # real HID hardware, so Windows treats each one as a held
                # key and fires repeat KeyPress events. Without this guard,
                # one scanned '5' becomes '55555...' in the buffer.
                return False

            if key_event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if len(self._buffer) >= self.MIN_BARCODE_LENGTH:
                    self.barcode_scanned.emit(self._buffer)
                self._buffer = ""
                return False

            if elapsed > self.MAX_INTERVAL_MS:
                self._buffer = ""

            text = key_event.text()
            if text and text.isprintable():
                self._buffer += text

        return False  # never swallow events, other widgets still need them