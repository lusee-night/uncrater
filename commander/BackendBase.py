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
        self.eos_flag = False

    def drop_eos_flag(self):
        self.eos_flag = False

    def inspect_packet(self,appid, blob):
        if appid in [
            uc.id.AppID_uC_Start,
            uc.id.AppID_uC_Heartbeat,
            uc.id.AppID_uC_Bootloader,
            uc.id.AppID_End_Of_Sequence,
            uc.id.AppID_Watchdog,
        ]:    
            P = uc.Packet(appid, blob = blob)
            print (P.info())
            if P.appid == uc.id.AppID_End_Of_Sequence:
                self.eos_flag = True;

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
                if ccsds_groupflags or (ccsds_appid==0x300):
                    # last packet
                    istart = 6
                    iend = 7+ccsds_packetlen
                    self.full_packet = self.full_packet + order(data[istart:iend])
                    print (f"Storing appdid 0x{ccsds_appid:04x} ({len(self.full_packet)} bytes)")
                    ## now if the packet is housekeeping, show temperatures
                    self.inspect_packet(ccsds_appid, self.full_packet)
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
                    print (".", end="",flush=True)
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
        
    
