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
                if ccsds_packet_type == 1:
                    # last packet
                    istart = 6
                    iend = 7+ccsds_packetlen
                    iallend = iend+6
                    self.full_packet = self.full_packet + order(data[istart:iend])
                    #if ccsds_appid <0x200:
                    #    ccsds_appid = ccsds_appid + 0x200
                    print (f"Storing appdid 0x{ccsds_appid:04x} ({len(self.full_packet)} bytes)")
                    self.save_data(ccsds_appid, self.full_packet)        
                    self.full_packet = bytearray(0)
                    ok = (data[iend+2]==0XFF and data[iend+3]==0XFF and data[iend+4]==0XFE and data[iend+5]==0X00)
                    if not ok:
                        print ("Bad end of packet!")
                    data = data[iallend+6:]
                    if len(data)<6:
                        break
                    else:
                        print ("More data in this stream (after end packet)....")
                else:
                    print (".",end="",flush=True)
                    iend = 7+ccsds_packetlen
                    
                    
                    self.full_packet = self.full_packet + order(data[6:iend])
                    data = data[iend:]
                    if len(data)<6:
                        break
                    else:
                        print ("More data in this stream (after TBC packet)....")



    def save_ccsds_legacy(self,data):
        while data is not None:
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
                    print (f"Lost CCSDS packet detected ({lost} packets)!!!!")
            self.last_cnt = ccsds_sequence_cnt

            hocus = len(data) - ccsds_packetlen
            print ('hocus',ccsds_packet_type, ccsds_secheaderflag, formatted_data[1]>>10)
            nextdata = None
            if  hocus<7 or hocus==8:
                print ("Weird hocus!!")
                tbc= True
            elif hocus == 7:
                tbc = True
            elif hocus == 9 or hocus == 13: # 9 was old, 13 is the new FW.
                tbc = False
            else:
                #ndx = ccsds_packetlen+9+6 ## testing 
                ##nextdata = data[ndx:]
                ##
                #tbc = False                
                print ("Merged packets detected, extra size", hocus-9, 'dropping')
                data = data[:ccsds_packetlen+9]
                tbc = False


            if (hocus == 13):
                print (f"EXTRA: {data[-6]:x} {data[-5]:x} {data[-4]:x} {data[-3]:x} {data[-2]:x} {data[-1]:x}")
                data = data[:-4]
            data = data[6:]                        
            cdata = bytearray(len(data))
            cdata[::2]= data[1::2]
            cdata[1::2] = data[::2]
            self.full_packet = self.full_packet + cdata
            if not tbc:
                if ccsds_appid <0x200:
                    ccsds_appid = ccsds_appid + 0x200
                print ("Storing appdid ",hex(ccsds_appid))
                towrite = self.full_packet[:-2] ## now chop last two bytes        
                self.save_data(ccsds_appid, towrite)        
                self.full_packet = bytearray(0)
            else:
                print (".",end="",flush=True)
            data = nextdata



    def save_data(self, appid, data):
        fname = os.path.join(self.out_dir,f"{self.packet_count:05d}_{appid:04x}.bin")        
        f=open(fname,'wb')
        f.write(data) 
        f.close()
        self.clog.logt(f"Stored AppID {hex(appid)} len={len(data)}\n")    
        self.packet_count += 1
        
    