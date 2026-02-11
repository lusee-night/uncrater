import numpy as np
from typing import Union

INT32_MIN = -(2**31)
INT32_MAX = 2**31 - 1


def _safe_abs_int32(val: int) -> int:
    if val >= 0:
        return val
    if val == INT32_MIN:
        return -INT32_MIN
    return -val


def _clz32(val: int) -> int:
    if val == 0:
        return 32
    return 32 - val.bit_length()


def _get_shift_by(val: int) -> int:
    lz = _clz32(val & 0xFFFFFFFF)
    return max(16 - lz + 1, 0)


def encode_10plus6(x: Union[int, np.ndarray]) -> Union[int, np.ndarray]:
    if isinstance(x, np.ndarray):
        assert x.dtype == np.int32
        return np.array([_encode_10plus6_scalar(int(y)) for y in x], dtype=np.uint16)
    return _encode_10plus6_scalar(int(x))


def decode_10plus6(x: Union[int, np.ndarray]) -> Union[int, np.ndarray]:
    if isinstance(x, np.ndarray):
        assert x.dtype == np.uint16
        return np.array([_decode_10plus6_scalar(int(y)) for y in x], dtype=np.int32)
    return _decode_10plus6_scalar(int(x))


def _encode_10plus6_scalar(val: int) -> int:
    if val == 0:
        return 0

    is_neg = 32 if val < 0 else 0
    abs_val = _safe_abs_int32(val)
    lz = _clz32(abs_val)

    lower_part = is_neg + lz
    lower_part_mask = ~63

    if lz > 16:
        upper_part = abs_val << (lz - 16)
    elif lz < 16:
        upper_part = abs_val >> (16 - lz)
    else:
        upper_part = abs_val

    return ((upper_part & lower_part_mask) + lower_part) & 0xFFFF


def _decode_10plus6_scalar(val: int) -> int:
    if val == 0:
        return 0
    is_neg = val & 32
    lz = val & 31
    out = val & ~63

    if lz > 16:
        out = out >> (lz - 16)
    elif lz < 16:
        out = out << (16 - lz)

    if is_neg:
        out = -out
    return int(out)


def encode_4_into_5(vals_in: np.ndarray) -> np.ndarray:
    assert vals_in.size == 4
    vals_in = np.ascontiguousarray(vals_in, dtype=np.int32)
    shifts = 0
    compressed = np.zeros(4, dtype=np.uint16)
    for i in range(4):
        val = int(vals_in[i])
        negative_bit = 1 << 15 if val < 0 else 0
        abs_value = _safe_abs_int32(val)
        lz = _clz32(abs_value)
        shift = 0 if lz >= 18 else 18 - lz
        in_place_shift_bit = 1 << 14 if shift >= 16 else 0
        stored_shift = shift - 16 if shift >= 16 else shift
        shifts |= (stored_shift << (4 * i))
        compressed_val = (abs_value >> shift) & 0x3FFF
        compressed[i] = compressed_val | negative_bit | in_place_shift_bit

    out = np.zeros(5, dtype=np.uint16)
    out[0] = shifts
    out[1:] = compressed
    return out


def decode_5_into_4(compressed_data: np.ndarray) -> np.ndarray:
    assert compressed_data.size % 5 == 0, "Input array length must be a multiple of 5"
    compressed_data = np.ascontiguousarray(compressed_data, dtype=np.uint16)
    num_chunks = compressed_data.size // 5
    decompressed_data = np.zeros(num_chunks * 4, dtype=np.int32)
    for i in range(num_chunks):
        chunk = compressed_data[i * 5:(i + 1) * 5]
        shifts = int(chunk[0])
        for j in range(4):
            comp = int(chunk[1 + j])
            is_neg = bool(comp & (1 << 15))
            shift_adjustment = 16 if (comp & (1 << 14)) else 0
            shift = ((shifts >> (4 * j)) & 0xF) + shift_adjustment
            abs_val = (comp & 0x3FFF) << shift
            decompressed_data[i * 4 + j] = -abs_val if is_neg else abs_val
    return decompressed_data


