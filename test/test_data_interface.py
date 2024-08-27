import os
import sys
import matplotlib.pyplot as plt
import numpy as np
import scipy as sp
import typing

sys.path.append('.')
sys.path.append('./scripter/')
sys.path.append('./commander/')

if os.environ.get('CORELOOP_DIR') is not None:
    sys.path.append(os.environ.get('CORELOOP_DIR'))

from test_base import Test
from lusee_script import Scripter
import uncrater as uc
from collections import defaultdict

from pycoreloop import appId


def spectrum_category(p: uc.Packet_Spectrum) -> str:
    """return high, med, low depending on the category of packet"""
    if p.appid >= appId.AppID_SpectraHigh and p.appid < appId.AppID_SpectraHigh + 16:
        return "high"
    elif p.appid >= appId.AppID_SpectraMed and p.appid < appId.AppID_SpectraMed + 16:
        return "med"
    else:
        assert (p.appid >= appId.AppID_SpectraLow and p.appid < appId.AppID_SpectraLow + 16)
        return "low"


def fits(occurences: typing.List[int], probs: typing.List[float], p_value: float)->bool:
    """perform binomial test on 1-vs-all (high vs med+low, etc),
       return True if the p_value from every test is greater than p_value parameter"""
    n = sum(occurences)
    for k, p in zip(occurences, probs):
        res = sp.stats.binomtest(k, n, p)
        if res.pvalue < p_value:
            return False
    return True


class Test_DataInterface(Test):
    name = "data_interface"
    version = 0.1
    description = """ Check that RFS_SET_AVG_SET_HI and RFS_SET_AVG_SET_MID commands work."""
    instructions = """ Do not need to connect anything."""
    default_options = {
        "time": 60,
        "frac_high": 0.3,
        "frac_med": 0.4,
    }  ## dictinary of options for the test
    options_help = {
        "time": "Total time to run the test.",
        "frac_high": "Fraction of packets with AppId_SpectraHigh. Should be between 0.0 and 1.0, will be multiplied by 255 in the test.",
        "frac_med": "Fraction of packets with AppId_SpectraMed. Should be between 0.0 and 1.0, will be multiplied by 255 in the test."
    }  ## dictionary of help for the options

    def generate_script(self):
        """ Generates a script for the test """
        if self.time < 30:
            print("Time raised to 30 seconds.")
            self.time = 30

        if self.frac_high + self.frac_med > 1.0:
            print("frac_high and frac_med combined must be less than 1.0.")
            sys.exit(1)

        frac_high = int(255 * self.frac_high)
        frac_mid = int(255 * self.frac_med)

        scripter = Scripter()
        scripter.start()
        # set Navg_1 and Navg_2 to 4 (2^2 -- we send shifts)
        # to produces lots of spectra
        scripter.set_Navg(2, 2)
        scripter.set_avg_set_hi(frac_high)
        scripter.set_avg_set_mid(frac_mid)
        scripter.wait(self.time)
        scripter.stop()
        scripter.time_to_die()
        return scripter

    def analyze(self, C, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.results = {}
        passed = True

        self.results['packets_received'] = len(C.cont)

        C.cut_to_hello()

        if len(C) > 0 and type(C.cont[0]) == uc.Packet_Hello:
            H = C.cont[0]
            H._read()
            self.results['hello'] = 1

            def h2v(h):
                v = f"{h:#0{6}x}"
                v = v[2:4] + '.' + v[4:6]
                return v

            def h2vs(h):
                v = f"{h:#0{10}x}"
                v = v[4:6] + '.' + v[6:8] + ' r' + v[8:10]
                return v

            def h2d(h):
                v = f"{h:#0{10}x}"
                v = v[6:8] + '/' + v[8:10] + '/' + v[2:6]

                return v

            def h2t(h):
                v = f"{h:#0{10}x}"
                v = v[4:6] + ':' + v[6:8] + '.' + v[8:10]
                return v

            self.results['SW_version'] = h2vs(H.SW_version)
            self.results['FW_version'] = h2v(H.FW_Version)
            self.results['FW_ID'] = f"0x{H.FW_ID:#0{4}}"
            self.results['FW_Date'] = h2d(C.cont[0].FW_Date)
            self.results['FW_Time'] = h2t(C.cont[0].FW_Time)
        else:
            self.results['hello'] = 0
            self.results['SW_version'] = "N/A"
            self.results['FW_version'] = "N/A"
            self.results['FW_ID'] = "N/A"
            self.results['FW_Date'] = "N/A"
            self.results['FW_Time'] = "N/A"

        hb_num, sp_num = 0, 0
        hb_tmin, hb_tmax, last_hb, last_hbtime = 0, 0, None, None
        heartbeat_counter_ok = True

        sp_crc_ok = True
        occurences = {"high": 0, "med": 0, "low": 0}

        for packet in C.cont:
            if type(packet) == uc.Packet_Heartbeat:
                hb_num += 1
            elif type(packet) == uc.Packet_Spectrum:
                sp_num += 1
                packet._read()
                cat = spectrum_category(packet)
                occurences[cat] = occurences[cat] + 1
                sp_crc_ok = (sp_crc_ok & (not packet.error_crc_mismatch))

        for cat in ["high", "med", "low"]:
            self.results[f'frac_{cat}'] = occurences[cat] / sp_num
            # all 16 products in 1 packet have same AppId, divide by 16 for accurate statistics
            occurences[cat] = occurences[cat] // 16

        if sp_num < 1:
            passed = False
            sp_all = False
        else:
            sp_all = all([all([i in spectrum for i in range(16)]) for spectrum in C.spectra])
            probs = [self.frac_high, self.frac_med, 1.0 - self.frac_high - self.frac_med]
            passed = passed and fits([occurences[key] for key in ["high", "med", "low"]], probs, p_value=0.05)


        self.results['sp_all'] = int(sp_all)
        self.results['sp_num'] = len(C.spectra)
        self.results['heartbeat_received'] = hb_num
        self.results['hearbeat_count'] = int(hb_num)
        self.results['heartbeat_not_missing'] = int(heartbeat_counter_ok & (hb_tmax < 11))
        self.results['sp_packets_received'] = sp_num
        self.results['result'] = int(passed)
