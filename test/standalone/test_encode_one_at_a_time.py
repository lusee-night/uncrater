import numpy as np
import pytest
import random

from bit_utils import *
from uncrater.c_utils import decode_10plus6, encode_10plus6


@pytest.fixture
def utils_lib():
    np.random.seed(42)
    random.seed(42)
    return {
        "encode_10plus6_signed": encode_10plus6,
        "decode_10plus6_signed": decode_10plus6,
    }


def test_signed(utils_lib):
    n_reps = 10
    # only one value for signed int with 0 leading zeros, the minimal one
    lzs_signs_lens = [(0, True, 1)]
    for lz in range(1, 33):
        lzs_signs_lens.append((lz, True, n_reps))
        lzs_signs_lens.append((lz, False, n_reps))
    a = random_array(lzs_signs_lens=lzs_signs_lens)
    a_encoded = [utils_lib["encode_10plus6_signed"](x) for x in a]
    a_back = np.array(
        [utils_lib["decode_10plus6_signed"](y) for y in a_encoded], dtype=np.int32
    )
    assert all_close(a, a_back)
    assert first_k_bits_match(a, a_back, MATCHING_BITS - 3)


# if __name__ == "__main__":
#     np.random.seed(42)
#     # need to comment out fixture decorator to call like that
#     test_signed(utils_lib())
