import os
import struct
import uncrater as uc

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
            def order (data):
                cdata = bytearray(len(data))
                cdata[::2]= data[1::2]
                cdata[1::2] = data[::2]
                return cdata

            while data is not None:
                formatted_data = struct.unpack_from(f">3H",data[:6])
                ccsds_version= (formatted_data[0] >> 13)
                ccsds_packet_type= ((formatted_data[0] >> 12) & 0x1)
                ccsds_secheaderflag = ((formatted_data[0] >> 11) & 0x1)
                ccsds_appid= (formatted_data[0] & 0x7FF)
                ccsds_groupflags = (formatted_data[1] >> 14)        
                ccsds_sequence_cnt = (formatted_data[1] & 0x3FFF)
                ccsds_packetlen  = (formatted_data[2])
                if ccsds_groupflags:
                    # last packet
                    istart = 6
                    iend = 7+ccsds_packetlen
                    self.full_packet = self.full_packet + order(data[istart:iend])
                    print (f"Storing appdid 0x{ccsds_appid:04x} ({len(self.full_packet)} bytes)")
                    ## now if the packet is housekeeping, show temperatures
                    if ccsds_appid==0x20a:
                        P = uc.Packet_Heartbeat(ccsds_appid, blob = self.full_packet)
                        print (P.info())

                    self.save_data(ccsds_appid, self.full_packet)        
                    self.full_packet = bytearray(0)
                    data = data[iend:]
                    if len(data)<6:
                        if len(data)>0:
                            print (f"Some garbage in this stream (after end packet).... {len(data)} bytes")
                        break
                    else:
                        print (f"More data in this stream (after end packet).... {len(data)} bytes")
                        #open('debug.bin','wb').write(data)
                        #stop()
                else:
                    print (".",end="",flush=True)
                    iend = 7+ccsds_packetlen
                    
                    
                    self.full_packet = self.full_packet + order(data[6:iend])
                    data = data[iend:]
                    if len(data)<6:
                        break
                    else:
                        print ("More data in this stream (after TBC packet)....")


    def save_data(self, appid, data):
        fname = os.path.join(self.out_dir,f"{self.packet_count:05d}_{appid:04x}.bin")        
        f=open(fname,'wb')
        f.write(data) 
        f.close()
        self.clog.logt(f"Stored AppID {hex(appid)} len={len(data)}\n")    
        self.packet_count += 1
        
    