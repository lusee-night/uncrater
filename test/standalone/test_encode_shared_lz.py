import os
import ctypes

import numpy as np
import pytest
import random

from bit_utils import *


@pytest.fixture
def utils_lib():
    np.random.seed(42)
    random.seed(42)
    utils_lib_path = os.path.join(os.environ["CORELOOP_DIR"], "build", "libcl_utils.so")
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
        "encode_pos_func": encode_pos_func,
        "decode_pos_func": decode_pos_func,
        "encode_signed_func": encode_signed_func,
        "decode_signed_func": decode_signed_func,
    }


def encode_array_pos(spectra: np.ndarray, utils_lib):
    spectra = np.ascontiguousarray(spectra, dtype=np.uint32)
    assert spectra.ndim == 1
    array_size = spectra.shape[0]

    compressed_data = np.ascontiguousarray(
        np.zeros(array_size * 4, dtype=np.uint8), dtype=np.uint8
    )

    num_bytes_written = utils_lib["encode_pos_func"](
        spectra.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32)),
        compressed_data.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte)),
        array_size,
    )

    compressed_data = compressed_data[:num_bytes_written]

    return compressed_data


def encode_array_signed(spectra, utils_lib):
    spectra = np.ascontiguousarray(spectra, dtype=np.int32)
    assert spectra.ndim == 1
    array_size = spectra.shape[0]

    compressed_data = np.ascontiguousarray(
        np.zeros(array_size * 4, dtype=np.uint8), dtype=np.uint8
    )

    num_bytes_written = utils_lib["encode_signed_func"](
        spectra.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
        compressed_data.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte)),
        array_size,
    )

    compressed_data = compressed_data[:num_bytes_written]

    return compressed_data


def decode_array_pos(compressed_data: np.ndarray, array_size: int, utils_lib):
    decompressed_array = np.zeros(array_size, dtype=np.uint32)
    decompressed_array = np.ascontiguousarray(decompressed_array, dtype=np.uint32)

    utils_lib["decode_pos_func"](
        compressed_data.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte)),
        decompressed_array.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32)),
        array_size,
    )

    return decompressed_array


def decode_array_signed(compressed_data: np.ndarray, array_size: int, utils_lib):
    decompressed_array = np.zeros(array_size, dtype=np.int32)
    decompressed_array = np.ascontiguousarray(decompressed_array, dtype=np.int32)

    utils_lib["decode_signed_func"](
        compressed_data.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte)),
        decompressed_array.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
        array_size,
    )

    return decompressed_array


def helper_test_const(constant, array_size: int, is_signed: bool, utils_lib):
    dtype = np.int32 if is_signed else np.uint32
    a = constant * np.ones(array_size, dtype=dtype)

    if is_signed:
        a_compressed = encode_array_signed(a, utils_lib)
        a_back = decode_array_signed(a_compressed, array_size, utils_lib)
    else:
        a_compressed = encode_array_pos(a, utils_lib)
        a_back = decode_array_pos(a_compressed, array_size, utils_lib)

    assert all_close(a, a_back)
    assert first_k_bits_match(a, a_back, MATCHING_BITS)


def test_constants(utils_lib):
    array_size = 10
    for is_signed in [True]:
        for lz in [0, 1, 2, 3, 4, 15, 16, 17, 25, 29, 30, 31, 32]:
            random_constant = random_int_lz(lz, is_signed)
            helper_test_const(random_constant, array_size, is_signed, utils_lib)


def test_smooth_values(utils_lib):
    array_size = 64
    x = np.linspace(0, 2 * np.pi, array_size)
    for amplitude in [2**10, 2**20, 2**30]:
        a = (np.sin(x) * amplitude).astype(np.uint32)
        a_compressed = encode_array_pos(a, utils_lib)
        a_back = decode_array_pos(a_compressed, array_size, utils_lib)
        assert all_close(a, a_back)


def test_random_input(utils_lib):
    array_size = 1024
    a = np.random.randint(0, 2**31, size=array_size, dtype=np.uint32)
    for _ in range(10):
        idx = np.random.randint(0, array_size)
        if np.random.rand() < 0.5:
            a[idx] = 2**32 - 2
        else:
            a[idx] = 0
    a_compressed = encode_array_pos(a, utils_lib)
    a_back = decode_array_pos(a_compressed, array_size, utils_lib)
    assert all_close(a, a_back)


# generate array with prescribed lz_lens and test that encode/decode works for it
def helper_lz_lens(is_signed, lzs_signs_lens, utils_lib):
    if is_signed:
        # tuple format: (# leading zeros, is_negative, length)
        array_size = sum([lz_len[2] for lz_len in lzs_signs_lens])
    else:
        # tuple format: (# leading zeros, length)
        array_size = sum([lz_len[1] for lz_len in lzs_signs_lens])

    a = random_array(lzs_signs_lens=lzs_signs_lens)

    if is_signed:
        a_compressed = encode_array_signed(a, utils_lib)
        a_back = decode_array_signed(a_compressed, array_size, utils_lib)
    else:
        a_compressed = encode_array_pos(a, utils_lib)
        a_back = decode_array_pos(a_compressed, array_size, utils_lib)

    assert all_close(a, a_back)
    assert first_k_bits_match(a, a_back, MATCHING_BITS)


def test_lz_lens_pos(utils_lib):
    lz_lens = [(0, 4), (3, 4), (2, 7), (4, 5), (31, 3), (20, 4)]
    helper_lz_lens(is_signed=False, lzs_signs_lens=lz_lens, utils_lib=utils_lib)


def test_lz_lens_signed(utils_lib):
    # all values positive: cannot have 0 leading zeros
    # fmt: off
    lz_signs_lens = [ (1, False, 4), (3, False, 4), (2, False, 7), (4, False, 5), (31, False, 3), (20, False, 4), ]
    # fmt: on
    helper_lz_lens(is_signed=True, lzs_signs_lens=lz_signs_lens, utils_lib=utils_lib)

    # fmt: off
    lz_signs_lens = [ (1, False, 4), (1, True, 3), (3, False, 4), (2, False, 7), (4, False, 5), (5, True, 9), (31, False, 3), (20, False, 4), ]
    # fmt: on
    helper_lz_lens(is_signed=True, lzs_signs_lens=lz_signs_lens, utils_lib=utils_lib)


# if __name__ == "__main__":
#     np.random.seed(42)
#     # need to comment out fixture decorator to call like that
#     test_random_input(utils_lib())
