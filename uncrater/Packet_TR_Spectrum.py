from .PacketBase import PacketBase, pystruct
from .utils import Time2Time
import os, sys
import struct
import numpy as np
import binascii

if os.environ.get("CORELOOP_DIR") is not None:
    sys.path.append(os.environ.get("CORELOOP_DIR"))

# now try to import pycoreloop
try:
    from pycoreloop import appId as id
except ImportError:
    print("Can't import pycoreloop\n")
    print("Please install the package or setup CORELOOP_DIR to point at CORELOOP repo.")
    sys.exit(1)


class Packet_Metadata(PacketBase):
    @property
    def desc(self):
        return "Data Product Metadata"

    def _read(self):
        if self._is_read:
            return
        super()._read()
        # TODO: check if this actually works
        self.copy_attrs(pystruct.meta_data.from_buffer_copy(self._blob))
        self.format = self.seq.format
        self.time = Time2Time(self.base.time_32, self.base.time_16)
        self.errormask = self.base.errors
        self._is_read = True

    def info(self):
        self._read()
        desc = ""
        desc += f"Version : {self.version}\n"
        desc += f"packet_id : {self.unique_packet_id}\n"
        desc += f"Errormask: {self.errormask}\n"
        desc += f"Time: {self.time}\n"
        desc += f"Current weight: {self.base.weight_current}\n"
        desc += f"Previous weight: {self.base.weight_previous}\n"
        return desc

    @property
    def frequency(self):
        Navgf = self.seq.Navgf
        if Navgf == 1:
            return np.arange(2048) * 0.025
        elif Navgf == 2:
            return np.arange(1024) * 0.05
        else:
            return np.arange(512) * 0.1
