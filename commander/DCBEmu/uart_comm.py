import serial
from serial.tools import list_ports
import time
import os,sys
import struct
import csv

class LuSEE_UART:
    def __init__(self, clog):
        #If you're not receiving the large packets, run:
        #sudo ifconfig <device name> mtu 9000
        self.port = None #None will automatically scan for Flashpro
        self.baud = 115200
        self.timeout_reg = 0.01 #In seconds
        self.timeout_data = 2 #In seconds
        self.parity = serial.PARITY_NONE
        self.clog = clog

        
            
        

    def get_connections(self):
        ports = list_ports.comports()
        flashpro = None
        if (len(ports) == 0):
            self.clog.log ("No USB connection found: Make sure FPGA is plugged into the computer!\n")
            return False
        else:
            for i in ports:
                
                self.clog.log("Found: "+str(i.description)+"\n")
            for i in ports:
                #if (i.manufacturer == "Microsemi"):
                if (("Silicon Labs" in i.manufacturer and "Standard COM" in i.description) or  ## for windows 
                    ("UART" in i.description and "Standard" in i.description)):  #for linux
                    flashpro = i
                    break
        if (flashpro == None):
            self.clog.log("No Microsemi Flashpro found: Make sure FPGA is plugged into the computer!\n")
            return False

        self.port = flashpro.device
        self.clog.log (f"Using {flashpro.description} at port {self.port}.\n")
        return True

    def read(self):
        return self.connection.read()
    
    def connect_usb(self, timeout=1):
        self.clog.log("Connecting to USB...\n")
        try:
            self.connection = serial.Serial(port=self.port, baudrate=self.baud, parity=self.parity, timeout=timeout)
            self.connection.flush()
        except:
            return False
        self.clog.log("Connection Opened.\n")
        return True


    def close(self):
        self.connection.flush()
        self.connection.close()
        self.clog.log("Connection Closed\n")


