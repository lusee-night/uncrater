"""
Coreloop-backed C wrappers used only by optional parity tests.

This module is only imported by the standalone test that verifies Python
encoder/decoder output against the original C implementation. It is not used by
runtime uncrater code, so the coreloop C shared library is not required to use
uncrater.
"""

import ctypes
import os
import platform
import numpy as np
from typing import Union


def _resolve_lib_path() -> str:
    coreloop_dir = os.environ["CORELOOP_DIR"]
    build_dir = os.path.join(coreloop_dir, "build")

    system = platform.system()
    if system == "Darwin":
        lib_name = "libcl_utils.dylib"
    elif system == "Linux":
        lib_name = "libcl_utils.so"
    else:
        raise RuntimeError(f"Unsupported platform for coreloop shared library: {system}")

    lib_path = os.path.join(build_dir, lib_name)
    if not os.path.exists(lib_path):
        raise FileNotFoundError(f"Expected coreloop shared library at {lib_path}")
    return lib_path


lib_path = _resolve_lib_path()
lib = ctypes.CDLL(lib_path)

lib.encode_10plus6.argtypes = [ctypes.c_int32]
lib.encode_10plus6.restype = ctypes.c_uint16

lib.decode_10plus6.argtypes = [ctypes.c_uint16]
lib.decode_10plus6.restype = ctypes.c_int32

lib.encode_4_into_5.argtypes = [ ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_uint16), ]
lib.encode_4_into_5.restype = None

lib.decode_5_into_4.argtypes = [ ctypes.POINTER(ctypes.c_uint16), ctypes.POINTER(ctypes.c_int32), ]
lib.decode_5_into_4.restype = None


def encode_10plus6(x: Union[int, np.array]) -> Union[int, np.array]:
    if isinstance(x, int):
        return lib.encode_10plus6(x)
    else:
        assert(x.dtype == np.int32)
        return np.array([lib.encode_10plus6(y) for y in x], dtype=np.uint16)


def decode_10plus6(x: Union[int, np.array]) -> Union[int, np.array]:
    if isinstance(x, int):
        return lib.decode_10plus6(x)
    else:
        assert(x.dtype == np.uint16)
        return np.array([lib.decode_10plus6(y) for y in x], dtype=np.int32)


def decode_5_into_4_helper(compressed_data: np.ndarray):
    array_size = compressed_data.shape[0] - 1
    assert array_size == 4
    decompressed_array = np.zeros(array_size, dtype=np.int32)
    decompressed_array = np.ascontiguousarray(decompressed_array, dtype=np.int32)

    lib.decode_5_into_4(
        compressed_data.ctypes.data_as(ctypes.POINTER(ctypes.c_uint16)),
        decompressed_array.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
    )

    return decompressed_array


def decode_5_into_4(compressed_data: np.ndarray) -> np.ndarray:
    assert compressed_data.size % 5 == 0, "Input array length must be a multiple of 5"
    num_chunks = compressed_data.size // 5
    decompressed_data = np.zeros(num_chunks * 4, dtype=np.int32)
    for i in range(num_chunks):
        chunk = compressed_data[i * 5:(i + 1) * 5]
        decompressed_data[i * 4:(i + 1) * 4] = decode_5_into_4_helper(chunk)
    return decompressed_data
