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
        "navg2": 6,
        "tr_start": 0,
        "tr_stop": 16,
        "tr_avg_shift": 2
    }  ## dictinary of options for the test
    options_help = {
        "time": "Total time to run the test.",
        "navg2": "Phase 2 (moving to TICK/TOCK) averages over 2^navg2 values.",
        "tr_start": "Start of time-resolved window.",
        "tr_stop": "End of time-resolved window.",
        "tr_avg_shift": "Average over every 2^tr_avg_shift values.",
    }  ## dictionary of help for the options


    def correct_tr_size(self):
        pass

    def generate_script(self):
        """ Generates a script for the test """
        if self.time < 30:
            print("Time raised to 30 seconds.")
            self.time = 30

        scripter = Scripter()
        scripter.reset()
        scripter.wait(5)

        scripter.set_Navg(Navg1=12, Navg2=self.navg2)
        scripter.set_tr_start_lsb(self.tr_start)
        scripter.set_tr_stop_lsb(self.tr_stop)
        scripter.set_tr_avg_shift(self.tr_avg_shift)

        scripter.start()
        scripter.wait(self.time)
        scripter.stop()

        return scripter

    def get_tr_shape(self):
        return (self.tr_stop - self.tr_start) // ( 1 << self.tr_avg_shift ), 1 << self.navg2

    # plot all TR spectra and return the string with includegraphics instruction
    # do not know in advance how many plots we need
    def plot_tr_spectra(self, coll: uc.Collection, figures_dir) -> str:
        figures_dir = os.path.abspath(figures_dir)
        result = "\n"
        for tr_packet_idx, trs in enumerate(coll.tr_spectra):
            fig, ax = plt.subplots(4, 4, figsize=(24, 24))
            fig_fname = os.path.join(figures_dir, f"tr_spectra_{tr_packet_idx}.pdf")
            for product_idx in range(16):
                if product_idx not in trs:
                    continue
                x, y = product_idx // 4, product_idx % 4
                data = trs[product_idx].data
                # do not plot more than 4 first bins, it'll be impossible to parse
                for bin_idx in range(min(data.shape[0], 4)):
                    ax[x][y].plot(data[bin_idx].flatten(), label=f"Bin {bin_idx+1}")
                ax[x][y].set_title(f"Product {product_idx+1}/16 of packet {tr_packet_idx+1}/{len(coll.tr_spectra)}")
                ax[x][y].set_xlabel(f"Phase 1 averaging index")
                ax[x][y].set_xticks(range(0, data[0].size, 1 << (self.navg2 - 3)))
                # TODO: how is this called?
                ax[x][y].set_ylabel(f"Value")
                ax[x][y].legend()
            fig.tight_layout()
            fig.savefig(fig_fname)
            result += f"\n\\includegraphics*[width=\\linewidth]{{{fig_fname}}}\n"
        return result


    def analyze(self, C, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.results = {}
        passed = True

        self.results['packets_received'] = len(C.cont)

        C.cut_to_hello()

        self.get_versions(C)

        hb_num, sp_num, tr_sp_num = 0, 0, 0
        hb_tmin, hb_tmax, last_hb, last_hbtime = 0, 0, None, None
        heartbeat_counter_ok = True
        tr_shape_ok = 1

        for packet in C.cont:
            if type(packet) == uc.Packet_Heartbeat:
                hb_num += 1
            elif type(packet) == uc.Packet_Spectrum:
                sp_num += 1
            elif type(packet) == uc.Packet_TR_Spectrum:
                tr_sp_num += 1
                try:
                    packet.data = packet.data.reshape(self.get_tr_shape())
                except:
                    tr_shape_ok = 0
                    print(f"Wrong shape of time-resolved packet: attempted to reshape: {packet.data.shape}")
                    print(f"to new shape: {self.get_tr_shape()}")

        self.results['sp_num'] = sp_num
        self.results['sp_all'] = C.has_all_products()
        self.results['tr_sp_all'] = C.has_all_tr_products()
        self.results['tr_sp_num'] = tr_sp_num
        self.results['sp_crc_ok'] = C.all_spectra_crc_ok()
        self.results['tr_sp_crc_ok'] = C.all_tr_spectra_crc_ok()
        self.results['tr_shape_ok'] = tr_shape_ok
        self.results['heartbeat_received'] = hb_num
        self.results['hearbeat_count'] = int(hb_num)
        self.results['heartbeat_not_missing'] = int(heartbeat_counter_ok & (hb_tmax < 11))
        self.results['sp_packets_received'] = sp_num
        self.results['tr_sp_packets_received'] = tr_sp_num
        self.results['tr_plots_str'] = self.plot_tr_spectra(C, figures_dir)

        passed = self.results['sp_all'] and self.results['tr_sp_all'] and self.results['sp_crc_ok'] and self.results['tr_sp_crc_ok'] and tr_shape_ok

        self.results['result'] = int(passed)
