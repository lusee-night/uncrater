import os
import ctypes
import numpy as np
import pytest
import random

ARRAY_SIZE = 2048

@pytest.fixture
def utils_lib():
    utils_lib_path = os.path.join(os.environ['CORELOOP_DIR'],'build','libcl_utils.so')
    lib = ctypes.CDLL(utils_lib_path)

    encode_pos_func = lib.encode_shared_lz_positive
    encode_pos_func.argtypes = [
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.c_int32,
    ]
    encode_pos_func.restype = int

    decode_pos_func = lib.decode_shared_lz_positive
    decode_pos_func.argtypes = [
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.c_int32,
    ]
    decode_pos_func.restype = None

    encode_signed_func = lib.encode_shared_lz_signed
    encode_signed_func.argtypes = [
        ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.c_int32,
    ]
    encode_signed_func.restype = int

    decode_signed_func = lib.decode_shared_lz_signed
    decode_signed_func.argtypes = [
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.POINTER(ctypes.c_int32),
        ctypes.c_int32,
    ]
    decode_signed_func.restype = None

    return {
        'encode_pos_func': encode_pos_func,
        'decode_pos_func': decode_pos_func,
        'encode_signed_func': encode_signed_func,
        'decode_signed_func': decode_signed_func,
    }

def encode_array_pos(spectra, utils_lib):
    spectra = np.ascontiguousarray(spectra, dtype=np.uint32)
    assert spectra.shape == (ARRAY_SIZE,), f"Input array must have shape (ARRAY_SIZE,)"

    compressed_data = np.ascontiguousarray(np.zeros(ARRAY_SIZE * 4, dtype=np.uint8), dtype=np.uint8)

    num_bytes_written = utils_lib['encode_pos_func'](
        spectra.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32)),
        compressed_data.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte)),
        ARRAY_SIZE,
    )

    compressed_data = compressed_data[:num_bytes_written]

    return compressed_data

def encode_array_signed(spectra, utils_lib):
    spectra = np.ascontiguousarray(spectra, dtype=np.int32)
    assert spectra.shape == (ARRAY_SIZE,), f"Input array must have shape (ARRAY_SIZE,)"

    compressed_data = np.ascontiguousarray(np.zeros(ARRAY_SIZE * 4, dtype=np.uint8), dtype=np.uint8)

    num_bytes_written = utils_lib['encode_signed_func'](
        spectra.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
        compressed_data.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte)),
        ARRAY_SIZE,
    )

    compressed_data = compressed_data[:num_bytes_written]

    return compressed_data


def decode_array_pos(compressed_data, utils_lib):
    decompressed_array = np.zeros(ARRAY_SIZE, dtype=np.uint32)

    utils_lib['decode_pos_func'](
        compressed_data.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte)),
        decompressed_array.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32)),
        ARRAY_SIZE,
    )

    return decompressed_array

def decode_array_signed(compressed_data, utils_lib):
    decompressed_array = np.zeros(ARRAY_SIZE, dtype=np.int32)

    utils_lib['decode_signed_func'](
        compressed_data.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte)),
        decompressed_array.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
        ARRAY_SIZE,
    )

    return decompressed_array


def print_deviation_indices(a, b, rtol, atol):
    diff = np.abs(a - b)
    tol = atol + rtol * np.abs(b)
    deviation_indices = np.where(diff > tol)
    for idx in zip(*deviation_indices):
        print(f"Deviation at index {idx}: array 1 value: {a[idx]}, array 2 value: {b[idx]}")


def all_close(a: np.ndarray, b: np.ndarray) -> bool:
    # both arrays must have finite values
    if not np.all(np.isfinite(a)):
        return False
    if not np.all(np.isfinite(b)):
        return False

    rtol = 0.1
    atol = 0.1
    if not np.allclose(a.astype(np.float64), b.astype(np.float64), rtol=rtol, atol=atol):
        # ic(a, b, np.abs(a - b), rtol * np.abs(b), np.abs(a - b) - rtol * np.abs(b))
        print_deviation_indices(a, b, rtol, atol)
    return np.allclose(a.astype(np.float64), b.astype(np.float64), rtol=rtol, atol=atol)


# return random int32 with specified number of leading zeros of its absolute value
def random_int_lz(lz, is_signed):
    assert 0 <= lz <= 32

    if lz == 32:
        return 0
    elif lz == 31:
        value = 1
    elif lz == 0 and is_signed:
        return np.iinfo(np.int32).min
    else:
        base_value = 1 << (32 - lz - 1)
        random_part = random.randint(0, (1 << (32 - lz - 1)) - 1)
        value = base_value + random_part

    if is_signed:
        if lz == 0:
            sign = -1
        else:
            sign = random.choice([-1, 1])
        value *= sign

    if is_signed:
        assert(np.iinfo(np.int32).min <= value <= np.iinfo(np.int32).max)
    else:
        assert(np.iinfo(np.uint32).min <= value <= np.iinfo(np.uint32).max)

    return value

def helper_test_const(constant, is_signed, utils_lib):
    dtype = np.int32 if is_signed else np.uint32
    a = constant * np.ones(ARRAY_SIZE, dtype=dtype)

    if is_signed:
        a_compressed = encode_array_signed(a, utils_lib)
        a_back = decode_array_signed(a_compressed, utils_lib)
    else:
        a_compressed = encode_array_pos(a, utils_lib)
        a_back = decode_array_pos(a_compressed, utils_lib)

    assert all_close(a, a_back)

def test_constants(utils_lib):
    for is_signed in [True, False]:
        for lz in [0, 1, 2, 3, 4, 15, 16, 17, 25, 29, 30, 31, 32]:
            random_constant = random_int_lz(lz, is_signed)
            helper_test_const(random_constant, is_signed, utils_lib)


def test_smooth_values(utils_lib):
    x = np.linspace(0, 2 * np.pi, ARRAY_SIZE)
    for amplitude in [2 ** 10, 2 ** 20, 2 ** 30]:
        a = (np.sin(x) * amplitude).astype(np.uint32)
        a_compressed = encode_array_pos(a, utils_lib)
        a_back = decode_array_pos(a_compressed, utils_lib)
        assert all_close(a, a_back)


def test_random_input(utils_lib):
    a = np.random.randint(0, 2 ** 31, size=ARRAY_SIZE, dtype=np.uint32)
    for _ in range(10):
        idx = np.random.randint(0, ARRAY_SIZE)
        if np.random.rand() < 0.5:
            a[idx] = 2 ** 32 - 2
        else:
            a[idx] = 0
    a_compressed = encode_array_pos(a, utils_lib)
    a_back = decode_array_pos(a_compressed, utils_lib)
    assert all_close(a, a_back)


# if __name__ == "__main__":
#     np.random.seed(42)
#     # need to comment out fixture decorator to call like that
#     test_random_input(utils_lib())
