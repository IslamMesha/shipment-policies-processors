import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.licensing import (
    LicenseError,
    get_device_id,
    get_license_path,
    validate_license_file,
)


class LicenseDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Activate Shipment Policy Processor")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "This computer needs a license. Send the machine ID below to "
                "the software provider to receive a license file."
            )
        )

        try:
            self.device_id = get_device_id()
        except LicenseError as exc:
            self.device_id = ""
            layout.addWidget(QLabel(str(exc)))
        else:
            device_id_label = QLabel(self.device_id)
            device_id_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            layout.addWidget(device_id_label)

            copy_button = QPushButton("Copy machine ID")
            copy_button.clicked.connect(self.copy_device_id)
            layout.addWidget(copy_button)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        select_button = QPushButton("Select license file...")
        select_button.clicked.connect(self.select_license)
        layout.addWidget(select_button)

        cancel_button = QPushButton("Exit")
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(cancel_button)

        self.activated = False

    def copy_device_id(self) -> None:
        QApplication.clipboard().setText(self.device_id)
        self.status_label.setText("Machine ID copied.")

    def select_license(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select License File",
            "",
            "License Files (*.json);;All Files (*)",
        )
        if not file_name:
            return

        source = Path(file_name)
        try:
            validate_license_file(source)
            destination = get_license_path()
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        except (LicenseError, OSError) as exc:
            self.status_label.setText(f"License could not be installed: {exc}")
            return

        self.activated = True
        self.accept()


def ensure_license() -> bool:
    try:
        validate_license_file()
        return True
    except LicenseError as exc:
        dialog = LicenseDialog()
        dialog.status_label.setText(str(exc))
        dialog.exec()
        return dialog.activated
