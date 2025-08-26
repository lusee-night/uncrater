import os
import sys
import matplotlib.pyplot as plt

import numpy as np
try:
    from icecream import ic
except:
    print ("Sorry, no ice cream.")

sys.path.append(".")
sys.path.append("./scripter/")
sys.path.append("./commander/")

if os.environ.get("CORELOOP_DIR") is not None:
    sys.path.append(os.environ.get("CORELOOP_DIR"))

from test_base import Test

from lusee_script import Scripter
import pycoreloop
from pycoreloop import appId
from pycoreloop import pystruct as cl
from pycoreloop import format_from_value

import uncrater as uc


class Test_EncodingFormat(Test):
    name = "encoding_format"
    version = 0.1
    description = """ Check that different compression formats work as expected."""
    instructions = """ Do not need to connect anything."""
    default_options = {
        "time": 30,
        "navg1": 14,
        "navg2": 3,
        "navgf": 1,
        "ramp": True,
    }  ## dictinary of options for the test
    options_help = {
        "time": "Total time to run the test.",
        "navg1": "Phase 1 (moving from FPGA) averages over 2^navg1 values.",
        "navg2": "Phase 2 (moving to TICK/TOCK) averages over 2^navg2 values.",
        "navgf": "Frequency averaging.",
        "ramp": "Use ramp mode for ADCs.",
    }  ## dictionary of help for the options

    def generate_script(self):
        """Generates a script for the test"""

        self.formats = [cl.OUTPUT_32BIT, cl.OUTPUT_16BIT_10_PLUS_6, cl.OUTPUT_16BIT_4_TO_5]

        min_time = 10 * len(self.formats)

        if self.time < min_time:
            print(f"Time raised to {min_time} seconds.")
            self.time = min_time

        scripter = Scripter()
        scripter.reset()
        scripter.wait(5)
        if self.ramp:
            scripter.ADC_special_mode('ramp')
        scripter.set_cdi_delay(2)
        scripter.set_Navg(Navg1=self.navg1, Navg2=self.navg2)
        scripter.set_avg_freq(self.navgf)

        for format in self.formats:
            scripter.wait(5)
            scripter.set_spectra_format(format)
            scripter.start()
            scripter.wait(self.time // len(self.formats))
            scripter.stop()
            scripter.wait(5)

        return scripter

    # plot all spectra as in test_alive and return the string with includegraphics instruction
    # do not know in advance how many plots we need
    def plot_spectra_as_alive(self, coll: uc.Collection, figures_dir) -> str:
        figures_dir = os.path.abspath(figures_dir)
        result = "\n"

        # 2048, not 2049: we drop the first entry in data later
        freq = np.arange(1, 2048) * 0.025
        for sp_packet_idx, spec in enumerate(coll.spectra):

            fmt = format_from_value[spec["meta"].format]
            fig, ax = plt.subplots(4, 4, figsize=(24, 24))
            fig_fname = os.path.join(figures_dir, f"spectra_as_alive_{sp_packet_idx}.pdf")

            for product_idx in range(16):
                if product_idx not in spec:
                    continue
                x, y = product_idx // 4, product_idx % 4
                if product_idx < 4:
                    data = spec[product_idx].data[1:]
                    ax[x][y].plot(freq, data, label=f"Product {product_idx+1}")
                    ax[x][y].set_xscale('log')
                    ax[x][y].set_yscale('log')
                else:
                    data= spec[product_idx].data[:400] * freq[:400]**2
                    ax[x][y].plot(freq[:400], data)
                ax[x][y].legend()
                ax[x][y].set_title(f"Packet {sp_packet_idx+1}/{len(coll.spectra)}, encoding {fmt}")

            for i in range(4):
                ax[3][i].set_xlabel('frequency [MHz]')
                ax[i][0].set_ylabel('power [uncalibrated]')

            fig.tight_layout()
            fig.savefig(fig_fname)
            plt.close(fig)
            result += f"\n\\includegraphics*[width=\\linewidth]{{{fig_fname}}}\n"

            if sp_packet_idx > 20:
                print(f"Warning: plotting only the first 20 spectra out of {len(coll.spectra)}")

        return result


    # plot all spectra and return the string with includegraphics instruction
    # do not know in advance how many plots we need
    def plot_spectra(self, coll: uc.Collection, figures_dir) -> str:
        figures_dir = os.path.abspath(figures_dir)
        result = "\n"
        freq = np.arange(1, 2049)
        for sp_packet_idx, spec in enumerate(coll.spectra):
            fmt = format_from_value[spec["meta"].format]
            fig, ax = plt.subplots(4, 4, figsize=(24, 24))
            fig_fname = os.path.join(figures_dir, f"spectra_{sp_packet_idx}.pdf")
            for product_idx in range(16):
                if product_idx not in spec:
                    continue
                x, y = product_idx // 4, product_idx % 4
                data = spec[product_idx].data
                # do not plot more than 4 first bins, it'll be impossible to parse
                ax[x][y].plot(freq, data, label=f"Product {product_idx+1}")
                ax[x][y].set_title( f"Packet {sp_packet_idx+1}/{len(coll.spectra)}, encoding {fmt}" )
                ax[x][y].set_xlabel(f"Frequency")
                # TODO: how is this called?
                ax[x][y].set_ylabel(f"Value")
                if product_idx < 4:
                    ax[x][y].set_xscale("log")
                    ax[x][y].set_yscale("log")
                ax[x][y].legend()
            fig.tight_layout()
            fig.savefig(fig_fname)
            plt.close(fig)
            result += f"\n\\includegraphics*[width=\\linewidth]{{{fig_fname}}}\n"
            if sp_packet_idx > 30:
                print( f"Warning: plotting only the first 30 spectra out of {len(coll.spectra)}" )
        return result

    def analyze(self, coll, uart, commander, figures_dir):
        """Analyzes the results of the test.
        Returns true if test has passed.
        """
        self.results = {}
        self.get_versions(coll)
        tr_shape_ok = 1

        # we cannot reshape when reading TR spectra from disk,
        # because we don't know parameter for correct shape, so we have to do it here
        for i, packet in enumerate(coll.tr_spectra):
            for j in range(16):
                if j not in packet:
                    continue
                try:
                    packet[j].data = packet[j].data.reshape(self.get_tr_shape())
                except:
                    tr_shape_ok = 0
                    print(
                        f"Wrong shape of time-resolved packet: attempted to reshape: {packet[j].data.shape}"
                    )
                    print(f"to new shape: {self.get_tr_shape()}")

        self.results["packets_received"] = len(coll.cont)
        self.results["sp_num"] = coll.num_spectra_packets()
        self.results["sp_all"] = coll.has_all_products()
        self.results["tr_sp_all"] = coll.has_all_tr_products()
        self.results["tr_sp_num"] = coll.num_tr_spectra_packets()
        self.results["sp_crc_ok"] = coll.all_spectra_crc_ok()
        self.results["tr_sp_crc_ok"] = coll.all_tr_spectra_crc_ok()
        self.results["tr_shape_ok"] = tr_shape_ok
        self.results["heartbeat_received"] = coll.num_heartbeats()
        self.results["heartbeat_not_missing"] = int(
            coll.heartbeat_counter_ok() and coll.heartbeat_max_dt() < 11
        )
        self.results["sp_packets_received"] = coll.num_spectra_packets()
        ic(figures_dir)
        if not (figures_dir is None):
            self.results["plots_calibrated_str"] = self.plot_spectra_as_alive(coll, figures_dir)
            self.results["plots_raw_str"] = self.plot_spectra(coll, figures_dir)
        self.results["all_meta_error_free"] = coll.all_meta_error_free()

        passed = (
            self.results["sp_all"]
            and self.results["tr_sp_all"]
            and self.results["sp_crc_ok"]
            and self.results["tr_sp_crc_ok"]
            and self.results["all_meta_error_free"]
            and tr_shape_ok
        )

        self.results["result"] = int(passed)
