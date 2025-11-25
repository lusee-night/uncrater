import sys
sys.path.append('.')
sys.path.append('./scripter/')
sys.path.append('./commander/')
import matplotlib.pyplot as plt
import os


import argparse
import numpy as np
from test_base import Test
from  lusee_script import Scripter
from test_base import pycoreloop as cl
from pycoreloop import pystruct as ps
import uncrater as uc
from collections import defaultdict


class Test_Production(Test):

    name = "production"
    version = 0.2
    description = """ Script to be run during production science mode"""
    instructions = """ """
    default_options = {
        'mode' : 'normal',
        'alarm': 90,
        'store_flash': False,
        'calweight_slot': 0,
        'Nnotch': 4,
        'fullzoom': False,
    } ## dictinary of options for the test
    options_help = {
        'mode' : "Operating mode: normal, calibrator, grimm",
        'alarm': "Alarm setpoint for temperature watchdog",
        "store_flash": "Whether to store the script in flash for automatic recovery",
        "calweight_slot": "Calibrator weight slot to use in calibrator mode",
        "Nnotch": "Notch filter setting",
        "fullzoom": "Whether to run zoom over full spectral range"
    } ## dictionary of help for the options


    def generate_script(self):

        assert self.mode in ['normal','calibrator','grimm'], "Invalid mode"
        
        S = Scripter()
        S.reset()
        S.wait(0.5)
        S.seq_begin()        

        S.set_cdi_delay(1)
        S.set_dispatch_delay(100)
        S.set_alarm_setpoint(self.alarm)     
        S.enable_watchdogs(0b01111111)   # cdi alarm not there        
        S.set_notch(self.Nnotch)        
        S.set_Navg(14,6)
        #S.reject_enable(reject_frac=10, max_bad = 100)          
        
        S.set_avg_set_hi(75)
        S.set_avg_set_mid(150)
        
        if self.mode == 'grimm':
            S.enable_grimm_tales()
        elif self.mode == 'normal':
            S.set_tr_start_stop(0,2048)
            S.set_tr_avg_shift(6)


        S.set_avg_mode('40bit')        
        S.set_spectra_format(ps.OUTPUT_16BIT_4_TO_5)                        
        S.set_bitslice_auto(12)
        S.set_ana_gain('AAAA')
        
        # zoom

        if self.mode == 'calibrator':
            slicer = [24, 24, 27, 15, 18, 1, 12, 0]
            S.cal_set_slicer(auto=True,powertop=slicer[0], sum1=slicer[1], sum2=slicer[2], prod1=slicer[3], prod2=slicer[4], delta_powerbot=slicer[5], fd_slice=slicer[6], sd2_slice=slicer[7])
            S.cal_set_avg(7, 7)
            S.cal_set_drift_step(10)
            S.cal_antenna_enable(0b1111)
            S.cal_weights_load(self.calweight_slot)
            S.house_keeping(3)
            S.cal_set_corrAB(0.0,0.0)
            S.cal_raw11_every(10)
            S.notch_detector(True)
            S.cal_set_drift_guard(120*2**(self.Nnotch-4)) # (120 at 4, 240, at 5,etc)
            S.cal_set_ddrift_guard(1500)
            S.cal_set_gphase_guard(250000)
            S.cal_SNRonff(5,1)
            
            S.loop_start(0)
            # let's rest on bit slicer settle mode
            S.cal_enable(enable=True, mode=cl.pystruct.CAL_MODE_BIT_SLICER_SETTLE) 
            S.start()
            S.cdi_wait_minutes(60)
            S.stop()
            S.loop_next()

        else:
            S.cal_set_zoom_ch(chA=0, chB=1, chA_minus=2, chB_minus=3)
            S.cal_set_zoom_diff(diff_A=True, diff_B=True)
            
            S.cal_set_zoom_navg(6 if self.fullzoom else 8)
            S.cal_enable(enable=True, mode=cl.pystruct.CAL_MODE_ZOOM)
        

            S.loop_start(0)

            S.waveform(4)
            S.cdi_wait_seconds(1)
            
            if self.fullzoom:
                S.cal_set_pfb_bin(0)
                S.cal_set_zoom_range(2047)
                S.start()
                S.cdi_wait_spectra(180)
                S.cdi_wait_spectra(90)
                S.stop()
            else:
                S.cal_set_pfb_bin(0)
                S.cal_set_zoom_range(20)
                S.start()
                S.cdi_wait_spectra(90)
                S.stop()
                
                S.cal_set_pfb_bin(1000)
                S.cal_set_zoom_range(40)
                S.start()
                S.cdi_wait_spectra(90)
                S.stop()

                S.cal_set_pfb_bin(2000)
                S.cal_set_zoom_range(40)
                S.start()
                S.cdi_wait_spectra(90)
                S.stop()

            S.loop_next()

        S.request_eos()
        S.seq_end(store_flash=self.store_flash)
        S.wait_eos()
        return S
        
        

    def analyze(self, C, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.results = {}
        passed = True

        self.results['packets_received'] = len(C.cont)

        if len(C.cont) == 0:
            print ("No packets received, aborting")
            self.results['result'] = 0
            return 

        self.get_versions(C)

        self.results['result'] = int(passed)
        