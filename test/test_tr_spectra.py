import os
import sys
import matplotlib.pyplot as plt
import numpy as np
import scipy as sp
import typing

from icecream import ic

sys.path.append('.')
sys.path.append('./scripter/')
sys.path.append('./commander/')

if os.environ.get('CORELOOP_DIR') is not None:
    sys.path.append(os.environ.get('CORELOOP_DIR'))

from test_base import Test
from lusee_script import Scripter
from collections import defaultdict

from pycoreloop import appId

import uncrater as uc


class Test_TRSpectra(Test):
    name = "time_resolved"
    version = 0.1
    description = """ Check that time resolved spectra are received."""
    instructions = """ Do not need to connect anything."""
    default_options = {
        "time": 10,
        "tr_start": 0,
        "tr_stop": 8,
        "tr_avg_shift": 1
    }  ## dictinary of options for the test
    options_help = {
        "time": "Total time to run the test.",
        "tr_start": "Start of time-resolved window.",
        "tr_stop": "End of time-resolved window.",
        "tr_avg_shift": "Average over every 2^tr_avg_shift values.",
    }  ## dictionary of help for the options

    def generate_script(self):
        """ Generates a script for the test """
        if self.time < 20:
            print("Time raised to 20 seconds.")
            self.time = 20

        scripter = Scripter()
        scripter.reset()
        scripter.wait(5)

        scripter.set_Navg(Navg1=14, Navg2=3)
        scripter.set_tr_start_lsb(self.tr_start)
        scripter.set_tr_stop_lsb(self.tr_stop)
        scripter.set_tr_avg_shift(self.tr_avg_shift)

        scripter.start()
        scripter.wait(self.time)
        scripter.stop()

        return scripter

    def analyze(self, C, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.results = {}
        passed = True

        self.results['packets_received'] = len(C.cont)

        C.cut_to_hello()

        self.get_versions(C)

        hb_num, sp_num = 0, 0
        hb_tmin, hb_tmax, last_hb, last_hbtime = 0, 0, None, None
        heartbeat_counter_ok = True

        sp_crc_ok = True

        for packet in C.cont:
            if type(packet) == uc.Packet_Heartbeat:
                hb_num += 1
            elif type(packet) == uc.Packet_Spectrum:
                sp_num += 1
                packet._read()
                sp_crc_ok = (sp_crc_ok & (not packet.error_crc_mismatch))
            elif type(packet) == uc.Packet_TR_Spectrum:
                packet._read()

        self.results['sp_num'] = len(C.spectra)
        self.results['heartbeat_received'] = hb_num
        self.results['hearbeat_count'] = int(hb_num)
        self.results['heartbeat_not_missing'] = int(heartbeat_counter_ok & (hb_tmax < 11))
        self.results['sp_packets_received'] = sp_num
        self.results['result'] = int(passed)
