import json
import sys
import uuid
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QTextEdit, QListWidget, QListWidgetItem, QSplitter,
    QFileDialog, QMessageBox, QLabel, QToolBar
)

STORAGE_PATH = Path.home() / ".simple_notes.json"

def now_iso():
    return datetime.now().isoformat(timespec="seconds")

class NotesModel:
    """Sehr einfache JSON-„Datenbank“."""
    def __init__(self, path: Path):
        self.path = path
        self.notes = []
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                self.notes = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                # Fallback: korrupte Datei sichern
                backup = self.path.with_suffix(".backup.json")
                self.path.rename(backup)
                self.notes = []
        if not self.notes:
            self.create_note(title="Willkommen 👋", body="Dies ist deine erste Notiz.")
            self.save()

    def save(self):
        self.path.write_text(json.dumps(self.notes, ensure_ascii=False, indent=2), encoding="utf-8")

    def create_note(self, title="", body=""):
        n = {
            "id": str(uuid.uuid4()),
            "title": title.strip() or "Unbenannt",
            "body": body,
            "updated_at": now_iso(),
        }
        self.notes.insert(0, n)
        return n

    def update_note(self, note_id, title, body):
        for n in self.notes:
            if n["id"] == note_id:
                n["title"] = title.strip() or "Unbenannt"
                n["body"] = body
                n["updated_at"] = now_iso()
                return n
        return None

    def delete_note(self, note_id):
        self.notes = [n for n in self.notes if n["id"] != note_id]

    def find(self, note_id):
        for n in self.notes:
            if n["id"] == note_id:
                return n
        return None

