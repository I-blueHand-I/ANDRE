import os
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QStackedLayout, QLineEdit, QFileDialog
)
from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtGui import QImage

from ui.shared_styles import _btn
from ui.theme import ACCENT


class ExportWidget(QWidget):
    """
    Bouton EXPORT ANIM qui se transforme en champ texte au clic.
    Sauvegarde les frames sous forme de PNGs numérotés dans :
        {animations_folder}/{nom_saisi}/frame_0001.png …
    Si animations_folder n'est pas configuré, ouvre un QFileDialog.
    """

    def __init__(self, config, frames_fn, parent=None):
        super().__init__(parent)
        self.config     = config
        self._frames_fn = frames_fn   # () -> list[np.ndarray]

        lay = QStackedLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self._btn = _btn("EXPORT ANIM", size=11, pad="5px 8px")
        self._btn.setFixedHeight(60)
        self._btn.clicked.connect(self._start_edit)
        self._btn_style = self._btn.styleSheet()

        self._edit = QLineEdit()
        self._edit.setPlaceholderText("nom du dossier…")
        self._edit.setFixedHeight(60)
        self._edit.setStyleSheet(f"""
            QLineEdit {{
                background: #1a1a1a; color: white;
                border: 1px solid {ACCENT};
                font-family: 'terminal grotesque'; font-weight: bold; font-size: 11px;
                padding: 5px 8px;
            }}
        """)
        self._edit.returnPressed.connect(self._confirm)
        self._edit.installEventFilter(self)

        lay.addWidget(self._btn)
        lay.addWidget(self._edit)

    # ── Événements ────────────────────────────────────────────────────────────

    def eventFilter(self, obj, event):
        if obj is self._edit and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key_Escape:
                self.layout().setCurrentIndex(0)
                return True
        return super().eventFilter(obj, event)

    def trigger(self):
        if self.layout().currentIndex() == 0:
            self._start_edit()
        else:
            self._confirm()

    def _start_edit(self):
        self.layout().setCurrentIndex(1)
        self._edit.clear()
        self._edit.setFocus()

    def _confirm(self):
        name = self._edit.text().strip()
        self.layout().setCurrentIndex(0)
        if name:
            self._do_export(name)
            self._btn.setText("✓ EXPORTED")
            self._btn.setStyleSheet(
                self._btn_style
                .replace("background-color: #333333", "background-color: #1a3d1a")
                .replace("color: white",               "color: #66dd66")
                .replace("border: 1px solid #666666",  "border: 1px solid #44aa44")
            )
            QTimer.singleShot(2000, self._reset_btn)

    def _reset_btn(self):
        self._btn.setText("EXPORT ANIM")
        self._btn.setStyleSheet(self._btn_style)

    # ── Export ────────────────────────────────────────────────────────────────

    def _do_export(self, folder_name: str):
        parent = self.config.get("animations_folder", "").strip()
        if not parent:
            parent = QFileDialog.getExistingDirectory(self, "Dossier d'export")
            if not parent:
                return

        dest = os.path.join(parent, folder_name)
        os.makedirs(dest, exist_ok=True)

        for i, frame in enumerate(self._frames_fn()):
            arr = np.ascontiguousarray(frame)
            H, W = arr.shape[:2]
            img  = QImage(arr.data, W, H, W * 3, QImage.Format_RGB888)
            img.save(os.path.join(dest, f"frame_{i + 1:04d}.png"))
