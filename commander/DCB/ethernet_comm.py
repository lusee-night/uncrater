import time
import os,sys
import struct
import csv
import socket
import select
import binascii

class LuSEE_ETHERNET:
    def __init__(self, clog, save_data, tm_file):
        self.version = 1.12
        self.clog = clog
        self.save_data = save_data

        self.TCP_IP = 'localhost'
        self.PORT_TCP = 5004
        self.PORT_TCP_TM = 5005
        self.ssl_delimiter = 0xEB90

        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (self.TCP_IP, self.PORT_TCP)
        self.tcp_socket.connect(server_address)


        self.tcp_socket_TM = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address_TM = (self.TCP_IP, self.PORT_TCP_TM)
        self.tcp_socket_TM.connect(server_address_TM)

        self.clog.log(f"Initialized LuSEE_ETHERNET with version {self.version}.\n")
        self.clog.log(f"TCP IP is {self.TCP_IP} and TCP port is {self.PORT_TCP}.\n")
        self.etherStop = False
        self.tm_file = tm_file
        self.BUFFER_SIZE = 9014
                


    def write_cdi_reg(self, data):
        dataVal = int(data)
        dataValMSB = ((dataVal >> 16) & 0xFF)
        dataValLSB = dataVal & 0xFFFF
        WRITE_MESSAGE = struct.pack('>BH', dataValMSB, dataValLSB)

        try:
            self.tcp_socket.sendall(WRITE_MESSAGE)
        except:
            print(f"Python Ethernet --> Couldn't write {hex(data)}")

    def cdi_command(self,cmd,arg):
        self.write_cdi_reg((cmd<<16)+arg)


    def organize_header(self, formatted_data):
        header_dict = {}
        header_dict["message_id"] = hex(formatted_data[0] >> 10)
        header_dict["message_length"] = hex(formatted_data[0] & 0x3FF)
        header_dict["message_spare"] = hex(formatted_data[1])
        header_dict["ccsds_version"] = hex(formatted_data[2] >> 13)
        header_dict["ccsds_packet_type"] = hex((formatted_data[2] >> 12) & 0x1)
        header_dict["ccsds_secheaderflag"] = hex((formatted_data[2] >> 11) & 0x1)
        header_dict["ccsds_appid"] = hex(formatted_data[2] & 0x7FF)
        header_dict["ccsds_groupflags"] = hex(formatted_data[3] >> 14)
        header_dict["ccsds_sequence_cnt"] = hex(formatted_data[3] & 0x3FFF)
        header_dict["ccsds_packetlen"] = hex(formatted_data[4])
        return header_dict


    def ListenForData(self):
        data = bytearray(0)
        while not self.etherStop:
            cdata = self.tcp_socket.recv(self.BUFFER_SIZE)
            data = data+cdata
            print(f".",end="")
            if not ((data[0] == 0xEB) and (data[1] == 0x90)):
                print(f"First 2 bytes of the packet were {hex(data[0])} and {hex(data[1])}, not {hex(self.ssl_delimiter)}!")
                found = False
                for i in range(len(data)):
                    if (data[i] == 0xEB):
                        if (data[i+1] == 0x90):
                            print(f"Found sync at index {i}")
                            data = data[i:]
                            found = True
                            break
                if not found:
                    print(f"Couldn't find sync in the packet")
                    data = bytearray(0)
                    continue

            unpack_buffer = int((len(data))/2)
            formatted_data = struct.unpack_from(f">{unpack_buffer}H",data)
            # This is now a sanity check
            if (formatted_data[0] != self.ssl_delimiter):
                print(f"The first 2 bytes of the packet were {hex(formatted_data[0])}, not {hex(self.ssl_delimiter)}, internal error!")
                sys.exit(1)
                
            header_dict = self.organize_header(formatted_data[1:])
            cdi_packet_size = int(header_dict['ccsds_packetlen'], 16)
            if (int(header_dict["ccsds_appid"], 16) == 0x200):
                extra_packets = 12
            else:
                extra_packets = 13
            tsize = cdi_packet_size + extra_packets
            if (len(data) < tsize): #Account for the delimiter 0xEB90
                #print(f"CDI packet is supposed to have a size of {cdi_packet_size}, however, we only received {len(data)} waiting for more")
                pass
            else:
                self.save_data(data[6:tsize])
                data = data[tsize:]    
                #print(f"Incoming APID is {header_dict['ccsds_appid']}")
                


    def ListenForData_TM(self):
        while not self.etherStop:
            cdata = self.tcp_socket_TM.recv(self.BUFFER_SIZE)
            self.tm_file.write(cdata)
            self.tm_file.flush()


if __name__ == "__main__":
    #arg = sys.argv[1]
    luseeEthernet = LuSEE_ETHERNET()

    print(luseeEthernet.read_cdi_reg(0x120))


