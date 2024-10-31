import os
import ctypes

import itertools

import numpy as np
import pytest
import random

from icecream import ic

from bit_utils import *


# @pytest.fixture
def utils_lib():
    np.random.seed(42)
    random.seed(42)
    utils_lib_path = os.path.join(os.environ["CORELOOP_DIR"], "build", "libcl_utils.so")
    lib = ctypes.CDLL(utils_lib_path)

    encode_signed_func = lib.encode_4_into_5
    encode_signed_func.argtypes = [
        ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_uint16),
    ]
    encode_signed_func.restype = None

    decode_signed_func = lib.decode_5_into_4
    decode_signed_func.argtypes = [
        ctypes.POINTER(ctypes.c_uint16),
        ctypes.POINTER(ctypes.c_int32),
    ]
    decode_signed_func.restype = None

    return {
        "encode_func": encode_signed_func,
        "decode_func": decode_signed_func,
    }


def encode_array(spectra, utils_lib):
    assert spectra.ndim == 1 and spectra.shape[0] == 4
    spectra = np.ascontiguousarray(spectra, dtype=np.int32)
    array_size = spectra.shape[0]

    compressed_data = np.ascontiguousarray(np.zeros(array_size + 1, dtype=np.uint16), dtype=np.uint16)

    utils_lib["encode_func"](
        spectra.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
        compressed_data.ctypes.data_as(ctypes.POINTER(ctypes.c_uint16)),
    )

    return compressed_data


def decode_array(compressed_data: np.ndarray, utils_lib):
    array_size = compressed_data.shape[0] - 1
    assert array_size == 4
    decompressed_array = np.zeros(array_size, dtype=np.int32)
    decompressed_array = np.ascontiguousarray(decompressed_array, dtype=np.int32)

    utils_lib["decode_func"](
        compressed_data.ctypes.data_as(ctypes.POINTER(ctypes.c_uint16)),
        decompressed_array.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
    )

    return decompressed_array


def helper_test_const(constant, is_signed: bool, utils_lib):
    array_size = 4
    dtype = np.int32 if is_signed else np.uint32
    a = constant * np.ones(array_size, dtype=dtype)

    a_compressed = encode_array(a, utils_lib)
    a_back = decode_array(a_compressed, utils_lib)
    assert all_close(a, a_back)
    assert first_k_bits_match(a, a_back, MATCHING_BITS)


def test_constants(utils_lib):
    for is_signed in [True]:
        for lz in [0, 1, 2, 3, 4, 13, 14, 15, 16, 17, 18, 19, 25, 29, 30, 31, 32]:
            for _ in range(10):
                random_constant = random_int_lz(lz, is_signed)
                helper_test_const(random_constant, is_signed, utils_lib)


def helper_lz_lens(lzs_signs_lens, utils_lib):
    array_size = sum([lz_len[2] for lz_len in lzs_signs_lens])
    assert array_size == 4
    a = random_array(lzs_signs_lens=lzs_signs_lens)

    a_compressed = encode_array(a, utils_lib)
    a_back = decode_array(a_compressed, utils_lib)
    if not all_close(a, a_back):
        ic(lzs_signs_lens, a, a_back)

    assert all_close(a, a_back)
    assert first_k_bits_match(a, a_back, MATCHING_BITS)


def test_lz_lens(utils_lib):
    variants = []
    lzs = [0, 1, 2, 13, 14, 15, 16, 17, 18, 19, 20, 30, 31, 32]
    pairs = list(itertools.product(lzs, repeat=2))
    sign_pairs = list(itertools.product([True, False], repeat=2))
    for lz_1, lz_2 in pairs:
        for sign_1, sign_2 in sign_pairs:
            variants.append([(lz_1, sign_1, 2), (lz_2, sign_2, 2)])

    lzs = [0, 1, 2, 15, 16, 17, 18, 19, 20, 31, 32]
    triples = list(itertools.product(lzs, repeat=3))
    sign_triples = list(itertools.product([True, False], repeat=3))
    for lz_1, lz_2, lz_3 in triples:
        for sign_1, sign_2, sign_3 in sign_triples:
            variants.append([(lz_1, sign_1, 2), (lz_2, sign_2, 1), (lz_3, sign_3, 1)])
            variants.append([(lz_1, sign_1, 1), (lz_1, sign_2, 1), (lz_2, sign_2, 1), (lz_3, sign_3, 1)])

    for lz_signs_lens in variants:
        helper_lz_lens(lzs_signs_lens=lz_signs_lens, utils_lib=utils_lib)



if __name__ == "__main__":
    np.random.seed(42)
    # need to comment out fixture decorator to call like that
    # for _ in range(10):
    #     lzs_signs_lens = [(32, True, 2), (0, True, 2)]
    #     helper_lz_lens(lzs_signs_lens=lzs_signs_lens, utils_lib=utils_lib())

    test_constants(utils_lib())
    test_lz_lens(utils_lib())
