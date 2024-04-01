import binascii
import struct
import numpy as np

def parse_spectrum(binary_blob, format, expected_packed_id):
    """Parse the spectrum from the binary blob.

    Args:
        binary_blob (bytes): The binary blob containing the spectrum.

    Returns:
        dict: The spectrum.
    """
    packet_id, crc = struct.unpack('<II', binary_blob[:8])
    if expected_packed_id != packet_id:
        raise ValueError("Packet ID mismatch")
    calculated_crc = binascii.crc32(binary_blob[8:]) & 0xffffffff
    if crc != calculated_crc:
        raise ValueError("CRC mismatch")
    if format==0:
        Ndata= len(binary_blob[8:])//4
        data = struct.unpack(f'<{Ndata}i', binary_blob[8:])
    else:
        raise NotImplementedError("Only format 0 is supported")
    return np.array(data, dtype=np.int32).astype(np.float32)
