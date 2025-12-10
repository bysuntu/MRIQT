MRI Data Processing Library
===========================

This repository contains tools for processing raw MRI data from Firtech systems.

Main Function
=============

kspace2Image(folder)
--------------------

Converts k-space data from raw MRI files to reconstructed images.

Parameters:
    folder (str): Path to the folder containing raw MRI (.raw) files

Returns:
    list: Array of pairs [kspace, image] where:
        - kspace: numpy array of k-space data (complex64)
        - image: numpy array of reconstructed image (float32)

Description:
    This function processes all .raw files in the specified folder, 
    reads the raw k-space data, performs inverse FFT to reconstruct
    the image, and returns both the original k-space and the 
    reconstructed image as pairs.

Usage Example:
    from dataprocessingpython import kspace2Image
    
    # Process all raw files in the 'Raw Data' folder
    results = kspace2Image('Raw Data')
    
    # Access the first kspace-image pair
    kspace, image = results[0]
    
    # Work with the data
    print(f"K-space shape: {kspace.shape}")
    print(f"Image shape: {image.shape}")

Dependencies:
    - numpy
    - matplotlib (for visualization)
    - pathlib

File Format:
    The function supports the Firtech raw MRI format with specific 
    header offsets for parameters like number of samples, views, 
    slices, etc. The format supports complex 24-bit data stored in 
    32-bit slots and 16-bit ADC data.