import os
import sys
import matplotlib.pyplot as plt

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

from pycoreloop import appId

import uncrater as uc


class Test_TRSpectra(Test):
    name = "time_resolved"
    version = 0.1
    description = """ Check that time resolved spectra are received."""
    instructions = """ Do not need to connect anything."""
    default_options = {
        "time": 30,
        "navg1": 14,
        "navg2": 3,
        "ramp": False,
        "tr_start": 0,
        "tr_stop": 8,
        "tr_avg_shift": 2,
    }  ## dictinary of options for the test
    options_help = {
        "time": "Total time to run the test.",
        "navg1": "Phase 1 (moving from FPGA) averages over 2^navg1 values.",
        "navg2": "Phase 2 (moving to TICK/TOCK) averages over 2^navg2 values.",
        "ramp": "Use ramp mode for ADCs.",
        "tr_start": "Start of time-resolved window.",
        "tr_stop": "End of time-resolved window.",
        "tr_avg_shift": "Average over every 2^tr_avg_shift values.",
    }  ## dictionary of help for the options

    def generate_script(self):
        """Generates a script for the test"""
        if self.time < 30:
            print("Time raised to 30 seconds.")
            self.time = 30

        scripter = Scripter()
        scripter.reset()
        scripter.wait(5)
        if self.ramp:
            scripter.ADC_special_mode('ramp')
        scripter.set_cdi_delay(2)
        scripter.set_Navg(Navg1=self.navg1, Navg2=self.navg2)
        scripter.set_tr_start_stop(self.tr_start, self.tr_stop)
        scripter.set_tr_avg_shift(self.tr_avg_shift)

        scripter.start()
        scripter.wait(self.time)
        scripter.stop()
        scripter.wait(5)
        return scripter

    def get_tr_shape(self):
        return 1 << self.navg2, (self.tr_stop - self.tr_start) // (
            1 << self.tr_avg_shift
        )

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
                for bin_idx in range(min(data.shape[1], 4)):
                    ax[x][y].plot(data[:, bin_idx].flatten(), label=f"Bin {bin_idx+1}")
                ax[x][y].set_title(
                    f"Product {product_idx+1}/16 of packet {tr_packet_idx+1}/{len(coll.tr_spectra)}"
                )
                ax[x][y].set_xlabel(f"Phase 1 averaging index")
                ax[x][y].set_xticks(
                    range(0, data[:, 0].size, 1 << max(0, (self.navg2 - 3)))
                )
                # TODO: how is this called?
                ax[x][y].set_ylabel(f"Value")
                ax[x][y].legend()
            fig.tight_layout()
            fig.savefig(fig_fname)
            plt.close(fig)
            result += f"\n\\includegraphics*[width=\\linewidth]{{{fig_fname}}}\n"
            if tr_packet_idx > 5:
                print(
                    f"Warning: plotting only the first 5 TR spectra out of {len(coll.tr_spectra)}"
                )
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
        self.results["tr_sp_packets_received"] = coll.num_tr_spectra_packets()
        if not (figures_dir is None):
            self.results["tr_plots_str"] = self.plot_tr_spectra(coll, figures_dir)
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
