import random
import typing
import numpy as np

MATCHING_BITS = 13


def print_deviation_indices(a, b, rtol, atol):
    diff = np.abs(a - b)
    tol = atol + rtol * np.abs(b)
    deviation_indices = np.where(diff > tol)
    for idx in zip(*deviation_indices):
        print(
            f"Deviation at index {idx}: array 1 value: {a[idx]}, array 2 value: {b[idx]}"
        )


def all_close(a: np.ndarray, b: np.ndarray) -> bool:
    # both arrays must have finite values
    if not np.all(np.isfinite(a)):
        return False
    if not np.all(np.isfinite(b)):
        return False

    rtol = 0.1
    atol = 0.1
    if not np.allclose(
        a.astype(np.float64), b.astype(np.float64), rtol=rtol, atol=atol
    ):
        # ic(a, b, np.abs(a - b), rtol * np.abs(b), np.abs(a - b) - rtol * np.abs(b))
        print_deviation_indices(a, b, rtol, atol)
    return np.allclose(a.astype(np.float64), b.astype(np.float64), rtol=rtol, atol=atol)


def first_k_bits_match(original: np.ndarray, back: np.ndarray, k: int) -> bool:
    """
    Verifies that the first k most significant bits in the corresponding elements of arrays `original` and `back`
    are the same. Also checks that the signs of every corresponding element in `original` and `back` are the same.

    Parameters:
    - original (np.ndarray): First array of integers (np.int32 or np.uint32).
    - back (np.ndarray): Second array of integers (np.int32 or np.uint32).
    - k (int): Number of most significant bits to compare.

    Returns:
    - bool: True if the first `k` most significant bits match for all corresponding elements, False otherwise.
    """

    if original.shape != back.shape:
        raise ValueError("Input arrays must have the same shape")

    if original.dtype not in [np.int32, np.uint32] or back.dtype not in [
        np.int32,
        np.uint32,
    ]:
        raise ValueError("Arrays must be of type np.int32 or np.uint32")

    if np.any((original < 0) != (back < 0)):
        return False

    # convert to 64 bits to avoid overflow in bits_required calculation (adding 1 there)
    original_abs = np.abs(original).astype(np.uint64)
    back_abs = np.abs(back).astype(np.uint64)

    bits_required = np.floor(np.log2(original_abs + 1)).astype(np.uint64) + 1
    shift_by = np.maximum(bits_required - k, 0)

    original_shifted = original_abs >> shift_by
    back_shifted = back_abs >> shift_by

    return np.all(original_shifted == back_shifted)


# return random int32 with specified number of leading zeros of its absolute value
def random_int_lz(lz: int, is_signed: bool, is_neg: typing.Optional[bool] = None):
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
        if is_neg is None:
            if lz == 0:
                sign = -1
            else:
                sign = random.choice([-1, 1])
        else:
            assert is_neg or lz > 0
            sign = -1 if is_neg else 1
        value *= sign

    if is_signed:
        assert np.iinfo(np.int32).min <= value <= np.iinfo(np.int32).max
    else:
        assert np.iinfo(np.uint32).min <= value <= np.iinfo(np.uint32).max

    return value


def random_array(
    lzs_signs_lens: typing.Union[
        typing.List[typing.Tuple[int, int]], typing.List[typing.Tuple[int, bool, int]]
    ]
) -> np.ndarray:
    """
    Generate an array of random numbers with prescribed segments that have the same leading zeros.

    Parameters:
    - lzs_signs_lens (List[Tuple[int, int]] or List[Tuple[int, bool, int]]):
      If is_signed is False, contains tuples (lz_1, len_1), (lz_2, len_2), etc.
      If is_signed is True, contains tuples (lz_1, is_neg_1, len_1), (lz_2, is_neg_2, len_2), etc.

    Returns:
    - np.ndarray: An array where its first len_1 elements have lz_1 leading zeros and the prescribed sign,
                  the next len_2 elements have lz_2 leading zeros and the prescribed sign, etc.
    """

    assert len(lzs_signs_lens[0]) in [2, 3]
    is_signed = len(lzs_signs_lens[0]) == 3
    dtype = np.int32 if is_signed else np.uint32
    result = []

    for item in lzs_signs_lens:
        if is_signed:
            lz, is_neg, length = item
        else:
            lz, length = item
            is_neg = False

        segment = [
            random_int_lz(lz, is_signed=is_signed, is_neg=is_neg) for _ in range(length)
        ]
        result.extend(segment)

    return np.array(result, dtype=dtype)
