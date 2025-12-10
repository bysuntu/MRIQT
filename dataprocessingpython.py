# -*- coding: utf-8 -*-
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import scipy.fft
import os

# 固定偏移（基于手册）
OFF_NO_SAMPLES   = 0xFC00
OFF_NO_VIEWS     = 0xFC04
OFF_NO_VIEWSSEC  = 0xFC08
OFF_NO_SLICES    = 0xFC0C
OFF_DATATYPE     = 0xFC12  # 2 bytes
OFF_NO_ECHOES    = 0xFC98
OFF_NO_EXPS      = 0xFC9C
DATA_START       = 0x10108  # 真正数据起点

def read_u32_le(f, off):
    f.seek(off)
    return int.from_bytes(f.read(4), 'little', signed=False)

def read_i32_le(f, off):
    f.seek(off)
    return int.from_bytes(f.read(4), 'little', signed=True)

def read_u16_le(f, off):
    f.seek(off)
    return int.from_bytes(f.read(2), 'little', signed=False)

def parse_params(fp):
    noSamples  = read_u32_le(fp, OFF_NO_SAMPLES)
    noViews    = read_u32_le(fp, OFF_NO_VIEWS)
    noViewsSec = read_u32_le(fp, OFF_NO_VIEWSSEC)
    noSlices   = read_u32_le(fp, OFF_NO_SLICES)
    dt_code    = read_u16_le(fp, OFF_DATATYPE)
    noEchoes   = read_u32_le(fp, OFF_NO_ECHOES)
    noExps     = read_u32_le(fp, OFF_NO_EXPS)
    return dict(
        noSamples=noSamples, noViews=noViews, noViewsSec=noViewsSec,
        noSlices=noSlices, noEchoes=noEchoes, noExperiments=noExps,
        dataTypeCode=dt_code
    )

def sign_extend_24(u):
    """u: np.uint32 array of low-24-bit values"""
    v = (u & 0x00FFFFFF).astype(np.int32)
    neg = v & 0x00800000
    v[neg != 0] -= 0x01000000
    return v

def read_raw_firtech(path: Path):
    with path.open('rb') as f:
        params = parse_params(f)
        f.seek(0, 2)
        file_size = f.tell()

        # 计算总样本数
        P = params
        dims = (P["noExperiments"], P["noEchoes"], P["noSlices"],
                P["noViewsSec"], P["noViews"], P["noSamples"])
        total_points = np.prod(dims, dtype=np.int64)

        dt = P["dataTypeCode"]
        if dt in (0x00, 0x02):  # complex int (24-bit stored in 4B slots)
            bytes_per_point = 8  # I(4B) + Q(4B)
            count_u32 = total_points * 2  # I & Q
            with path.open('rb') as f2:
                f2.seek(DATA_START)
                iq_u32 = np.fromfile(f2, dtype='<u4', count=count_u32)
            if iq_u32.size != count_u32:
                raise ValueError("File too short for declared dimensions. "
                                 f"Expected {count_u32} 32-bit words, got {iq_u32.size}.")
            # 取低24位并做符号扩展
            iq24 = sign_extend_24(iq_u32)
            I = iq24[0::2]
            Q = iq24[1::2]
            data = I.astype(np.float32) + 1j * Q.astype(np.float32)
        elif dt == 0x01:  # ADC 16-bit (single channel stream)
            bytes_per_point = 2  # 仅一路，非I/Q
            with path.open('rb') as f2:
                f2.seek(DATA_START)
                data = np.fromfile(f2, dtype='<i2', count=total_points)
            if data.size != total_points:
                raise ValueError("File too short for declared dimensions (ADC).")
            data = data.astype(np.float32)  # 可按需保留为int16
        else:
            raise ValueError(f"Unknown DataTypeCode: 0x{dt:02X}")

        # 形状重排：experiments, echoes, slices, viewsSec, views, samples
        data = data.reshape(dims)

        return data, params

def kspace2Image(folder):
    """
    Convert k-space data from raw files in the specified folder to images.

    Args:
        folder (str): Path to the folder containing raw MRI files

    Returns:
        list: Array of pairs [kspace, image] converted from raw data
    """
    results = []
    folder_path = Path(folder)

    # Process all raw files in the folder
    for raw_file in folder_path.glob("*.raw"):
        try:
            # Read the raw file
            data, params = read_raw_firtech(raw_file)
            print(f"Processing {raw_file.name}, Params: {params}")

            # Extract k-space data (typically take first experiment/echo/slice for a single image)
            # Shape: (experiments, echoes, slices, viewsSec, views, samples)
            kspace = data[0, 0, 0, 0, :, :]  # (noViews, noSamples)
            print(f"K-space shape: {kspace.shape}, dtype: {kspace.dtype}")

            # Flip the k-space vertically if needed
            kspace_flipped = np.flipud(kspace)

            # Perform inverse FFT to convert k-space to image space
            image = abs(np.fft.ifftshift(np.fft.ifft2(kspace_flipped)))

            # Add the kspace-image pair to our results
            results.append([kspace, image])

        except Exception as e:
            print(f"Error processing {raw_file.name}: {str(e)}")
            continue

    return results

# Example usage (uncomment to test):
# results = kspace2Image("Raw Data")
# print(f"Converted {len(results)} files to [kspace, image] pairs")
results = kspace2Image("Raw Data")
for idx, (kspace, image) in enumerate(results):
    plt.figure(figsize=(10, 4))
    plt.subplot(1, 2, 1)
    plt.title(f"K-space {idx}")
    plt.imshow(np.log1p(np.abs(kspace)), cmap='gray')
    plt.subplot(1, 2, 2)
    plt.title(f"Image {idx}")
    plt.imshow(image, cmap='gray')
plt.show()
