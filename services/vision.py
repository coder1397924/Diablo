import base64
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QBuffer, QByteArray, QIODevice
from PyQt6.QtGui import QPixmap


# =====================================================================
# PERFORMANCE + QUALITY CONSTANTS
# =====================================================================
_JPEG_QUALITY = 85
_MAX_WIDTH = 1600   # Resize large monitors to this width to reduce payload size


class VisionSentinel:

    @staticmethod
    def capture_primary_desktop() -> str:
        """
        Captures the primary monitor using Qt native APIs.
        Returns a base64-encoded JPEG string.
        
        Improvements:
        - No disk I/O (uses in-memory buffer)
        - Downscales very large monitors for performance
        - Validates pixmap capture success
        """
        try:
            screen = QApplication.primaryScreen()
            if not screen:
                print("[VISION SENTINEL]: No primary screen detected.")
                return ""

            pixmap: QPixmap = screen.grabWindow(0)

            if pixmap.isNull():
                print("[VISION SENTINEL]: Screen grab returned null pixmap.")
                return ""

            # ----------------------------------------------------------
            # Downscale very large images (4K → reduce network payload)
            # ----------------------------------------------------------
            if pixmap.width() > _MAX_WIDTH:
                pixmap = pixmap.scaledToWidth(
                    _MAX_WIDTH,
                    mode=1  # Qt.SmoothTransformation
                )

            # ----------------------------------------------------------
            # Convert to JPEG in-memory using QBuffer
            # ----------------------------------------------------------
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)

            success = pixmap.save(buffer, "JPG", quality=_JPEG_QUALITY)
            buffer.close()

            if not success:
                print("[VISION SENTINEL]: Failed to encode pixmap to JPEG.")
                return ""

            encoded_string = base64.b64encode(byte_array.data()).decode("utf-8")
            return encoded_string

        except Exception as e:
            print(f"[VISION SENTINEL ERROR]: Capture failure: {str(e)}")
            return ""