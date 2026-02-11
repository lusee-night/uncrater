import ctypes
import random

import numpy as np
import pytest

from bit_utils import random_array, random_int_lz
from uncrater.c_utils import (
    decode_5_into_4 as py_decode_5_into_4,
    decode_10plus6 as py_decode_10plus6,
    encode_4_into_5 as py_encode_4_into_5,
    encode_10plus6 as py_encode_10plus6,
)

try:
    from uncrater import c_utils_coreloop as coreloop_utils
except Exception as exc:
    pytest.skip(
        f"coreloop C utils are unavailable for parity tests: {exc}",
        allow_module_level=True,
    )


c_decode_5_into_4 = coreloop_utils.decode_5_into_4
c_decode_10plus6 = coreloop_utils.decode_10plus6
c_encode_10plus6 = coreloop_utils.encode_10plus6


@pytest.fixture(autouse=True)
def seeded_rng():
    np.random.seed(42)
    random.seed(42)


def _coreloop_encode_4_into_5(vals_in: np.ndarray) -> np.ndarray:
    vals = np.ascontiguousarray(vals_in, dtype=np.int32)
    assert vals.ndim == 1 and vals.size == 4
    out = np.zeros(5, dtype=np.uint16)
    coreloop_utils.lib.encode_4_into_5(
        vals.ctypes.data_as(ctypes.POINTER(ctypes.c_int32)),
        out.ctypes.data_as(ctypes.POINTER(ctypes.c_uint16)),
    )
    return out


def _sample_signed_values_for_10plus6() -> np.ndarray:
    lzs_signs_lens = [(0, True, 1)]
    for lz in range(1, 33):
        lzs_signs_lens.append((lz, True, 3))
        lzs_signs_lens.append((lz, False, 3))
    return random_array(lzs_signs_lens=lzs_signs_lens)


def _sample_vectors_for_4_into_5() -> list[np.ndarray]:
    vectors: list[np.ndarray] = []

    for lz in [0, 1, 2, 13, 14, 15, 16, 17, 18, 19, 25, 29, 30, 31, 32]:
        for _ in range(3):
            constant = random_int_lz(lz, is_signed=True)
            vectors.append(np.full(4, constant, dtype=np.int32))

    specs = [
        [(0, True, 2), (1, False, 2)],
        [(13, False, 2), (14, True, 2)],
        [(15, False, 2), (16, True, 1), (31, False, 1)],
        [(32, False, 1), (1, True, 1), (2, False, 1), (30, True, 1)],
    ]
    for lzs_signs_lens in specs:
        vectors.append(random_array(lzs_signs_lens=lzs_signs_lens))

    lz_pool = [0, 1, 2, 15, 16, 17, 18, 19, 20, 31, 32]
    for _ in range(32):
        spec = []
        for _ in range(4):
            lz = random.choice(lz_pool)
            is_neg = True if lz == 0 else random.choice([True, False])
            spec.append((lz, is_neg, 1))
        vectors.append(random_array(lzs_signs_lens=spec))

    return vectors


def test_10plus6_scalar_exact_match():
    samples = _sample_signed_values_for_10plus6()
    for val in samples:
        val_int = int(val)
        py_encoded = int(py_encode_10plus6(val_int))
        c_encoded = int(c_encode_10plus6(val_int))
        assert py_encoded == c_encoded
        assert int(py_decode_10plus6(py_encoded)) == int(c_decode_10plus6(py_encoded))


def test_10plus6_array_exact_match():
    samples = _sample_signed_values_for_10plus6()
    py_encoded = py_encode_10plus6(samples)
    c_encoded = c_encode_10plus6(samples)
    np.testing.assert_array_equal(py_encoded, c_encoded)
    np.testing.assert_array_equal(py_decode_10plus6(py_encoded), c_decode_10plus6(py_encoded))


def test_4_into_5_and_5_into_4_exact_match():
    vectors = _sample_vectors_for_4_into_5()

    py_encoded_chunks = []
    c_encoded_chunks = []
    for vec in vectors:
        py_encoded = py_encode_4_into_5(vec)
        c_encoded = _coreloop_encode_4_into_5(vec)
        np.testing.assert_array_equal(py_encoded, c_encoded)
        py_encoded_chunks.append(py_encoded)
        c_encoded_chunks.append(c_encoded)

    py_stream = np.concatenate(py_encoded_chunks).astype(np.uint16, copy=False)
    c_stream = np.concatenate(c_encoded_chunks).astype(np.uint16, copy=False)
    np.testing.assert_array_equal(py_stream, c_stream)
    np.testing.assert_array_equal(py_decode_5_into_4(py_stream), c_decode_5_into_4(py_stream))
