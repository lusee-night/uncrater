import sys
sys.path.append('.')
sys.path.append('./scripter/')
sys.path.append('./commander/')
import matplotlib.pyplot as plt
import os


import argparse
import numpy as np
from test_base import Test
from test_base import pycoreloop as cl
from  lusee_script import Scripter, bl
import uncrater as uc
from collections import defaultdict


def hex_parse(str,bits):
    if str[:2]=='0x':
        val = int(str,16)
    else:
        val = int(str)
    if val<0 or (val>2**bits-1):
        raise ValueError(f"Value {val} is out of range for {bits} bits")
    return val

class Test_Bootload(Test):

    name = "bootload"
    version = 0.1
    description = """ Reboots spectrometer and interacts with bootloader."""
    instructions = """ No need to connect anything"""
    default_options = {
        "cmd": "reboot",
    } ## dictinary of options for the test
    options_help = {
        "cmd" : r""" Test command to execute. Can be 'reboot', 'reboot_only', 'check', 'command {val} {arg}', 
                    'register {addres} {arg}', 'wait {seconds}', 'launch {region}', 'delete {region}' or 'write {region} {hex file}'"""            
    } ## dictionary of help for the options



    def hex_line_error_checking(self, num, line):
        #Check basic conformance
        if (len(line) < 3):
            sys.exit(f"Line {num} has a length of {len(line)}, the full line is {line}")
        if (line[0:1] != bytes(":","utf-8")):
            sys.exit(f"Line {num} does not start with a ':', it starts with a {line[0:1]}")

        #Valid data starts after the initial colon and goes until before the last 2 nibbles, which are the line checksum
        #More details here: https://en.wikipedia.org/wiki/Intel_HEX#Checksum_calculation
        line_length = len(line[1:-2])
        #len() gives you length in nibbles, we want bytes
        bytes_length = int(line_length/2)

        #This starts after the colon and takes two consecutive nibbles at a time and converts them to their integer values, and stops before the line checksum
        val = [int(line[1+(j*2):1+(j*2)+2], 16) for j in range(bytes_length)]
        running_sum = sum(val)
        calculated_checksum = bl.convert_checksum(running_sum, 8)

        #Last 2 characters are the 8 bit checksum, interpreted as hex
        line_checksum = int(line[-2:], 16)

        if (calculated_checksum != line_checksum):
            sys.exit(f"Line {num} of file {self.file_path} has a calculated checksum of {hex(calculated_checksum)} and a checksum at the end of the line of {hex(line_checksum)}. The total line is {line}")


    def read_file_old(self, filename):        
        if (not os.path.isfile(filename)):
            sys.exit(f"The given path {filename} is not a valid file. Point to a microcontroller hex file")
        f = open(filename, mode="rb")
        lines = f.read().splitlines() #Because line usually ends with \r\n
        #We will end up with an array of 32 bit integers, because that's how all this data is written to the FPGA registers
        write_array = []
        last_hex_line = b':00000001FF'
        
        for num,i in enumerate(lines):

            self.hex_line_error_checking(num, i)
            #Part of Intel Hex Format
            line_type = int(i[1:3])
            if (line_type == 10):
                line_number = int(i[2:6], 16)
                #if (line_number != num):
                #    sys.exit(f"The binary file's line number was {line_number} but the program was at line {num}")
                #In a normal data line, there are 4 sets of 32 bit integers
                for j in range(4):
                    #First I grab them as 8 byte, two nibble values. The first 9 bits are the : character and the line number
                    four_bytes = [int(i[9+(j*8)+(k*2):9+(j*8)+(k*2)+2], 16) for k in range(4)]
                    #Then I rearrange them because that's what the SPI Flash calls for
                    rearranged_bytes = (four_bytes[3] << (8*3)) + (four_bytes[2] << (8*2)) + (four_bytes[1] << 8) + (four_bytes[0])
                    write_array.append(rearranged_bytes)
            #Jack includes this line that's written in the hex file, don't know if we need to. It doesn't have the line number

            
            elif (line_type == 4):
                four_bytes = [int(i[9+(k*2):9+(k*2)+2], 16) for k in range(4)]
                rearranged_bytes = (four_bytes[3] << (8*3)) + (four_bytes[2] << (8*2)) + (four_bytes[1] << 8) + (four_bytes[0])
                write_array.append(rearranged_bytes)
            elif (i != last_hex_line):
                sys.exit(f"Line {num} of file {filename} should be the final line. Instead of being {last_hex_line}, it's {i}")
        return write_array



    def read_file(self, filename):        
        if (not os.path.isfile(filename)):
            sys.exit(f"The given path {filename} is not a valid file. Point to a microcontroller hex file")
        f = open(filename, mode="rb")
        lines = f.read().splitlines() #Because line usually ends with \r\n
        #We will end up with an array of 32 bit integers, because that's how all this data is written to the FPGA registers
        write_array = []
        
        for num,i in enumerate(lines):
            self.hex_line_error_checking(num, i)
            assert(i[0]==58) ##58 == :
            ll = int(i[1:3],16)
            aa = int(i[3:7],16)            
            tt = int(i[7:9],16)
            
            dd = [int(i[9+j*2:9+j*2+2],16) for j in range(ll)]
            
            if tt==0x04 or tt==0x05:
                print (f'Ignoring address record at line {num}')
                continue # ignore extended address records
            if tt==0x01:
                break   # end of file
            if (tt!=0):
                raise ValueError(f"Unknown record type {tt} in line {num}, {i}")
            if len(write_array*4)<aa:
                print (f'Appending zeros at line {i}')
                write_array += [0]*(aa//4-len(write_array))


            ## now rearrange data:
            #print (i)
            print (f"{len(write_array)*4:x}")
            for j in range(0,ll,4):  
                try:
                    val = dd[j] + (dd[j+1]<<8) + (dd[j+2]<<16) + (dd[j+3]<<24)
                except:
                    # do just two
                    val = (dd[j] + (dd[j+1]<<8))
                write_array.append(val)
        return write_array




    def generate_script(self):

        S = Scripter()
        S.wait(1)
        cmds  = self.cmd.split(';')
        for cmd in cmds:
            cmd = [a.strip() for a in cmd.split()]
            
            command, args = cmd[0], cmd[1:]
            print (f'>>>>> {command}, {args}')

            if command == 'reboot':
                S.reboot()
                S.wait(1)
                S.bootloader_stay()

            elif command == 'reboot_only':
                S.reboot()
                S.wait(1)

            elif command == 'check':
                S.bootloader_check()
            
            elif command == 'cmd':
                val,arg  = hex_parse(args[0],8), hex_parse(args[1],16)
                S.command(val, arg)

            elif command == 'register':
                address, val = hex_parse(args[0],16), hex_parse(args[1],32)
                S.write_register(address, val)

            elif command == 'wait':
                try:
                    seconds = int(args[0])
                except:
                    raise ValueError("Please provide a number of seconds")
                S.wait(seconds)

            elif command == 'launch':
                try:
                    region = int(args[0])
                except:
                    raise ValueError("Please provide a region number")
                S.bootloader_load_region(region)
                S.bootloader_launch()
            
            elif command == 'delete':
                try:
                    region = int(args[0])
                except:
                    raise ValueError("Please provide a region number")
                S.bootloader_delete_region(region)
            
            elif command == 'write':
                try:
                    region = int(args[0])
                except:
                    raise ValueError("Please provide a region number")
                try:
                    self.filename = args[1]
                except:
                    raise ValueError("Please provide a filename")
                
                write_array = self.read_file(self.filename)
                #write_array2 = self.read_file_old(self.filename)                
                #print (len(write_array), len(write_array2))
                ##for i in range(20):
                #    print (f'{write_array[i]:08x} {write_array2[i]:08x}')                
                S.bootloader_write_region(region, write_array)
            else:
                raise ValueError(f"Command {command} not recognized")

        S.wait(5)
        return S

    def analyze(self, C: uc.Collection, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.results = {}
        passed = True
        for i, packet in enumerate(C.cont):
            if packet.appid == 0x208:
                packet._read()
                print (f"Packet {i}: bootloader")
                print(packet.info())
                
            elif packet.appid == 0x209:
                print (f"Packet {i}: SWS hello")
                print(packet.info())

            else:
                print (f"Packet {i}: AppID={packet.appid}")

        self.results['result'] = int(passed)
