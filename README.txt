MRI DICOM System
================

This repository contains a PyQt5-based application for viewing and processing MRI DICOM images. The application provides a comprehensive interface for medical professionals to view MRI scans, add annotation lines, manage patient information, and save scans to patient records.

Features
========

1. Main Menu Interface:
   - Four main buttons: Connection, Operation, Checking, and Viewing
   - Dark theme UI for better visualization of medical images
   - Frameless window with custom close button

2. Connection Module:
   - Integration with MRI hardware systems
   - Connection status indicator with visual feedback
   - Hardware initialization and configuration

3. DICOM Viewer (Operation Module):
   - Load and view DICOM image sequences
   - Interactive slider to navigate through image stacks
   - Display of multiple image slices
   - Custom line annotation tools with adjustable parameters

4. Patient Management:
   - Patient demographics form (name, IC, date of birth, sex, height, weight)
   - SQLite database for patient information storage
   - Save patient records to database
   - View all patient records in a table
   - Link MRI scans to patient records

5. Annotation Tools:
   - Adjustable line parameters (angle, spacing, number, origin, length)
   - Real-time drawing of multiple parallel lines on images
   - Visual indicators for measurement tools

Main Components
===============

FrontPage Class
---------------
The main entry point of the application with four primary modules:
- Connection: Checks MRI hardware connectivity
- Operation: Open the DICOM viewer interface
- Checking: Placeholder for future functionality
- Viewing: Placeholder for future functionality

ImageWithLine Class
-------------------
The core DICOM viewing interface with:
- Patient demographics form
- DICOM image display area
- Image navigation slider
- Line annotation controls
- Database integration for patient records

ImageLabel Class
----------------
Custom QLabel that extends the basic label with:
- Drawing capabilities to overlay lines on images
- Real-time updating of annotation lines
- Coordinate transformations for proper rendering

PatientDatabaseDialog Class
---------------------------
Modal dialog for viewing patient records:
- Displays patient data in a table format
- Shows ID, name, IC, date of birth, sex, height, weight, and creation time
- Read-only interface for patient data

Database Schema
===============

The application uses SQLite for patient information storage:
1. `patients` table:
   - id: Primary key (auto-increment)
   - name: Patient name (text, not null)
   - ic: Identification card number (unique, not null)
   - dob: Date of birth (text, not null)
   - sex: Patient sex (text, not null)
   - height: Patient height in cm (real)
   - weight: Patient weight in kg (real)
   - created_at: Record creation timestamp

2. `mri_scans` table:
   - id: Primary key (auto-increment)
   - patient_id: Foreign key referencing patients table
   - scan_date: Date of the MRI scan
   - folder_path: Path to the DICOM files
   - notes: Optional notes about the scan
   - created_at: Record creation timestamp

DICOM Processing
================

The application supports loading and displaying DICOM images with:
- Grayscale rendering of DICOM pixel data
- Proper normalization of pixel values
- Support for image stacks with navigation controls
- Integration with the kspace2Image function for raw MRI data processing

Line Annotation System
======================

The annotation system allows users to:
- Draw multiple parallel lines on images
- Adjust line angle (0-360 degrees)
- Control line spacing in pixels
- Set number of parallel lines to draw
- Specify origin point (X, Y coordinates)
- Control line length in pixels
- Visually distinguish lines with dotted red lines

Dependencies
============
- Python 3.x
- PyQt5
- numpy
- pydicom
- sqlite3
- math
- dataprocessingpython.py (for kspace to image conversion)
- test_basic.py (for connection testing)

File Structure
==============
- mriQt.py: Main application code
- dataprocessingpython.py: K-space to image conversion functions
- test_basic.py: Hardware connection testing functions
- patient_data.db: SQLite database for patient information
- icons/: Directory containing SVG icons for UI buttons
- mriImages/: Directory for processed images
- Raw Data/: Directory for raw MRI data files
- Processed Data/: Directory for processed data

Usage
=====
1. Run `python mriQt.py` to start the application
2. Use the Connection module to check MRI hardware connectivity
3. Use the Operation module to load and view DICOM images
4. Enter patient information in the demographics form
5. Save patient information to the database
6. Use the annotation tools to draw measurement lines on images
7. Save scans to patient records linking them to specific patients

Connection Testing
==================
The application integrates with MRI hardware through a C++ DLL wrapper.
The connection test performs:
- System initialization
- Hardware configuration
- Channel setup
- Output path configuration
- Safe system closure

The connection status is displayed with visual indicators:
- Green checkmark (✓) for successful connection
- Red cross (×) for failed connection
- Clock icon (🕐) during connection attempt

Patient Information Workflow
============================
1. Fill in patient demographics (name, IC required)
2. Validate and save patient information to database
3. Load DICOM images into the viewer
4. Select a patient from the database
5. Link the MRI scan to the selected patient
6. Store scan metadata (date, file path, notes) in database

Line Annotation Parameters
==========================
- Angle: Rotation of the main line (0-360 degrees)
- Line Spacing: Distance between parallel lines in pixels
- Number of Lines: Count of parallel lines to draw
- Origin X, Y: Center point for line positioning
- Line Length: Length of each individual line in pixels

The annotations are drawn using red dotted lines that are overlaid on the medical images in real-time as parameters are adjusted.

Data Processing Integration
===========================
The application includes integration with the kspace2Image function from the dataprocessingpython.py file for converting raw k-space data to reconstructed images. This allows for:

- Processing raw MRI data files
- Converting k-space to image space using inverse FFT
- Flipping k-space data as needed for proper reconstruction
- Handling multiple data formats (complex 24-bit, 16-bit ADC)
