# Based on driver by Emi Taumuar
# E. Tamura 2024.09.27-
# 
# ver0.0 initial release
# ver0.1 Emi Tamura (2024.10.02) modified to be simple
#        one frequency and one amplitude can be set
# ver0.2 Emi Tamura (2024.10.07) debug
# 



try:
    import pyvisa
except:
    pyvisa = None
    
import numpy as np
import time

class KS33500:
    def __init__(self,ip_address):
        self.debug=False
        self.pro='cnt_33500.py'
        self.version='v0.1'
        self.address=ip_address
        self.freq=[]
        self.chs=[]
        self.amplitude=0.01
        self.offset=0.0
        self.offset_f=False
        self.ks=None
        self.inst=None
        self.functions=[]

  
    #########################################################################
    # initialize 33500
    #########################################################################
    def init_33500 (self):
        # initialize
        self.ks = pyvisa.ResourceManager()
        # Connect to the Keysight 33500B over Ethernet
        #self.inst = self.ks.open_resource(f"TCPIP0::{self.address}::inst0::INSTR")
        self.inst = self.ks.open_resource(f"TCPIP::{self.address}::INSTR")
        if self.debug:
            print (f"connecting to {self.address}::inst0")

    #########################################################################
    # output off
    #########################################################################
    def output_off (self, ch):
        self.write_33500(f"OUTP{ch} OFF")

    #########################################################################
    # output on
    #########################################################################
    def output_on (self, ch):
        self.write_33500(f"OUTP{ch} ON")

    #########################################################################
    # function
    #########################################################################
    def set_function (self, ch, func):
        self.write_33500(f"SOUR{ch}:FUNC {func}")

    #########################################################################
    # frequency
    #########################################################################
    def set_frequency (self, ch, frequency):
        self.write_33500(f"SOUR{ch}:FREQ {frequency}")

    #########################################################################
    # amplitude
    #########################################################################
    def set_amplitude (self, ch, amplitude):
        self.write_33500(f"SOUR{ch}:VOLT {amplitude}")

    #########################################################################
    # offset
    #########################################################################
    def set_offset (self, ch, offset):
        self.write_33500(f"SOUR{ch}:VOLT:OFFS {offset}")

    #########################################################################
    # close 33500
    #########################################################################
    def close_33500 (self):
        self.inst.close()

    #########################################################################
    # write command to 33500
    #########################################################################
    def write_33500 (self, com):
        com += '\n'
        if self.debug:
            print ('writing', com)
        ## let's try to write in a fail-safe mode
        for i in range(3):
            try:
                self.inst.write(com)
                return
            except Exception as e:
                print(f"Error writing to 33500: {e}")
                if i < 2:
                    print("Retrying...")
                    time.sleep(0.05) ## can't afford to wait too long, spectrometer is running
                else:
                    print("Failed to write after 3 attempts.")
                    raise e
        self.inst.write(com)

