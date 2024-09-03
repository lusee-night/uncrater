import os
import struct

class BackendBase:

    def __init__(self, clog, uart_log, session):
        self.clog = clog
        self.uart_log = uart_log
        self.session = session
        self.out_dir = os.path.join(session,'cdi_output')
        self.packet_count = 0
        self.full_packet = bytearray(0)
        self.last_cnt = None

    def save_ccsds(self,data):
        formatted_data = struct.unpack_from(f">3H",data[:6])
        ccsds_version= (formatted_data[0] >> 13)
        ccsds_packet_type= ((formatted_data[0] >> 12) & 0x1)
        ccsds_secheaderflag = ((formatted_data[0] >> 11) & 0x1)
        ccsds_appid= (formatted_data[0] & 0x7FF)
        ccsds_groupflags = (formatted_data[1] >> 14)
        ccsds_sequence_cnt = (formatted_data[1] & 0x3FFF)
        ccsds_packetlen  = (formatted_data[2])
        if self.last_cnt is not None:
            lost = ccsds_sequence_cnt - (self.last_cnt + 1)
            if lost>0:
                print ("Lost CCSDS packet detected ({lost} packets)!!!!")
        self.last_cnt = ccsds_sequence_cnt

        hocus = len(data) - ccsds_packetlen
        if hocus == 7:
            tbc = True
        elif hocus == 9:
            tbc = False
        else:
            print ("Merged packets detected!!!!")
        data = data[6:]                        
        cdata = bytearray(len(data))
        cdata[::2]= data[1::2]
        cdata[1::2] = data[::2]
        self.full_packet = self.full_packet + cdata
        if not tbc:
            print ("Storing appdid ",hex(ccsds_appid))
            towrite = self.full_packet[:-2] ## now chop last two bytes        
            self.save_data(ccsds_appid, towrite)        
            self.full_packet = bytearray(0)
        else:
            print (".",end="",flush=True)
            



    def save_data(self, appid, data):
        fname = os.path.join(self.out_dir,f"{self.packet_count:05d}_{appid:04x}.bin")        
        f=open(fname,'wb')
        f.write(data) 
        f.close()
        self.clog.logt(f"Stored AppID {hex(appid)} len={len(data)}\n")    
        self.packet_count += 1
        
    