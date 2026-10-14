import sys
from datetime import date
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from services.pdf_writer import SERIAL_X, SERIAL_Y
from services.processor import process_shipment
from services.licensing import validate_installed_license
from ui.license_dialog import ensure_license

APP_DIR = Path(__file__).resolve().parent
ICON_NAME = "shipment_policy_processor.ico"


def format_license_status(
    expires_on: date | None,
    *,
    today: date | None = None,
) -> str:
    if expires_on is None:
        return "License expiry: Never | Days remaining: Unlimited"

    days_remaining = (expires_on - (today or date.today())).days
    if days_remaining < 0:
        return f"License expired on {expires_on.isoformat()}"

    day_label = "day" if days_remaining == 1 else "days"
    return (
        f"License expiry: {expires_on.isoformat()} | "
        f"Days remaining: {days_remaining} {day_label}"
    )


def get_app_icon_path() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "assets" / ICON_NAME

    return APP_DIR / "assets" / ICON_NAME


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Shipment Policy Processor")
        self.setWindowIcon(QIcon(str(get_app_icon_path())))

        self.resize(600, 400)

        self.data_file = None
        self.policy_pdf = None
        license_payload = validate_installed_license()
        expires_on = license_payload["expires_on"]
        self.license_expiry_date = (
            date.fromisoformat(expires_on) if expires_on is not None else None
        )

        layout = QVBoxLayout()

        self.license_status_label = QLabel()
        layout.addWidget(self.license_status_label)
        self.update_license_status()

        self.license_status_timer = QTimer(self)
        self.license_status_timer.timeout.connect(self.update_license_status)
        self.license_status_timer.start(60_000)

        # ---------------------------------------------
        # Data file
        # ---------------------------------------------

        self.data_label = QLabel("Data file: Not selected")

        data_button = QPushButton("Select Excel / CSV")

        data_button.clicked.connect(self.select_data_file)

        layout.addWidget(data_button)
        layout.addWidget(self.data_label)

        # ---------------------------------------------
        # Policy PDF
        # ---------------------------------------------

        self.pdf_label = QLabel("Policy PDF: Not selected")

        pdf_button = QPushButton("Select Policy PDF")

        pdf_button.clicked.connect(self.select_policy_pdf)

        layout.addWidget(pdf_button)
        layout.addWidget(self.pdf_label)

        # ---------------------------------------------
        # Serial position preset
        # ---------------------------------------------

        layout.addWidget(QLabel("Serial position preset:"))

        position_layout = QHBoxLayout()
        self.position_group = QButtonGroup(self)
        self.bosta_position = QRadioButton("Bosta")
        self.jt_position = QRadioButton("J&T")
        self.position_group.addButton(self.bosta_position)
        self.position_group.addButton(self.jt_position)
        position_layout.addWidget(self.bosta_position)
        position_layout.addWidget(self.jt_position)
        layout.addLayout(position_layout)

        # ---------------------------------------------
        # X position
        # ---------------------------------------------

        layout.addWidget(QLabel("Serial X position:"))

        self.x_input = QLineEdit(str(SERIAL_X))

        layout.addWidget(self.x_input)

        # ---------------------------------------------
        # Y position
        # ---------------------------------------------

        layout.addWidget(QLabel("Serial Y position:"))

        self.y_input = QLineEdit(str(SERIAL_Y))

        layout.addWidget(self.y_input)

        self.jt_position.toggled.connect(
            lambda checked: checked and self.set_serial_position(48.56, 40)
        )
        self.bosta_position.toggled.connect(
            lambda checked: checked and self.set_serial_position(48.56, 125)
        )
        self.bosta_position.setChecked(True)

        # ---------------------------------------------
        # Process
        # ---------------------------------------------

        process_button = QPushButton("Process PDF")

        process_button.clicked.connect(self.process)

        layout.addWidget(process_button)

        self.setLayout(layout)

    def update_license_status(self) -> None:
        self.license_status_label.setText(
            format_license_status(self.license_expiry_date)
        )

    def set_serial_position(self, serial_x: float, serial_y: float):
        self.x_input.setText(str(serial_x))
        self.y_input.setText(str(serial_y))

    def select_data_file(self):

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Data File", "", "Data Files (*.csv *.xlsx *.xls)"
        )

        if file_path:

            self.data_file = file_path

            self.data_label.setText(f"Data file: {Path(file_path).name}")

    def select_policy_pdf(self):

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Policy PDF", "", "PDF Files (*.pdf)"
        )

        if file_path:

            self.policy_pdf = file_path

            self.pdf_label.setText(f"Policy PDF: {Path(file_path).name}")

    def read_serial_position(
        self, field: QLineEdit, label: str, default: float
    ) -> float:

        value_text = field.text().strip()

        if not value_text:
            return default

        try:
            return float(value_text)
        except ValueError as exc:
            raise ValueError(f"{label} must be a valid number.") from exc

    def process(self):

        if not self.data_file:

            QMessageBox.warning(
                self,
                "Missing File",
                "Please select the data file.",
            )

            return

        if not self.policy_pdf:

            QMessageBox.warning(
                self,
                "Missing File",
                "Please select the policy PDF.",
            )

            return

        output_directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
        )

        if not output_directory:
            return

        try:

            serial_x = self.read_serial_position(
                self.x_input,
                "Serial X position",
                SERIAL_X,
            )
            serial_y = self.read_serial_position(
                self.y_input,
                "Serial Y position",
                SERIAL_Y,
            )

            result = process_shipment(
                data_file=self.data_file,
                policy_pdf=self.policy_pdf,
                output_directory=output_directory,
                serial_x=serial_x,
                serial_y=serial_y,
            )

            pdf_message = (
                f"PDF:\n{result['pdf_file']}"
                if result["pdf_file"]
                else "PDF:\nNot generated because no page matched a phone number."
            )

            QMessageBox.information(
                self,
                "Processing Completed",
                (
                    "Processing completed successfully.\n\n"
                    f"Data records: "
                    f"{result['total_data_rows']}\n"
                    f"Matched records: "
                    f"{result['matched_rows']}\n"
                    f"Unmatched records: "
                    f"{result['unmatched_rows']}\n\n"
                    f"PDF pages: "
                    f"{result['total_pages']}\n"
                    f"Edited PDF pages: "
                    f"{result['matched_pages']}\n\n"
                    f"Excel:\n"
                    f"{result['excel_file']}\n\n"
                    f"{pdf_message}"
                ),
            )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Processing Error",
                str(e),
            )


if __name__ == "__main__":

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(get_app_icon_path())))

    if not ensure_license():
        sys.exit(1)

    window = MainWindow()

    window.show()

    sys.exit(app.exec())