class MainWindow(QMainWindow):
    AUTOSAVE_MS = 600  # Debounce-Autosave

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Notes (PySide6)")
        self.resize(1000, 650)

        self.model = NotesModel(STORAGE_PATH)
        self.current_id = None
        self.dirty = False
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self.save_current_note)

        self._build_ui()
        self._load_list()

    # ---------- UI ----------
    def _build_ui(self):
        # Toolbar / Aktionen
        toolbar = QToolBar("Haupttoolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        act_new = QAction("Neu", self)
        act_new.setShortcut(QKeySequence.New)
        act_new.triggered.connect(self.new_note)
        toolbar.addAction(act_new)

        act_save = QAction("Speichern", self)
        act_save.setShortcut(QKeySequence.Save)
        act_save.triggered.connect(self.save_current_note)
        toolbar.addAction(act_save)

        act_delete = QAction("Löschen", self)
        act_delete.setShortcut(QKeySequence.Delete)
        act_delete.triggered.connect(self.delete_current_note)
        toolbar.addAction(act_delete)

        toolbar.addSeparator()

        act_export = QAction("Exportieren…", self)
        act_export.setShortcut("Ctrl+E")
        act_export.triggered.connect(self.export_notes)
        toolbar.addAction(act_export)

        # Splitter: links Liste + Suche, rechts Editor
        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        self.setCentralWidget(splitter)

        # --- Linke Seite (Suche + Liste) ---
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 8, 8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Suchen… (Titel/Text)")
        self.search.textChanged.connect(self._apply_filter)
        self.list = QListWidget()
        self.list.itemSelectionChanged.connect(self._on_list_selection_changed)
        left_layout.addWidget(self.search)
        left_layout.addWidget(self.list)

        # --- Rechte Seite (Titel + Editor) ---
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)

        title_row = QHBoxLayout()
        self.title = QLineEdit()
        self.title.setPlaceholderText("Titel")
        self.title.textEdited.connect(self._on_edited)
        self.meta = QLabel("")
        self.meta.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.meta.setStyleSheet("color:#666;")
        title_row.addWidget(self.title, 2)
        title_row.addWidget(self.meta, 1)

        self.body = QTextEdit()
        self.body.textChanged.connect(self._on_edited)

        right_layout.addLayout(title_row)
        right_layout.addWidget(self.body)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # Beim ersten Start erste Notiz anzeigen
        if self.model.notes:
            self._load_note_into_editor(self.model.notes[0]["id"])

    # ---------- Daten / Liste ----------
    def _load_list(self, filtered=None):
        self.list.blockSignals(True)
        self.list.clear()
        notes = filtered if filtered is not None else self.model.notes
        for n in notes:
            item = QListWidgetItem(f'{n["title"]}')
            item.setData(Qt.UserRole, n["id"])
            item.setToolTip(f'Zuletzt geändert: {n["updated_at"]}')
            self.list.addItem(item)
        self.list.blockSignals(False)

    def _apply_filter(self):
        q = self.search.text().strip().lower()
        if not q:
            self._load_list()
            return
        filtered = []
        for n in self.model.notes:
            if q in n["title"].lower() or q in n["body"].lower():
                filtered.append(n)
        self._load_list(filtered)

    # ---------- Editor-Logik ----------
    def _on_edited(self):
        self.dirty = True
        self._autosave_timer.start(self.AUTOSAVE_MS)

    def _on_list_selection_changed(self):
        selected = self.list.selectedItems()
        if not selected:
            return
        note_id = selected[0].data(Qt.UserRole)
        if note_id == self.current_id:
            return
        # Vor Wechsel speichern (leise)
        if self.dirty:
            self.save_current_note()
        self._load_note_into_editor(note_id)

    def _load_note_into_editor(self, note_id):
        n = self.model.find(note_id)
        if not n:
            return
        self.current_id = note_id
        self.title.blockSignals(True)
        self.body.blockSignals(True)
        self.title.setText(n["title"])
        self.body.setPlainText(n["body"])
        self.title.blockSignals(False)
        self.body.blockSignals(False)
        self.meta.setText(f'Zuletzt geändert: {n["updated_at"]}')
        self.dirty = False
        # In Liste markieren
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.data(Qt.UserRole) == note_id:
                self.list.setCurrentItem(it)
                break

    # ---------- Aktionen ----------
    def new_note(self):
        if self.dirty:
            self.save_current_note()
        n = self.model.create_note(title="Neue Notiz", body="")
        self.model.save()
        self._load_list()
        self._load_note_into_editor(n["id"])

    def save_current_note(self):
        if not self.current_id:
            return
        title = self.title.text()
        body = self.body.toPlainText()
        updated = self.model.update_note(self.current_id, title, body)
        if updated:
            self.meta.setText(f'Zuletzt geändert: {updated["updated_at"]}')
            self._refresh_list_item_title(self.current_id, updated["title"])
            self.model.save()
            self.dirty = False

    def _refresh_list_item_title(self, note_id, title):
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.data(Qt.UserRole) == note_id:
                it.setText(title)
                it.setToolTip(f'Zuletzt geändert: {now_iso()}')
                break

    def delete_current_note(self):
        if not self.current_id:
            return
        reply = QMessageBox.question(
            self, "Löschen bestätigen",
            "Diese Notiz wirklich löschen?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        nid = self.current_id
        self.model.delete_note(nid)
        self.model.save()
        self.current_id = None
        self.dirty = False
        self._load_list()
        # Editor leeren oder nächste Notiz öffnen
        if self.model.notes:
            self._load_note_into_editor(self.model.notes[0]["id"])
        else:
            self.title.clear()
            self.body.clear()
            self.meta.clear()

    def export_notes(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportieren als JSON", str(Path.home() / "notes_export.json"), "JSON (*.json)")
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(self.model.notes, ensure_ascii=False, indent=2), encoding="utf-8")
            QMessageBox.information(self, "Export", "Export erfolgreich.")
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Export", str(e))

    # ---------- Fenster schließen ----------
    def closeEvent(self, event):
        if self.dirty:
            # leises Autosave statt Dialog
            self.save_current_note()
        event.accept()

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
