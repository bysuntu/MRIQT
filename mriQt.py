import sys
import os
import numpy as np
import pydicom
import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout,
                             QPushButton, QSlider, QHBoxLayout, QFileDialog,
                             QGroupBox, QSpinBox, QFormLayout, QLineEdit,
                             QComboBox, QDateEdit, QMessageBox, QTableWidget,
                             QTableWidgetItem, QDialog, QVBoxLayout as QVBoxLayoutDialog,
                             QHeaderView, QInputDialog, QTextEdit)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QImage, QIcon
from PyQt5.QtCore import Qt, QPointF, QDate, QSize
import math

from dataprocessingpython import kspace2Image

# Import checkConnection function from test_basic
try:
    from test_basic import checkConnection
except ImportError:
    # Fallback if test_basic is not available
    def checkConnection():
        return 0  # Default to success for testing

class PatientDatabaseDialog(QDialog):
    """Dialog to display patient database records"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Patient Database")
        self.setGeometry(200, 200, 700, 500)

        # Set dark theme for dialog
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
                font-size: 10pt;
            }
            QTableWidget {
                background-color: #3a3a3a;
                alternate-background-color: #404040;
                color: #ffffff;
                gridline-color: #555555;
                border: 1px solid #666666;
            }
            QHeaderView::section {
                background-color: #4a4a4a;
                color: #ffffff;
                padding: 3px;
                border: 1px solid #666666;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 3px;
                color: #ffffff;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)

        layout = QVBoxLayoutDialog()

        # Create table widget
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "IC", "Date of Birth", "Sex", "Height (cm)", "Weight (kg)", "Created At"])

        # Make table read-only
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        # Set column resize mode
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)

        layout.addWidget(self.table)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def load_data(self, data):
        """Load data into the table"""
        self.table.setRowCount(len(data))

        for row_idx, row_data in enumerate(data):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value) if value is not None else "")
                self.table.setItem(row_idx, col_idx, item)

class ImageLabel(QLabel):
    """Custom QLabel that draws lines on top of the image"""
    def __init__(self, text, parent):
        super().__init__(text)
        self.parent_widget = parent

    def paintEvent(self, event):
        # First draw the label (image) itself
        super().paintEvent(event)

        # Then draw lines on top if we have a pixmap
        if self.pixmap() and not self.pixmap().isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # Get the actual pixmap size within the label
            label_width = self.width()
            label_height = self.height()

            scaled_pixmap = self.pixmap().scaled(label_width, label_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            pixmap_width = scaled_pixmap.width()
            pixmap_height = scaled_pixmap.height()

            # Calculate the offset to center the pixmap within the label
            pixmap_x = (label_width - pixmap_width) // 2
            pixmap_y = (label_height - pixmap_height) // 2

            # Set clipping region to the pixmap area only
            painter.setClipRect(pixmap_x, pixmap_y, pixmap_width, pixmap_height)

            # Dotted line pen
            pen = QPen(Qt.red, 2, Qt.DotLine)
            painter.setPen(pen)

            # Get parameters from parent widget
            angle = self.parent_widget.degree_slider.value() / 10.0  # Convert from tenths to degrees
            spacing = self.parent_widget.thickness_spinbox.value()
            num_lines = self.parent_widget.num_lines_spinbox.value()
            origin_x = self.parent_widget.origin_x_spinbox.value()
            origin_y = self.parent_widget.origin_y_spinbox.value()
            line_length = self.parent_widget.line_length_spinbox.value()

            # Convert angle to radians
            angle_rad = math.radians(angle)

            # Calculate perpendicular direction for spacing
            perp_angle_rad = angle_rad + math.pi / 2

            # Draw multiple parallel lines
            for i in range(num_lines):
                # Calculate offset from origin for this line
                offset = (i - (num_lines - 1) / 2) * spacing

                # Calculate the center point of this line (offset perpendicular to line direction)
                center_x = origin_x + offset * math.cos(perp_angle_rad)
                center_y = origin_y + offset * math.sin(perp_angle_rad)

                # Calculate line endpoints using the specified line length
                half_length = line_length / 2

                # Start and end points along the line direction
                x1 = center_x - half_length * math.cos(angle_rad)
                y1 = center_y - half_length * math.sin(angle_rad)
                x2 = center_x + half_length * math.cos(angle_rad)
                y2 = center_y + half_length * math.sin(angle_rad)

                # Translate to pixmap coordinates
                x1 += pixmap_x
                y1 += pixmap_y
                x2 += pixmap_x
                y2 += pixmap_y

                # Draw the line
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

class FrontPage(QWidget):
    """Front page with 4 main buttons"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MRI DICOM System")
        self.setGeometry(100, 100, 450, 220)

        # Remove default window frame for custom dark theme
        self.setWindowFlags(Qt.FramelessWindowHint)

        # Set dark gray background stylesheet
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                font-size: 14pt;
            }
            QPushButton {
                background-color: #4a4a4a;
                border: 2px solid #666666;
                border-radius: 10px;
                padding: 30px;
                color: #ffffff;
                font-size: 16pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
                border: 2px solid #888888;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QLabel {
                color: #ffffff;
            }
        """)

        # Create main layout with tight margins
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)  # Very small margins

        # Title bar with close button
        title_bar = QHBoxLayout()

        # Title
        title = QLabel("MRI DICOM System")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title.setStyleSheet("font-size: 18pt; font-weight: bold; margin: 5px;")
        title_bar.addWidget(title)

        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(40, 40)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #ffffff;
                font-size: 32pt;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #ff0000;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #cc0000;
            }
        """)
        close_btn.clicked.connect(self.close)
        title_bar.addWidget(close_btn)

        layout.addLayout(title_bar)

        # Create horizontal layout for buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)  # Very small spacing between buttons
        button_layout.setContentsMargins(10, 10, 10, 10)  # Reduce margins around the button group

        # Connection button with overlapping status indicator
        button_size = 60

        # Create a container widget for connection button to enable absolute positioning
        connection_container = QWidget()
        connection_container.setFixedSize(button_size, button_size)

        self.connection_btn = QPushButton(connection_container)
        self.connection_btn.clicked.connect(self.open_connection)
        self.connection_btn.setFixedSize(button_size, button_size)
        self.connection_btn.move(0, 0)

        # Remove padding and make icon fill the button
        self.connection_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #666666;
                border-radius: 5px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
                border: 1px solid #888888;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)

        # Set SVG icon for connection button (replacing text)
        icon_path = os.path.join(os.path.dirname(__file__), "icons", "connection.svg")
        if os.path.exists(icon_path):
            self.connection_btn.setIcon(QIcon(icon_path))
            # Make icon fit the smaller button
            self.connection_btn.setIconSize(QSize(button_size - 6, button_size - 6))
            self.connection_btn.setToolTip("Connection")  # Add tooltip for accessibility
        else:
            # Fallback if icon not found
            self.connection_btn.setText("Connection")

        # Status label overlapping at upper right corner of button
        self.connection_status = QLabel("", connection_container)
        self.connection_status.setStyleSheet("font-size: 16pt; padding: 0px; background-color: transparent;")
        self.connection_status.setAlignment(Qt.AlignCenter)
        self.connection_status.setFixedSize(30, 30)
        self.connection_status.move(button_size - 30, 0)  # Position at upper right corner
        self.connection_status.raise_()  # Bring to front

        button_layout.addWidget(connection_container)

        # Operation button
        self.operation_btn = QPushButton()
        self.operation_btn.clicked.connect(self.open_operation)
        self.operation_btn.setFixedSize(button_size, button_size)

        # Remove padding and make icon fill the button
        self.operation_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #666666;
                border-radius: 5px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
                border: 1px solid #888888;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)

        # Set SVG icon for operation button
        operation_icon_path = os.path.join(os.path.dirname(__file__), "icons", "acquisition.svg")
        if os.path.exists(operation_icon_path):
            self.operation_btn.setIcon(QIcon(operation_icon_path))
            self.operation_btn.setIconSize(QSize(button_size - 6, button_size - 6))
            self.operation_btn.setToolTip("Operation")
        else:
            self.operation_btn.setText("Operation")

        button_layout.addWidget(self.operation_btn)

        # Checking button
        self.checking_btn = QPushButton()
        self.checking_btn.clicked.connect(self.open_checking)
        self.checking_btn.setFixedSize(button_size, button_size)

        # Remove padding and make icon fill the button
        self.checking_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #666666;
                border-radius: 5px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
                border: 1px solid #888888;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)

        # Set SVG icon for checking button
        checking_icon_path = os.path.join(os.path.dirname(__file__), "icons", "checking.svg")
        if os.path.exists(checking_icon_path):
            self.checking_btn.setIcon(QIcon(checking_icon_path))
            self.checking_btn.setIconSize(QSize(button_size - 6, button_size - 6))
            self.checking_btn.setToolTip("Checking")
        else:
            self.checking_btn.setText("Checking")

        button_layout.addWidget(self.checking_btn)

        # Viewing button
        self.viewing_btn = QPushButton()
        self.viewing_btn.clicked.connect(self.open_viewing)
        self.viewing_btn.setFixedSize(button_size, button_size)

        # Remove padding and make icon fill the button
        self.viewing_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #666666;
                border-radius: 5px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
                border: 1px solid #888888;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)

        # Set SVG icon for viewing button
        viewing_icon_path = os.path.join(os.path.dirname(__file__), "icons", "viewing.svg")
        if os.path.exists(viewing_icon_path):
            self.viewing_btn.setIcon(QIcon(viewing_icon_path))
            self.viewing_btn.setIconSize(QSize(button_size - 6, button_size - 6))
            self.viewing_btn.setToolTip("Viewing")
        else:
            self.viewing_btn.setText("Viewing")

        button_layout.addWidget(self.viewing_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Reference to operation window
        self.operation_window = None

    def open_connection(self):
        """Open connection interface and check connection status"""
        # Show checking message (clock icon)
        self.connection_status.setText("🕐")
        self.connection_status.setStyleSheet("font-size: 48pt; padding: 0px; background-color: transparent;")
        QApplication.processEvents()  # Update UI immediately

        try:
            # Call checkConnection function
            result = checkConnection()

            if result == 0:
                # Success - show green tick
                self.connection_status.setText("✓")
                self.connection_status.setStyleSheet("font-size: 64pt; padding: 0px; color: #00ff00; background-color: transparent;")
                QMessageBox.information(self, "Connection", f"Connection successful!\nReturn code: {result}")
            else:
                # Failure - show red cross (thin version)
                self.connection_status.setText("×")
                self.connection_status.setStyleSheet("font-size: 64pt; padding: 0px; color: #ff0000; background-color: transparent;")
                QMessageBox.warning(self, "Connection", f"Connection failed!\nReturn code: {result}")

        except Exception as e:
            # Error - show red cross (thin version)
            self.connection_status.setText("×")
            self.connection_status.setStyleSheet("font-size: 64pt; padding: 0px; color: #ff0000; background-color: transparent;")
            QMessageBox.critical(self, "Connection Error", f"Error during connection:\n{str(e)}")

    def open_operation(self):
        """Open operation interface (current GUI)"""
        if self.operation_window is None:
            self.operation_window = ImageWithLine(parent=self)
        self.operation_window.show()
        self.hide()

    def open_checking(self):
        """Open checking interface"""
        QMessageBox.information(self, "Checking", "Checking module - Coming soon!")

    def open_viewing(self):
        """Open viewing interface"""
        QMessageBox.information(self, "Viewing", "Viewing module - Coming soon!")

class ImageWithLine(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent_window = parent
        self.setWindowTitle("MRI DICOM Viewer with Line - Operation")
        self.setGeometry(100, 100, 1000, 600)

        # Remove default window frame for custom dark theme
        self.setWindowFlags(Qt.FramelessWindowHint)

        # Set dark gray background stylesheet
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                font-size: 12pt;
            }
            QGroupBox {
                background-color: #3a3a3a;
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 5px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QLineEdit, QSpinBox, QComboBox, QDateEdit {
                background-color: #404040;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 3px;
                color: #ffffff;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDateEdit:focus {
                border: 1px solid #888888;
            }
            QSlider::groove:horizontal {
                background: #404040;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #6a6a6a;
                border: 1px solid #888888;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #7a7a7a;
            }
            QLabel {
                color: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                width: 0px;
                height: 0px;
            }
        """)

        # Initialize variables
        self.dicom_files = []
        self.current_index = 0
        self.pixmap = None
        self.current_folder_path = None

        # Initialize database
        self.init_database()

        # Create main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)  # Reduce margins

        # Top bar with back button and close button
        top_bar = QHBoxLayout()
        self.back_btn = QPushButton("← Back to Main Menu")
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.setMaximumWidth(200)
        top_bar.addWidget(self.back_btn)
        top_bar.addStretch()

        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(40, 40)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #ffffff;
                font-size: 32pt;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #ff0000;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #cc0000;
            }
        """)
        close_btn.clicked.connect(self.close)
        top_bar.addWidget(close_btn)

        main_layout.addLayout(top_bar)

        # Content layout
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(5, 5, 5, 5)  # Reduce margins
        content_layout.setSpacing(5)  # Reduce spacing between sections

        # Left side - Patient Demographics
        left_layout = QVBoxLayout()
        left_layout.setSpacing(3)  # Reduce spacing between elements

        # Patient information group box
        patient_info_group = QGroupBox("Patient Information")
        patient_info_group.setStyleSheet("font-size: 10pt;")  # Smaller font
        patient_form = QFormLayout()
        patient_form.setVerticalSpacing(3)  # Reduce vertical spacing
        patient_form.setHorizontalSpacing(5)  # Reduce horizontal spacing
        patient_form.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)  # Prevent expansion

        # Name field
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter patient name")
        self.name_input.setStyleSheet("padding: 2px; font-size: 10pt;")  # Smaller font and padding
        patient_form.addRow("Name:", self.name_input)

        # IC (Identification Card) field
        self.ic_input = QLineEdit()
        self.ic_input.setPlaceholderText("Enter IC number")
        self.ic_input.setStyleSheet("padding: 2px; font-size: 10pt;")  # Smaller font and padding
        patient_form.addRow("IC:", self.ic_input)

        # Date of Birth field
        self.dob_input = QDateEdit()
        self.dob_input.setCalendarPopup(True)
        self.dob_input.setDate(QDate.currentDate())
        self.dob_input.setDisplayFormat("dd/MM/yyyy")
        self.dob_input.setStyleSheet("padding: 2px; font-size: 10pt;")  # Smaller font and padding
        patient_form.addRow("Date of Birth:", self.dob_input)

        # Sex field
        self.sex_input = QComboBox()
        self.sex_input.addItems(["Male", "Female", "Other"])
        self.sex_input.setStyleSheet("padding: 2px; font-size: 10pt;")  # Smaller font and padding
        patient_form.addRow("Sex:", self.sex_input)

        # Height field
        self.height_input = QLineEdit()
        self.height_input.setPlaceholderText("cm")
        self.height_input.setStyleSheet("padding: 2px; font-size: 10pt;")  # Smaller font and padding
        patient_form.addRow("Height (cm):", self.height_input)

        # Weight field
        self.weight_input = QLineEdit()
        self.weight_input.setPlaceholderText("kg")
        self.weight_input.setStyleSheet("padding: 2px; font-size: 10pt;")  # Smaller font and padding
        patient_form.addRow("Weight (kg):", self.weight_input)

        # Save button
        self.save_patient_btn = QPushButton("Save Patient Info")
        self.save_patient_btn.clicked.connect(self.save_patient_info)
        self.save_patient_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 3px;
                color: #ffffff;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)
        patient_form.addRow(self.save_patient_btn)

        # Clear button
        self.clear_patient_btn = QPushButton("Clear Form")
        self.clear_patient_btn.clicked.connect(self.clear_patient_form)
        self.clear_patient_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 3px;
                color: #ffffff;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)
        patient_form.addRow(self.clear_patient_btn)

        # View database button
        self.view_db_btn = QPushButton("View All Patients")
        self.view_db_btn.clicked.connect(self.view_database)
        self.view_db_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 3px;
                color: #ffffff;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)
        patient_form.addRow(self.view_db_btn)

        patient_info_group.setLayout(patient_form)
        left_layout.addWidget(patient_info_group)
        left_layout.addStretch()

        # Center - Image display
        center_layout = QVBoxLayout()
        center_layout.setSpacing(3)  # Reduce spacing between elements

        # Image label - Custom label for drawing lines
        self.label = ImageLabel("Load DICOM images to begin", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setMinimumSize(400, 400)  # Reduce minimum size
        self.label.setStyleSheet("border: 1px solid #555555; background-color: #1a1a1a;")

        # Load button
        self.load_button = QPushButton("Load DICOM Images")
        self.load_button.clicked.connect(self.load_images)
        self.load_button.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 3px;
                color: #ffffff;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)

        # Save scan button
        self.save_scan_button = QPushButton("Save Scan to Patient")
        self.save_scan_button.clicked.connect(self.save_scan_to_patient)
        self.save_scan_button.setEnabled(False)
        self.save_scan_button.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 3px;
                color: #ffffff;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)

        # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        self.slider.setValue(0)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(self.slider_changed)

        # Slider label
        self.slider_label = QLabel("Image: 0 / 0")
        self.slider_label.setAlignment(Qt.AlignCenter)
        self.slider_label.setStyleSheet("font-size: 10pt; padding: 0px;")

        center_layout.addWidget(self.label)
        center_layout.addWidget(self.load_button)
        center_layout.addWidget(self.save_scan_button)
        center_layout.addWidget(self.slider_label)
        center_layout.addWidget(self.slider)

        # Right side - Line parameters
        right_layout = QVBoxLayout()
        right_layout.setSpacing(3)  # Reduce spacing between elements

        # Line parameters group box
        line_params_group = QGroupBox("Parallel Lines Parameters")
        params_vlayout = QVBoxLayout()
        params_vlayout.setContentsMargins(5, 10, 5, 5)  # Reduce margins
        params_vlayout.setSpacing(3)  # Reduce spacing between elements

        # Angle control
        angle_layout = QVBoxLayout()
        angle_layout.setSpacing(2)  # Reduce spacing
        self.angle_label = QLabel("Angle: 0.0°")
        self.angle_label.setAlignment(Qt.AlignCenter)
        self.angle_label.setStyleSheet("font-size: 10pt;")  # Smaller font
        self.degree_slider = QSlider(Qt.Horizontal)
        self.degree_slider.setRange(0, 3600)  # 0 to 360.0 degrees (in tenths)
        self.degree_slider.setValue(0)
        self.degree_slider.setTickPosition(QSlider.TicksBelow)
        self.degree_slider.setTickInterval(450)  # Tick every 45 degrees
        self.degree_slider.valueChanged.connect(self.angle_slider_changed)
        angle_layout.addWidget(self.angle_label)
        angle_layout.addWidget(self.degree_slider)
        params_vlayout.addLayout(angle_layout)

        # Form layout for other parameters
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(3)  # Reduce vertical spacing
        form_layout.setHorizontalSpacing(5)  # Reduce horizontal spacing

        # Thickness (distance between lines) input
        self.thickness_spinbox = QSpinBox()
        self.thickness_spinbox.setRange(1, 200)
        self.thickness_spinbox.setValue(20)
        self.thickness_spinbox.setSuffix(" px")
        self.thickness_spinbox.valueChanged.connect(self.update_lines)
        self.thickness_spinbox.setStyleSheet("padding: 2px; font-size: 10pt;")  # Smaller font and pad
        form_layout.addRow("Line Spacing:", self.thickness_spinbox)

        # Number of lines input
        self.num_lines_spinbox = QSpinBox()
        self.num_lines_spinbox.setRange(1, 50)
        self.num_lines_spinbox.setValue(5)
        self.num_lines_spinbox.valueChanged.connect(self.update_lines)
        self.num_lines_spinbox.setStyleSheet("padding: 2px; font-size: 10pt;")  # Smaller font and pad
        form_layout.addRow("Number of Lines:", self.num_lines_spinbox)

        # Origin X input
        self.origin_x_spinbox = QSpinBox()
        self.origin_x_spinbox.setRange(-1000, 1000)
        self.origin_x_spinbox.setValue(256)
        self.origin_x_spinbox.setSuffix(" px")
        self.origin_x_spinbox.valueChanged.connect(self.update_lines)
        self.origin_x_spinbox.setStyleSheet("padding: 2px; font-size: 10pt;")  # Smaller font and pad
        form_layout.addRow("Origin X:", self.origin_x_spinbox)

        # Origin Y input
        self.origin_y_spinbox = QSpinBox()
        self.origin_y_spinbox.setRange(-1000, 1000)
        self.origin_y_spinbox.setValue(256)
        self.origin_y_spinbox.setSuffix(" px")
        self.origin_y_spinbox.valueChanged.connect(self.update_lines)
        self.origin_y_spinbox.setStyleSheet("padding: 2px; font-size: 10pt;")  # Smaller font and pad
        form_layout.addRow("Origin Y:", self.origin_y_spinbox)

        # Line length input
        self.line_length_spinbox = QSpinBox()
        self.line_length_spinbox.setRange(10, 2000)
        self.line_length_spinbox.setValue(500)
        self.line_length_spinbox.setSuffix(" px")
        self.line_length_spinbox.valueChanged.connect(self.update_lines)
        self.line_length_spinbox.setStyleSheet("padding: 2px; font-size: 10pt;")  # Smaller font and pad
        form_layout.addRow("Line Length:", self.line_length_spinbox)

        params_vlayout.addLayout(form_layout)

        # Post Processing button
        self.post_processing_btn = QPushButton("Post Processing")
        self.post_processing_btn.clicked.connect(self.post_processing)
        self.post_processing_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                border: 1px solid #666666;
                border-radius: 3px;
                padding: 3px;
                color: #ffffff;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)
        params_vlayout.addWidget(self.post_processing_btn)

        line_params_group.setLayout(params_vlayout)
        right_layout.addWidget(line_params_group)
        right_layout.addStretch()

        # Add all layouts to content layout
        content_layout.addLayout(left_layout, 1)
        content_layout.addLayout(center_layout, 3)
        content_layout.addLayout(right_layout, 1)

        # Add content to main layout
        main_layout.addLayout(content_layout)

        self.setLayout(main_layout)

    def init_database(self):
        """Initialize SQLite database for patient information"""
        self.conn = sqlite3.connect('patient_data.db')
        self.cursor = self.conn.cursor()

        # Create patients table if it doesn't exist
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                ic TEXT UNIQUE NOT NULL,
                dob TEXT NOT NULL,
                sex TEXT NOT NULL,
                height REAL,
                weight REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create MRI scans table to store image paths
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS mri_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                scan_date TEXT NOT NULL,
                folder_path TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            )
        ''')
        self.conn.commit()

    def save_patient_info(self):
        """Save patient information to database"""
        # Get values from input fields
        name = self.name_input.text().strip()
        ic = self.ic_input.text().strip()
        dob = self.dob_input.date().toString("yyyy-MM-dd")
        sex = self.sex_input.currentText()
        height = self.height_input.text().strip()
        weight = self.weight_input.text().strip()

        # Validate required fields
        if not name or not ic:
            QMessageBox.warning(self, "Validation Error", "Name and IC are required fields!")
            return

        # Validate height and weight are numbers
        try:
            height_val = float(height) if height else None
            weight_val = float(weight) if weight else None
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Height and Weight must be valid numbers!")
            return

        try:
            # Insert patient data
            self.cursor.execute('''
                INSERT INTO patients (name, ic, dob, sex, height, weight)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, ic, dob, sex, height_val, weight_val))
            self.conn.commit()

            QMessageBox.information(self, "Success", f"Patient information saved successfully!\nPatient ID: {self.cursor.lastrowid}")
            self.clear_patient_form()

        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Error", "A patient with this IC number already exists!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save patient information:\n{str(e)}")

    def clear_patient_form(self):
        """Clear all patient form fields"""
        self.name_input.clear()
        self.ic_input.clear()
        self.dob_input.setDate(QDate.currentDate())
        self.sex_input.setCurrentIndex(0)
        self.height_input.clear()
        self.weight_input.clear()

    def view_database(self):
        """Open a dialog to view all patient records"""
        try:
            # Query all patients
            self.cursor.execute('''
                SELECT id, name, ic, dob, sex, height, weight, created_at
                FROM patients
                ORDER BY id DESC
            ''')
            records = self.cursor.fetchall()

            if not records:
                QMessageBox.information(self, "Database", "No patient records found in the database.")
                return

            # Create and show dialog
            dialog = PatientDatabaseDialog(self)
            dialog.load_data(records)
            dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to retrieve patient records:\n{str(e)}")

    def go_back(self):
        """Return to front page"""
        if self.parent_window:
            self.parent_window.show()
        self.hide()

    def closeEvent(self, event):
        """Close database connection when application closes"""
        if hasattr(self, 'conn'):
            self.conn.close()
        event.accept()

    def load_images(self):
        """Load DICOM images from a directory"""
        folder_path = QFileDialog.getExistingDirectory(self, "Select DICOM Images Folder")

        if folder_path:
            # Get all DICOM files from the folder
            self.dicom_files = []
            self.current_folder_path = folder_path
            for file in sorted(os.listdir(folder_path)):
                if file.endswith('.dcm'):
                    self.dicom_files.append(os.path.join(folder_path, file))

            if self.dicom_files:
                self.slider.setEnabled(True)
                self.slider.setMaximum(len(self.dicom_files) - 1)
                self.current_index = 0
                self.slider.setValue(0)
                self.display_image(0)
                self.save_scan_button.setEnabled(True)
            else:
                self.label.setText("No DICOM files found in selected folder")
                self.save_scan_button.setEnabled(False)

    def display_image(self, index):
        """Display the DICOM image at the given index"""
        if 0 <= index < len(self.dicom_files):
            try:
                # Read DICOM file
                dicom_data = pydicom.dcmread(self.dicom_files[index])

                # Get pixel array
                pixel_array = dicom_data.pixel_array

                # Normalize to 0-255 range
                pixel_array = pixel_array.astype(np.float32)
                pixel_array = (pixel_array - pixel_array.min()) / (pixel_array.max() - pixel_array.min()) * 255
                pixel_array = pixel_array.astype(np.uint8)

                # Convert to QImage
                height, width = pixel_array.shape
                bytes_per_line = width
                q_image = QImage(pixel_array.data, width, height, bytes_per_line, QImage.Format_Grayscale8)

                # Convert to QPixmap
                self.pixmap = QPixmap.fromImage(q_image)
                self.label.setPixmap(self.pixmap)

                # Update label
                self.slider_label.setText(f"Image: {index + 1} / {len(self.dicom_files)}")
                self.current_index = index

                # Trigger repaint to draw the line
                self.update()

            except Exception as e:
                self.label.setText(f"Error loading image: {str(e)}")

    def slider_changed(self, value):
        """Handle slider value change"""
        self.display_image(value)

    def angle_slider_changed(self, value):
        """Handle angle slider value change"""
        angle = value / 10.0  # Convert from tenths to degrees
        self.angle_label.setText(f"Angle: {angle:.1f}°")
        self.label.update()

    def update_lines(self):
        """Update the display when line parameters change"""
        self.label.update()

    def post_processing(self):
        """Call kspace2Image function to convert k-space data to image"""
        try:
            # Call the kspace2image function with "Raw Data" as default folder
            kspace2Image("Raw Data")

            # Show success alert popup
            QMessageBox.information(
                self,
                "Post Processing Complete",
                "K-space to image conversion has been completed successfully!"
            )
        except Exception as e:
            # Show error alert if conversion fails
            QMessageBox.critical(
                self,
                "Post Processing Error",
                f"An error occurred during k-space to image conversion:\n{str(e)}"
            )

    def save_scan_to_patient(self):
        """Save the currently loaded MRI scan to a patient record"""
        if not self.current_folder_path or not self.dicom_files:
            QMessageBox.warning(self, "No Images", "Please load DICOM images first!")
            return

        # Get list of all patients
        try:
            self.cursor.execute('SELECT id, name, ic FROM patients ORDER BY name')
            patients = self.cursor.fetchall()

            if not patients:
                QMessageBox.warning(self, "No Patients", "No patients found in database. Please add a patient first!")
                return

            # Create a list of patient names with IC for selection
            patient_list = [f"{name} (IC: {ic})" for _, name, ic in patients]

            # Show dialog to select patient
            patient_name, ok = QInputDialog.getItem(
                self,
                "Select Patient",
                "Choose patient for this MRI scan:",
                patient_list,
                0,
                False
            )

            if ok and patient_name:
                # Get the selected patient ID
                selected_index = patient_list.index(patient_name)
                patient_id = patients[selected_index][0]

                # Get scan date
                scan_date, ok = QInputDialog.getText(
                    self,
                    "Scan Date",
                    "Enter scan date (YYYY-MM-DD):",
                    QLineEdit.Normal,
                    datetime.now().strftime("%Y-%m-%d")
                )

                if ok and scan_date:
                    # Get optional notes
                    notes, ok = QInputDialog.getText(
                        self,
                        "Scan Notes",
                        "Enter notes (optional):",
                        QLineEdit.Normal,
                        ""
                    )

                    if ok:
                        # Save scan information
                        try:
                            self.cursor.execute('''
                                INSERT INTO mri_scans (patient_id, scan_date, folder_path, notes)
                                VALUES (?, ?, ?, ?)
                            ''', (patient_id, scan_date, self.current_folder_path, notes))
                            self.conn.commit()

                            QMessageBox.information(
                                self,
                                "Success",
                                f"MRI scan saved successfully!\n"
                                f"Scan ID: {self.cursor.lastrowid}\n"
                                f"Patient: {patients[selected_index][1]}\n"
                                f"Images: {len(self.dicom_files)} files"
                            )

                        except Exception as e:
                            QMessageBox.critical(self, "Error", f"Failed to save scan:\n{str(e)}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to retrieve patients:\n{str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FrontPage()
    window.show()
    sys.exit(app.exec_())
