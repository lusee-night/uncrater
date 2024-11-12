import os, sys
from typing import List

if os.environ.get("CORELOOP_DIR") is not None:
    sys.path.append(os.environ.get("CORELOOP_DIR"))

try:
    from pycoreloop import core_loop_errors as errs
except ImportError:
    print("Can't import pycoreloop\n")
    print( "Install the package or setup CORELOOP_DIR to point at CORELOOP repo." )
    sys.exit(1)

error_prefixes = ("ANALOG_", "CDI_", "DF_SPECTRA_DROPPED", "FLASH_CRC_FAIL")

# dict that maps error name (str) to code (int)
error_code_to_value = {
    name: getattr(errs, name)
    for name in dir(errs)
    if name.startswith(error_prefixes)
}

# dict that maps string to error code
error_value_to_code = {
    getattr(errs, name) : name
    for name in dir(errs)
    if name.startswith(error_prefixes)
}


def extract_error_values(mask: int) -> List[int]:
    return [err for err in error_value_to_code if mask & err]

def extract_error_codes(mask: int) -> List[str]:
    return [error_value_to_code[err] for err in error_value_to_code if mask & err]

def error_mask_pretty_print(mask: int) -> str:
    if mask == 0:
        return ""
    else:
        return ",".join(extract_error_codes(mask))
