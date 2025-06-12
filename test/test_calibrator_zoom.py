import sys

import uncrater.Packet_Calibrator

sys.path.append('.')
sys.path.append('./scripter/')
sys.path.append('./commander/')
import matplotlib.pyplot as plt
import os

from typing import List

import argparse
import numpy as np
from test_base import Test
from test_base import pycoreloop as cl
from lusee_script import Scripter
import uncrater as uc
from collections import defaultdict


class Test_CalibratorZoom(Test):
    name = "calibrator_zoom"
    version = 0.1
    description = """ Runs the WV calibrator EM """
    instructions = """ Connect the VW calibrator.  """
    default_options = {
        "mode": "manual",
        "slow": False,
    }  ## dictinary of options for the test
    options_help = {
        "mode": "manual",
        "slow": "Run the test in slow mode for SSL",
    }  ## dictionary of help for the options

    def generate_script(self):
        """ Generates a script for the test """

        S = Scripter()

        S.wait(1)
        S.reset()
        S.wait(3)

        if self.slow:
            S.set_dispatch_delay(120)

        # S.enable_heartbeat(False)
        S.set_Navg(14, 4)

        ### Main spectral engine

        S.set_ana_gain('HHHH')
        for i in range(4):
            S.set_route(i, None, i)

        S.set_bitslice(0, 10)
        for i in range(1, 4):
            S.set_bitslice(i, 19)

        S.cal_set_pfb_bin(1522)
        S.cal_set_zoom_navg(6)
        S.cal_enable(enable=True, mode=cl.pystruct.CAL_MODE_ZOOM)

        ch = 2
        freq = 38.05  # MHz
        ampl = 280

        S.awg_tone(ch, freq, ampl)

        S.start()
        S.cdi_wait_seconds(120)
        S.stop()
        S.request_eos()
        S.wait_eos()

        return S

    def plot_zoom_spectra(self, zoom_spectra_packets: List[uncrater.Packet_Calibrator.Packet_Cal_ZoomSpectra], figures_dir: str):
        """
        Plot the first 3 packets from zoom_spectra_packets list.
        Each packet gets its own figure with 2x2 subplots showing the 4 numpy arrays.
        """
        fig, axes = plt.subplots(3, 4, figsize=(16, 12))
        fig.suptitle('Zoom Spectra Data', fontsize=16, fontweight='bold')

        # Plot data for first 3 packets
        for packet_idx in range(min(3, len(zoom_spectra_packets))):
            packet = zoom_spectra_packets[packet_idx]

            # Row for this packet
            row = packet_idx

            axes[row, 0].plot(packet.ch1_autocorr)
            axes[row, 0].set_title(f'Packet {packet_idx}: Autocorrelation Channel 1')
            axes[row, 0].grid(True, alpha=0.3)

            axes[row, 1].plot(packet.ch2_autocorr)
            axes[row, 1].set_title(f'Packet {packet_idx}: Autocorrelation Channel 2')
            axes[row, 1].grid(True, alpha=0.3)

            axes[row, 2].plot(packet.ch1_2_corr_real)
            axes[row, 2].set_title(f'Packet {packet_idx}: Correlation Real')
            axes[row, 2].grid(True, alpha=0.3)

            axes[row, 3].plot(packet.ch1_2_corr_imag)
            axes[row, 3].set_title(f'Packet {packet_idx}: Correlation Imaginary')
            axes[row, 3].grid(True, alpha=0.3)

        # Adjust layout to prevent overlap
        plt.tight_layout()

        # Save to PDF
        plt.savefig(os.path.join(figures_dir, 'zoom_spectra.pdf'), format='pdf', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_spectra(self, spectra, figures_dir):
        fig_sp, ax_sp = plt.subplots(4, 4, figsize=(12, 12))
        freq = np.arange(1, 2048) * 0.025

        for i, S in enumerate(spectra):
            for c in range(16):
                x, y = c // 4, c % 4

                if c < 4:
                    data = S[c].data[1:]
                    ax_sp[x][y].plot(freq, data, label=f"{i}")
                    ax_sp[x][y].set_xscale('log')
                    ax_sp[x][y].set_yscale('log')
                else:
                    data = S[c].data[:400] * freq[:400] ** 2
                    ax_sp[x][y].plot(freq[:400], data)
            break
        for j in range(4):
            ax_sp[3][j].set_xlabel('frequency [MHz]')
            ax_sp[j][0].set_ylabel('power [uncalibrated]')

        fig_sp.tight_layout()
        plt.savefig(os.path.join(figures_dir, 'spectra.pdf'), format='pdf', dpi=300, bbox_inches='tight')
        plt.close()

    def analyze(self, C: uc.Collection, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.results = {}
        passed = True

        self.results['packets_received'] = len(C.cont)
        self.get_versions(C)

        crc_ok = C.all_spectra_crc_ok()
        if not crc_ok:
            passed = False

        has_all_products = C.has_all_products()
        if not has_all_products:
            passed = False

        self.results['zoom_sp_received'] = len(C.zoom_spectra_packets)

        if not len(C.zoom_spectra_packets) > 0:
            passed = False

        self.results['sp_num'] = len(C.spectra)

        if len(C.spectra) > 0:
            self.results['sp_crc'] = int(crc_ok)
            self.results['sp_all'] = int(has_all_products)
            self.results["meta_error_free"] = C.all_meta_error_free()
        else:
            self.results['sp_crc'] = 0
            self.results['sp_all'] = 0
            self.results["meta_error_free"] = 0

        self.results['result'] = int(passed)
        self.plot_zoom_spectra(C.zoom_spectra_packets, figures_dir)
        self.plot_spectra(C.spectra, figures_dir)
