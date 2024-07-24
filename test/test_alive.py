
import sys
sys.path.append('.')
sys.path.append('./scripter/')
sys.path.append('./commander/')

from test_base import Test
from  lusee_script import Scripter
from commander import Commander
import argparse
import numpy as np


class Test_Alive(Test):
    
    name = "alive"
    version = 0.1
    description = """ Basic aliveness test of communication and spectral engine."""
    instructions = """ Do not need to connect anything."""
    default_options = {
        "time" : 60
    } ## dictinary of options for the test
    options_help = {
        "time" : "Total time to run the test. 1/3 will be spent taking spectra. Need to be larger than 15s."
    } ## dictionary of help for the options


    def generate_script(self):
        """ Generates a script for the test """
        if self.time<15:
            print ("Time raised to 15 seconds.")
            self.time = 15
            
        S = Scripter()
        S.reset()
        S.wait(1)
        S.ADC_ramp(True)
        S.house_keeping(0)
        S.wait(1)
        for i in range(4):
            S.waveform(i)
            S.wait(1)
        S.set_Navg(14,3)
        #S.start()
        S.wait(self.time-S.total_time-1)
        #S.stop()
        S.house_keeping(0)
        S.wait(1)
        return S
    
    def analyze(self, C, uart, commander):
        """ Analyzes the results of the test. 
            Returns true if test has passed.
        """
        C.cut_to_hello()
        print(C.list())
        for P in C.cont:
            print (P.info())    

