import ctypes
import os
import numpy as np
from typing import Union

lib_path = os.path.join(os.environ['CORELOOP_DIR'],'build','libcl_utils.so')
lib = ctypes.CDLL(lib_path)

lib.encode_10plus6.argtypes = [ctypes.c_int32]
lib.encode_10plus6.restype = ctypes.c_uint16

lib.decode_10plus6.argtypes = [ctypes.c_uint16]
lib.decode_10plus6.restype = ctypes.c_int32


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
