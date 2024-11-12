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
        "navg1": 12,
        "navg2": 3,
    }  ## dictinary of options for the test
    options_help = {
        "time": "Total time to run the test.",
        "navg1": "Phase 1 (moving from FPGA) averages over 2^navg1 values.",
        "navg2": "Phase 2 (moving to TICK/TOCK) averages over 2^navg2 values.",
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
        scripter.set_Navg(self.navg1, self.navg2)
        scripter.set_avg_set_hi(frac_high)
        scripter.set_avg_set_mid(frac_mid)
        scripter.wait(5)
        scripter.start()
        scripter.wait(self.time)
        scripter.stop()
        scripter.time_to_die()
        return scripter

    def analyze(self, coll: uc.Collection, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.results = {}
        passed = True

        coll.cut_to_hello()
        self.get_versions(coll)

        hb_num = coll.num_heartbeats()
        sp_num = coll.num_spectra_packets()
        heartbeat_counter_ok = coll.heartbeat_counter_ok()
        sp_crc_ok = coll.all_spectra_crc_ok()
        occurences = {"high": 0, "med": 0, "low": 0}
        hb_tmax = coll.heartbeat_max_dt()

        for packet in coll.spectra:
            for i in range(16):
                if i in packet:
                    cat = spectrum_category(packet[i])
                    occurences[cat] = occurences[cat] + 1

        for cat in ["high", "med", "low"]:
            # all 16 products in 1 packet have same AppId, divide by 16 for accurate statistics
            occurences[cat] = occurences[cat] // 16
            self.results[f'frac_{cat}'] = f"{occurences[cat] / sp_num:.4f}"

        if sp_num < 1:
            passed = False
            sp_all = False
        else:
            sp_all = all([all([i in spectrum for i in range(16)]) for spectrum in coll.spectra])
            probs = [self.frac_high, self.frac_med, 1.0 - self.frac_high - self.frac_med]
            passed = passed and fits([occurences[key] for key in ["high", "med", "low"]], probs, p_value=0.05)

        passed = passed and coll.all_meta_error_free() == 1

        self.results['packets_received'] = len(coll.cont)
        self.results['sp_all'] = int(sp_all)
        self.results['sp_num'] = len(coll.spectra)
        self.results['sp_crc'] = sp_crc_ok
        self.results['heartbeat_received'] = hb_num
        self.results['hearbeat_count'] = int(hb_num)
        self.results['heartbeat_not_missing'] = int(heartbeat_counter_ok & (hb_tmax < 11))
        self.results['sp_packets_received'] = sp_num
        self.results['meta_error_free'] = coll.all_meta_error_free()
        self.results['result'] = int(passed)
