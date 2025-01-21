from .PacketBase import PacketBase, pystruct
from .PacketBase import PacketBase
from .utils import Time2Time, process_telemetry

import struct
class Packet_Heartbeat(PacketBase):
    @property
    def desc(self):
        return  "Heartbeat"

    def _read(self):
        if self._is_read:
            return
        super()._read()
        temp = pystruct.heartbeat.from_buffer_copy(self._blob)       
        
        self.copy_attrs(temp)
        self.ok = (self.magic == b'BRNMRL')
        self.time = Time2Time(self.time_32, self.time_16)
        self.telemetry = process_telemetry(self.TVS_sensors)
        self._is_read = True

    def info (self):
        self._read()
        ok = "OK" if self.ok else "BAD"
        desc = "Heartbeat Packet\n"
        desc += f"Magic             : {ok}\n"
        desc += f"Count             : {self.packet_count}\n"
        desc += f"CDI command count : {self.cdi_total_command_count}\n"
        desc += f"Error bitmask     : {self.errors:b}\n"
        for k,u in zip(self.telemetry.keys(),['V','V','V','C']):
            desc += f"{k} : {self.telemetry[k]:6.4} {u}\n"
        if self.telemetry['T_FPGA']>90:
            desc += "******************************************\n" 
            desc += "*   FPGA temperature too high !!!!       * \n"
            desc += "******************************************\n" 
        
        return desc
