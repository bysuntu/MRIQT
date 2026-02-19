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
                             QHeaderView, QInputDialog, QTextEdit, QDesktopWidget)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QImage, QIcon, QColor
from PyQt5.QtCore import Qt, QPointF, QDate, QSize, QTimer
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
        self.loading_angle = 0  # For animation
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(200)  # Update every 200ms for slower rotation

    def update_animation(self):
        """Update loading animation angle"""
        if not self.pixmap() or self.pixmap().isNull():
            self.loading_angle = (self.loading_angle + 3) % 360
            self.update()

    def paintEvent(self, event):
        # If no pixmap, draw loading animation
        if not self.pixmap() or self.pixmap().isNull():
            painter = QPainter(self)
            painter.fillRect(event.rect(), self.palette().color(self.backgroundRole()))
            
            # Draw rotating loading spinner
            center_x = self.width() // 2
            center_y = self.height() // 2
            
            # Draw rotating circle spinner animation
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Draw dots in a circle
            num_dots = 8
            radius = 40
            for i in range(num_dots):
                angle = (i * 360 / num_dots + self.loading_angle) % 360
                angle_rad = math.radians(angle)
                
                x = center_x + radius * math.cos(angle_rad)
                y = center_y + radius * math.sin(angle_rad)
                
                # Opacity based on position
                opacity = 255 * (i + 1) // num_dots
                color = QColor(100, 150, 255, opacity)
                
                painter.setBrush(color)
                painter.drawEllipse(int(x) - 4, int(y) - 4, 8, 8)
            
            # Draw loading text
            painter.setPen(QColor(200, 200, 200))
            painter.setFont(self.font())
            painter.drawText(event.rect(), Qt.AlignHCenter | Qt.AlignBottom, "Loading DICOM images...")
        else:
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
        self.setFixedSize(450, 100)  # Compact size to fit title bar and buttons
        # Center on screen
        screen = QDesktopWidget().screenGeometry()
        self.move((screen.width() - 450) // 2, (screen.height() - 100) // 2)

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
        layout.setContentsMargins(0, 0, 0, 0)  # No margins
        layout.setSpacing(0)  # No spacing between elements

        # Title bar with close button
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 0)  # No margins
        title_bar.setSpacing(0)  # No spacing between elements

        # Close button (drawn icon)
        close_btn = QPushButton()
        close_btn.setFixedSize(28, 28)
        close_pixmap = QPixmap(16, 16)
        close_pixmap.fill(Qt.transparent)
        painter = QPainter(close_pixmap)
        painter.setPen(QPen(Qt.white, 2))
        painter.drawLine(2, 2, 13, 13)
        painter.drawLine(13, 2, 2, 13)
        painter.end()
        close_btn.setIcon(QIcon(close_pixmap))
        close_btn.setIconSize(QSize(16, 16))
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 0px;
                padding: 0px;
                margin: 0px;
                width: 28px;
                height: 28px;
            }
            QPushButton:hover {
                background-color: #ff0000;
            }
            QPushButton:pressed {
                background-color: #cc0000;
            }
        """)
        close_btn.clicked.connect(self.close)
        title_bar.addStretch()
        title_bar.addWidget(close_btn)
        
        # Wrap title bar in widget
        title_bar_widget = QWidget()
        title_bar_widget.setLayout(title_bar)
        title_bar_widget.setFixedHeight(28)  # Fixed minimal height for close button
        layout.addWidget(title_bar_widget, 0)

        # Create horizontal layout for buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)  # Very small spacing between buttons
        button_layout.setContentsMargins(10, 0, 10, 0)  # Minimal margins

        button_size = 60

        # Store connection icon paths for state changes
        icons_dir = os.path.join(os.path.dirname(__file__), "icons")
        self.connection_icon_default = os.path.join(icons_dir, "connection.svg")
        self.connection_icon_connecting = os.path.join(icons_dir, "connecting.svg")
        self.connection_icon_connected = os.path.join(icons_dir, "connected.svg")

        # Connection button
        self.connection_btn = QPushButton()
        self.connection_btn.clicked.connect(self.open_connection)
        self.connection_btn.setFixedSize(button_size, button_size)

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

        # Set SVG icon for connection button
        if os.path.exists(self.connection_icon_default):
            self.connection_btn.setIcon(QIcon(self.connection_icon_default))
            self.connection_btn.setIconSize(QSize(button_size - 6, button_size - 6))
            self.connection_btn.setToolTip("Connection")
        else:
            self.connection_btn.setText("Connection")

        button_layout.addWidget(self.connection_btn)

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

        # Wrap button layout in widget
        button_widget = QWidget()
        button_widget.setLayout(button_layout)
        button_widget.setFixedHeight(60)  # Fixed height to match button size
        layout.addWidget(button_widget, 0)

        self.setLayout(layout)

        # Reference to operation window
        self.operation_window = None

        # For window dragging
        self._drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def open_connection(self):
        """Open connection interface and check connection status"""
        # Show connecting icon (yellow) while checking
        if os.path.exists(self.connection_icon_connecting):
            self.connection_btn.setIcon(QIcon(self.connection_icon_connecting))
        QApplication.processEvents()  # Update UI immediately

        try:
            # Call checkConnection function
            result = checkConnection()

            if result == 0:
                # Success - show connected icon (green)
                if os.path.exists(self.connection_icon_connected):
                    self.connection_btn.setIcon(QIcon(self.connection_icon_connected))
                self.show_auto_close_message("Connection", f"Connection successful!\nReturn code: {result}")
            else:
                # Failure - revert to default disconnected icon
                if os.path.exists(self.connection_icon_default):
                    self.connection_btn.setIcon(QIcon(self.connection_icon_default))
                self.show_auto_close_message("Connection", f"Connection failed!\nReturn code: {result}")

        except Exception as e:
            # Error - revert to default disconnected icon
            if os.path.exists(self.connection_icon_default):
                self.connection_btn.setIcon(QIcon(self.connection_icon_default))
            self.show_auto_close_message("Connection Error", f"Error during connection:\n{str(e)}")

    def show_auto_close_message(self, title, text, duration=5000):
        """Show a message dialog that auto-closes after duration (ms)"""
        msg = QMessageBox(self)
        msg.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        msg.setText(text)
        msg.setStandardButtons(QMessageBox.NoButton)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #2b2b2b;
                border: 1px solid #666666;
            }
            QLabel {
                color: #ffffff;
                font-size: 12pt;
                padding: 10px;
            }
        """)
        QTimer.singleShot(duration, msg.accept)
        msg.exec_()

    def open_operation(self):
        """Open operation interface (current GUI)"""
        if self.operation_window is None:
            self.operation_window = ImageWithLine(parent=self)
        self.operation_window.show()
        self.hide()

    def open_checking(self):
        """Open checking interface"""
        self.show_auto_close_message("Checking", "Checking module - Coming soon!")

    def open_viewing(self):
        """Open viewing interface"""
        self.show_auto_close_message("Viewing", "Viewing module - Coming soon!")

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

        # Top bar with close button
        top_bar = QHBoxLayout()
        top_bar.addStretch()

        icons_dir = os.path.join(os.path.dirname(__file__), "icons")

        # Style shared by title bar buttons
        titlebar_btn_style = """
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 0px;
                color: #ffffff;
                padding: 0px;
                margin: 0px;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: {pressed};
            }}
        """

        # Maximize button
        self.maximize_btn = QPushButton()
        self.maximize_btn.setFixedSize(30, 30)
        maximize_icon = QIcon(os.path.join(icons_dir, "maximize.svg")) if os.path.exists(os.path.join(icons_dir, "maximize.svg")) else QIcon()
        if maximize_icon.isNull():
            # Draw a square icon programmatically
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setPen(QPen(Qt.white, 2))
            painter.drawRect(1, 1, 13, 13)
            painter.end()
            maximize_icon = QIcon(pixmap)
        self.maximize_btn.setIcon(maximize_icon)
        self.maximize_btn.setIconSize(QSize(16, 16))
        self.maximize_btn.setStyleSheet(titlebar_btn_style.format(hover="#5a5a5a", pressed="#3a3a3a"))
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        top_bar.addWidget(self.maximize_btn)

        # Close button (returns to main menu)
        close_btn = QPushButton()
        close_btn.setFixedSize(30, 30)
        # Draw an X icon programmatically
        close_pixmap = QPixmap(16, 16)
        close_pixmap.fill(Qt.transparent)
        painter = QPainter(close_pixmap)
        painter.setPen(QPen(Qt.white, 2))
        painter.drawLine(2, 2, 13, 13)
        painter.drawLine(13, 2, 2, 13)
        painter.end()
        close_btn.setIcon(QIcon(close_pixmap))
        close_btn.setIconSize(QSize(16, 16))
        close_btn.setStyleSheet(titlebar_btn_style.format(hover="#ff0000", pressed="#cc0000"))
        close_btn.clicked.connect(self.go_back)
        top_bar.addWidget(close_btn)

        main_layout.addLayout(top_bar)

        # Content layout
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(5, 5, 5, 5)  # Reduce margins
        content_layout.setSpacing(5)  # Reduce spacing between sections

        # Left side - Patient Demographics
        left_layout = QVBoxLayout()
        left_layout.setSpacing(3)  # Reduce spacing between elements

        # Patient information group box with icon in title
        patient_info_group = QGroupBox()
        patient_info_group.setStyleSheet("""
            QGroupBox {
                font-size: 10pt;
                padding-top: 10px;
                margin-top: 8px;
                border: 1px solid #555555;
                border-radius: 3px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
        """)
        
        # Create header layout with icon and title
        patient_header_layout = QHBoxLayout()
        patient_header_layout.setContentsMargins(0, 0, 0, 0)
        patient_header_layout.setSpacing(6)
        
        # Add icon
        patient_icon_label = QLabel()
        patient_icon = QIcon("icons/icon_patient info.svg")
        patient_icon_label.setPixmap(patient_icon.pixmap(QSize(36, 36)))
        patient_header_layout.addWidget(patient_icon_label)
        
        # Add title
        patient_title_label = QLabel("Patient Information")
        patient_title_label.setStyleSheet("font-size: 11pt; font-weight: bold; color: white;")
        patient_header_layout.addWidget(patient_title_label)
        patient_header_layout.addStretch()
        
        # Create header widget
        patient_header_widget = QWidget()
        patient_header_widget.setLayout(patient_header_layout)
        
        # Create a container layout for the group box
        patient_container_layout = QVBoxLayout()
        patient_container_layout.setContentsMargins(0, 0, 0, 0)
        patient_container_layout.setSpacing(0)
        patient_container_layout.addWidget(patient_header_widget)
        
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

        # Add form to container layout
        patient_container_layout.addLayout(patient_form)
        patient_info_group.setLayout(patient_container_layout)
        patient_info_group.setMinimumHeight(350)  # Set adequate height for content
        
        # Add group box to left layout
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
        line_params_group = QGroupBox()
        line_params_group.setStyleSheet("""
            QGroupBox {
                font-size: 10pt;
                padding-top: 10px;
                margin-top: 8px;
                border: 1px solid #555555;
                border-radius: 3px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
        """)
        
        # Create header layout with icon and title
        line_header_layout = QHBoxLayout()
        line_header_layout.setContentsMargins(0, 0, 0, 0)
        line_header_layout.setSpacing(6)
        
        # Add icon
        line_icon_label = QLabel()
        line_icon = QIcon("icons/icon_setting.svg")
        line_icon_label.setPixmap(line_icon.pixmap(QSize(36, 36)))
        line_header_layout.addWidget(line_icon_label)
        
        # Add title
        line_title_label = QLabel("Lines Parameters")
        line_title_label.setStyleSheet("font-size: 11pt; font-weight: bold; color: white;")
        line_header_layout.addWidget(line_title_label)
        line_header_layout.addStretch()
        
        # Create header widget
        line_header_widget = QWidget()
        line_header_widget.setLayout(line_header_layout)
        
        # Create a container layout for the group box
        line_container_layout = QVBoxLayout()
        line_container_layout.setContentsMargins(0, 0, 0, 0)
        line_container_layout.setSpacing(0)
        line_container_layout.addWidget(line_header_widget)
        
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

        # Add form layout to container
        line_container_layout.addLayout(params_vlayout)
        line_params_group.setLayout(line_container_layout)
        right_layout.addWidget(line_params_group)
        right_layout.addStretch()

        # Add all layouts to content layout
        content_layout.addLayout(left_layout, 1)
        content_layout.addLayout(center_layout, 3)
        content_layout.addLayout(right_layout, 1)

        # Add content to main layout
        main_layout.addLayout(content_layout)

        self.setLayout(main_layout)

        # For window dragging
        self._drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

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

    def toggle_maximize(self):
        """Toggle between maximized and normal window state"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

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