def encode_shared_lz_positive(spectra: np.ndarray) -> np.ndarray:
    spectra = np.ascontiguousarray(spectra, dtype=np.uint32)
    size = int(spectra.size)
    out = bytearray()
    i = 0
    while i < size:
        shift_by = _get_shift_by(int(spectra[i]))
        j = i + 1
        while j < size and (j - i) < 255:
            next_shift_by = _get_shift_by(int(spectra[j]))
            if abs(shift_by - next_shift_by) > 1:
                break
            j += 1
        if shift_by == 17:
            shift_by = 16
        n = j - i
        out.append(np.int8(shift_by).item() & 0xFF)
        out.append(n & 0xFF)
        for k in range(i, j):
            compressed_val = int(spectra[k]) >> shift_by
            out.extend(int(compressed_val).to_bytes(2, "little", signed=False))
        i = j
    return np.frombuffer(bytes(out), dtype=np.uint8)


def decode_shared_lz_positive(compressed_data: np.ndarray, array_size: int) -> np.ndarray:
    data = np.ascontiguousarray(compressed_data, dtype=np.uint8)
    x = np.zeros(array_size, dtype=np.uint32)
    idx = 0
    i = 0
    data_len = int(data.size)
    while i < data_len and idx < array_size:
        shift_by = np.int8(data[i]).item()
        i += 1
        n = int(data[i])
        i += 1
        for _ in range(n):
            compressed_val = int.from_bytes(bytes(data[i:i + 2]), "little", signed=False)
            i += 2
            x[idx] = (compressed_val << shift_by) & 0xFFFFFFFF
            idx += 1
    return x


def encode_shared_lz_signed(spectra: np.ndarray) -> np.ndarray:
    spectra = np.ascontiguousarray(spectra, dtype=np.int32)
    size = int(spectra.size)
    out = bytearray()
    i = 0
    while i < size:
        val = int(spectra[i])
        is_neg = 1 if val < 0 else 0
        shift_by = _get_shift_by(_safe_abs_int32(val))
        j = i + 1
        while j < size and (j - i) < 255:
            next_val = int(spectra[j])
            next_is_neg = 1 if next_val < 0 else 0
            if next_is_neg != is_neg:
                break
            next_shift_by = _get_shift_by(_safe_abs_int32(next_val))
            if abs(next_shift_by - shift_by) > 1:
                break
            j += 1

        if shift_by == 17:
            shift_by = 16

        segment_len = j - i
        sign_and_shift = (is_neg << 7) | (shift_by & 31)
        out.append(sign_and_shift & 0xFF)
        out.append(segment_len & 0xFF)
        for k in range(i, j):
            abs_val = _safe_abs_int32(int(spectra[k]))
            compressed_val = abs_val >> shift_by
            out.extend(int(compressed_val).to_bytes(2, "little", signed=False))
        i = j
    return np.frombuffer(bytes(out), dtype=np.uint8)


def decode_shared_lz_signed(compressed_data: np.ndarray, array_size: int) -> np.ndarray:
    data = np.ascontiguousarray(compressed_data, dtype=np.uint8)
    x = np.zeros(array_size, dtype=np.int32)
    idx = 0
    i = 0
    data_len = int(data.size)
    while i < data_len and idx < array_size:
        sign_and_shift = int(data[i])
        i += 1
        is_neg = (sign_and_shift >> 7) & 1
        shift_by = sign_and_shift & 31
        segment_len = int(data[i])
        i += 1
        for _ in range(segment_len):
            compressed_val = int.from_bytes(bytes(data[i:i + 2]), "little", signed=False)
            i += 2
            abs_val = compressed_val << shift_by
            x[idx] = -abs_val if is_neg else abs_val
            idx += 1
    return x
