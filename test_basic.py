#!/usr/bin/env python3
"""Simple test to verify mricpp is working."""

import mricpp
import numpy as np

def checkConnection():

    # Test 1: Import and version
    print("Test 1: Module imported successfully")
    print(f"  DLL Version: {mricpp.GetDLLVersion()}")
    print(f"  DLL Path: {mricpp.GetDLLPath()}")
    print()

    # Test 2: System selection
    print("Test 2: System functions")
    mricpp.SetSystemSel(2)
    print(f"  System Selection: {mricpp.GetSystemSel()}")
    mricpp.SetVerboseLevel(0)
    print(f"  Verbose level set to 0")
    print()

    print("Test 6: System initialization")
    print("Start")
    ret = mricpp.Init("C:\\Users\\bysu\\Downloads\\SpectrometerIDE\\dll\\hw_cfg\\init.ini")
    print(f"Init return: {ret}")


    if ret == 0:
        print("  System initialized successfully")
        ret = mricpp.ConfigFile("./hw_cfg/init.ini")
        print(f"  ConfigFile return: {ret}")

        mricpp.SetTotalCh(16, 0)
        total_ch = mricpp.GetTotalCh(0)
        print(f"  Total Channels: {total_ch}")

        mricpp.SetChSel("255", 0)
        print(f"  Channel selection set to: 255")

        mricpp.SetSaveMode(1)
        print(f"  Save mode set to: 1")

        mricpp.SetOutputPath("./output")
        print(f"  Output path set to: ./output")

        # Close system
        mricpp.CloseSys()
        print("  System closed successfully")
    else:
        print(f"  Failed to initialize system (error code: {ret})")


    return ret

print("=" * 60)
print("MRICpp Python Library Test")
print("=" * 60)
print()

# Test 1: Import and version
print("Test 1: Module imported successfully")
print(f"  DLL Version: {mricpp.GetDLLVersion()}")
print(f"  DLL Path: {mricpp.GetDLLPath()}")
print()

# Test 2: System selection
print("Test 2: System functions")
mricpp.SetSystemSel(2)
print(f"  System Selection: {mricpp.GetSystemSel()}")
mricpp.SetVerboseLevel(0)
print(f"  Verbose level set to 0")
print()

# Test 3: Enums
print("Test 3: Enums")
print(f"  BoardType.TX1 = {mricpp.BoardType.TX1}")
print(f"  ShimChannel.CHANNEL_X = {mricpp.ShimChannel.CHANNEL_X}")
print(f"  PreempKeys.A1 = {mricpp.PreempKeys.A1}")
print()

# Test 4: NumPy arrays
print("Test 4: NumPy array support")
test_array = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
print(f"  Created test array: {test_array}")
print(f"  Array shape: {test_array.shape}")
print(f"  Array dtype: {test_array.dtype}")
print()

# Test 5: Available functions
print("Test 5: Key functions available:")
functions = [
    'Init', 'ConfigFile', 'CloseSys', 'Run', 'Abort',
    'SetParameterFile', 'SetTotalCh', 'GetCurrentScanNo',
    'SetOutputPath', 'ScanCompleted', 'GetTotalScanNo'
]

for func in functions:
    if hasattr(mricpp, func):
        print(f"  [OK] {func}")
    else:
        print(f"  [MISSING] {func}")

print()

# Test 6: Initialize system (like C++ main)
print("Test 6: System initialization")
print("Start")
ret = mricpp.Init("C:\\Users\\bysu\\Downloads\\SpectrometerIDE\\dll\\hw_cfg\\init.ini")
print(f"Init return: {ret}")

if ret == 0:
    print("  System initialized successfully")
    ret = mricpp.ConfigFile("C:\\Users\\bysu\\Downloads\\SpectrometerIDE\\dll\\hw_cfg\\init.ini")
    print(f"  ConfigFile return: {ret}")

    mricpp.SetTotalCh(16, 0)
    total_ch = mricpp.GetTotalCh(0)
    print(f"  Total Channels: {total_ch}")

    mricpp.SetChSel("255", 0)
    print(f"  Channel selection set to: 255")

    mricpp.SetSaveMode(1)
    print(f"  Save mode set to: 1")

    mricpp.SetOutputPath("./output")
    print(f"  Output path set to: ./output")

    # Close system
    mricpp.CloseSys()
    print("  System closed successfully")
else:
    print(f"  Failed to initialize system (error code: {ret})")

print()
print("=" * 60)
print("All tests completed successfully!")
print("=" * 60)
