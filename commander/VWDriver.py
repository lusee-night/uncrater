import socket
import sys



def crc16(data : bytearray):
    length = len(data)
    offset = 0
    crc = 0xFFFF
    for i in range(0, length):
        crc ^= data[offset + i] << 8
        for j in range(0,8):
            if (crc & 0x8000) > 0:
                crc =(crc << 1) ^ 0x1021
            else:
                crc = crc << 1
    return crc & 0xFFFF


class VWDriver:

    def __init__ (self):
        self.server_address = ('192.168.7.2', 25000)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(self.server_address)
        self.seq = 0
        

    def send_cmd(self, cmd, payload):
        crc = crc16(payload)
        byte1 = (crc&0xff00) >>8
        byte2 = (crc&0x00ff)
        packet = bytes([0x4e,0x53,0x52,0x02]+[cmd]+[0]+[len(payload)]+[self.seq])+payload+bytes([byte1,byte2])
        self.sock.sendall(packet)
        self.seq = (self.seq+1)%256
        

        

    def disable_PA (self):
        self.send_cmd(0x20, bytes([ord('D'),0x0]+[0x0]*8))
        
    def enable_PA (self, range_correction):
        range_correction_bytes = range_correction.to_bytes(4, byteorder='big', signed=True)
        self.send_cmd(0x20, bytes([ord('D'),0x1])+range_correction_bytes+bytes([0x0]*4))

#v= VWDriver()
#v.enable_PA(int(sys.argv[1]))
#v.disable_PA()
