import sys
sys.path.append('.')
sys.path.append('./scripter/')
sys.path.append('./commander/')
import matplotlib.pyplot as plt
import os
import os.path
from typing import Tuple, List
from icecream import ic

import numpy as np

from test_base import Test
from  lusee_script import Scripter
import uncrater as uc
from collections import defaultdict

if os.environ.get("CORELOOP_DIR") is not None:
    sys.path.append(os.environ.get("CORELOOP_DIR"))
import pycoreloop
from pycoreloop import pystruct as cl

from helpers_avg_reject import simulate_averaging, create_trig_spectra

N_PRODUCTS = 16
N_AUTO_PRODUCTS = 4
N_CHANNELS = 2048
INT32_MAX = np.iinfo(np.int32).max


def save_to_file(data: np.ndarray, fname: str):
    full_fname =  os.path.join(os.environ["CORELOOP_DIR"], "data", fname)
    # Save to file
    assert data.ndim == 3
    with open(full_fname, "w") as f:
        f.write(str(data.size))
        f.write(" ")
        for s in range(data.shape[0]):
            for p in range(data.shape[1]):
                # f.write(" ".join(map(str, data[s, p, :])) + " ")
                for c in range(data.shape[2]):
                    f.write(str(data[s, p, c]) + " ")
    print(f"saved data to {full_fname}")


def create_spec_reject_const(fname: str, n_spectra: int=4, val: int=INT32_MAX // 2, **kwargs) -> np.ndarray:
    data = val * np.ones((n_spectra, N_PRODUCTS, N_CHANNELS), dtype=np.int32)
    data = data.astype(dtype=np.int32)
    save_to_file(data, fname)
    return data

def create_spec_reject_simple(fname: str, navg2, n_spectra: int=4, val: int=INT32_MAX // 2, **kwargs) -> np.ndarray:
    data = val * np.ones((n_spectra, N_PRODUCTS, N_CHANNELS), dtype=np.int32)
    data = data.astype(dtype=np.int32)
    bad_product = 0
    for i in range(navg2, n_spectra):
        n_bad = 2 * (i % navg2 + 1)
        data[i, bad_product, :n_bad] = val // 100
    save_to_file(data, fname)
    return data


def create_spec_reject_normal_noise(fname: str, navg2: int, n_spectra: int=4, seed: int=42, val: int=INT32_MAX // 4, **kwargs) -> np.ndarray:
    np.random.seed(seed=seed)
    baseline = np.random.randint(-val, val, size=(N_PRODUCTS, N_CHANNELS), dtype=np.int32)
    spectra = []

    for spec_idx in range(n_spectra):
        if spec_idx < navg2:
            sigma = val / 20.0
        else:
            sigma = val / 3.0
        normal_noise = sigma * np.random.randn(N_PRODUCTS, N_CHANNELS)
        if spec_idx > navg2:
            for product in range(N_PRODUCTS):
                if product != spec_idx % 4:
                    normal_noise[product, :] = 0.0
                n_bad = 8 * (spec_idx % navg2)
                normal_noise[:, :n_bad] = 0.0

        spec = baseline + normal_noise
        spectra.append(spec.astype(np.int32))

    data = np.stack(spectra)
    save_to_file(data, fname)
    return data


# def get_average(spectra: np.ndarray, avg_iter: int, navg2: int, reject_ratio: int,
#                 max_bad: int, prev_accepted) -> Tuple[np.ndarray, List[int]]:
#     assert reject_ratio >= 0
#     if avg_iter == 0:
#         # all packets are accepted
#         spectra = spectra[:navg2, :, :]
#         avg = np.mean(spectra.astype(np.int64), axis=0, dtype=np.int64).astype(np.int32)
#         # if avg_mode == "float":
#         #     avg = np.mean(spectra.astype(np.float32), axis=0, dtype=np.float32).astype(np.int32)
#         # elif avg_mode == "int":
#         #     avg = np.sum(spectra.astype(np.int32) // navg2, axis=0, dtype=np.int32).astype(np.int32)
#         # elif avg_mode == "40bit":
#         #     avg = np.mean(spectra.astype(np.int64), axis=0, dtype=np.int64).astype(np.int32)
#         accepted = list(range(navg2))
#     else:
#         n_avg_iters = spectra.shape[0] // navg2
#         curr_avg_iter, prev_avg_iter = avg_iter % n_avg_iters, (avg_iter - 1) % n_avg_iters
#
#         curr_spectra = spectra[curr_avg_iter * navg2:(curr_avg_iter + 1) * navg2, :, :]
#
#         if len(prev_accepted) <= navg2 // 2:
#             # we accepted too few packets in previous iteration to compare with average, accepting all now
#             accepted = list(range(navg2))
#         else:
#             prev_spectra = spectra[prev_avg_iter * navg2:(prev_avg_iter + 1) * navg2, :N_AUTO_PRODUCTS, :]
#             prev_spectra = prev_spectra[prev_accepted, :, :]
#
#             prev_avg = np.mean(prev_spectra, axis=0, dtype=np.int64)
#
#             accepted = []
#
#             for spec_idx in range(navg2):
#                 spectrum = curr_spectra[spec_idx, :N_AUTO_PRODUCTS, :]
#                 assert spectrum.shape == prev_avg.shape
#                 delta = np.abs(spectrum.astype(np.int64) - prev_avg.astype(np.int64))
#                 if reject_ratio > 0:
#                     n_bad = np.sum(delta > prev_avg // reject_ratio)
#                 else:
#                     n_bad = 0
#                 if n_bad <= max_bad:
#                     accepted.append(spec_idx)
#
#         avg = np.mean(curr_spectra[accepted, :, :].astype(np.int64), axis=0, dtype=np.int64).astype(np.int32)
#
#     return avg, accepted
#
#
# def simulate_averaging(spectra, navg2, reject_ratio, max_bad, avg_mode, n_avg_iters):
#     # initialize with None, will be removed at the end
#     results = [None]
#     all_accepted = [None]
#
#     for avg_iter in range(n_avg_iters):
#         avg, accepted = get_average(spectra=spectra, avg_iter=avg_iter, navg2=navg2, reject_ratio=reject_ratio, max_bad=max_bad, prev_accepted=all_accepted[-1])
#         results.append(avg)
#         all_accepted.append(accepted)
#
#     results = results[1:]
#     all_accepted = all_accepted[1:]
#
#     return results, all_accepted


class Test_Reject1(Test):
    name = "reject1"
    version = 0.5
    description = """ Basic aliveness test of communication and spectral engine."""
    instructions = """ Do not need to connect anything."""
    default_options = {
        "seed": 42,
        "avg_mode": "int",
        "output_format": "32bit",
        "navgf": 1,
        "Navg2_shift": 3,
        "cdi_delay": 0,
        "reject_ratio": 4,
        "max_bad": 16,
        "n_spectra_to_receive": 8,
        "n_spectra_to_generate": 32,
        "data_gen_func": "create_trig_spectra"
    } ## dictinary of options for the test
    options_help = {
        "seed" : "Random seed",
        "avg_mode" : "Averaging mode. Can be 'int', '40bit', or 'float'",
        "output_format": "Output encoding, can be '32bit', '4to5', '10plus6'",
        "navgf" : "Number of bins to average in outputting spectra, 1-4",
        "Navg2_shift" : "Second phase averaging shift",
        "cdi_delay": "Delay in units of 1.26ms for the CDI to space packets by (0=225ns)",
        "reject_ratio": "Maximal deviation ratio to declare entry bad",
        "max_bad": "Maximal number of bad entries per spectrum to accept",
        "n_spectra_to_receive": "Number of averaged spectra to receive",
        "n_spectra_to_generate": "Number of (non-averaged) spectra to generate (averaging is looped)",
        "data_gen_func": "Function to generate spectrum"
    } ## dictionary of help for the options


    def setup_data(self):
        this_module = sys.modules[__name__]
        data_func = getattr(this_module, self.data_gen_func)
        self.spectrum_fname = "user_spectrum.dat"
        self.navg2 = 2 ** self.Navg2_shift

        if self.output_format == "32bit":
            self.format = cl.OUTPUT_32BIT
        elif self.output_format == "4to5":
            self.format = cl.OUTPUT_16BIT_4_TO_5
        elif self.output_format == "10plus6":
            self.format = cl.OUTPUT_16BIT_10_PLUS_6
        else:
            raise RuntimeError("Unknown output format, supported values are 32bit, 4to5 and 10plus6")

        self.true_data = data_func(self.spectrum_fname, n_spectra=self.n_spectra_to_generate, navg2=self.navg2, seed=self.seed)

        self.expected_data, self.expected_accepted = simulate_averaging(spectra=self.true_data,
                                                 navg2=self.navg2,
                                                 reject_ratio=self.reject_ratio,
                                                 max_bad=self.max_bad,
                                                 n_avg_iters=self.n_spectra_to_receive,
                                                 avg_mode=self.avg_mode,
                                                 navgf=self.navgf)


    def generate_script(self):
        """ Generates a script for the test """

        self.setup_data()

        assert self.n_spectra_to_generate >= self.navg2

        scripter = Scripter()
        scripter.reset()
        
        ## Sequence
        scripter.seq_begin()
        scripter.set_cdi_delay(int(self.cdi_delay))
        scripter.set_dispatch_delay(2)
        scripter.set_spectra_format(self.format)
        scripter.house_keeping(0)
        scripter.ADC_special_mode("normal")
        scripter.set_Navg(14, self.Navg2_shift)
        ic(self.reject_ratio, self.max_bad)
        scripter.reject_enable(enable=True, reject_frac = self.reject_ratio, max_bad = self.max_bad)
        scripter.set_avg_mode(self.avg_mode)
        scripter.set_avg_freq(self.navgf)
        scripter.start()
        scripter.cdi_wait_spectra(self.n_spectra_to_receive)
        scripter.stop()
        scripter.house_keeping(0)
        scripter.request_eos()
        scripter.flash_clear()
        scripter.seq_end(store_flash=True)
        scripter.wait_eos()

        return scripter

    def get_rel_error(self, received_prod, expected_prod):
        # return np.max(np.abs(received_prod - expected_prod) / (np.abs(expected_prod) + 0.0001))
        return np.max(np.abs(received_prod - expected_prod) / np.mean(np.abs(expected_prod)))

    def get_l1_rel_error(self, received_prod, expected_prod):
        return np.sum(np.abs(received_prod - expected_prod)) / np.sum(np.abs(expected_prod))

    def compute_errors(self, C):
        self.sp_max_rel_error = "10 000"
        self.sp_max_l1_rel_error = "10 000"
        if len(self.expected_data) != self.n_spectra_to_receive:
            return
        if C.num_spectra_packets() != self.n_spectra_to_receive:
            return

        rel_errors = []
        l1_rel_errors = []

        for s_idx, spectra in enumerate(C.spectra):
            real_weight = spectra["meta"].base.weight
            expected_weight = len(self.expected_accepted[s_idx])
            if real_weight != expected_weight:
                continue
            if real_weight:
                for prod_idx in range(N_PRODUCTS):
                    received_prod = spectra[prod_idx].data
                    expected_prod = self.expected_data[s_idx][prod_idx, :]
                    assert received_prod.size == self.n_received_channels() == expected_prod.size
                    rel_error = self.get_rel_error(received_prod, expected_prod)
                    l1_rel_error = self.get_l1_rel_error(received_prod, expected_prod)
                    rel_errors.append(rel_error)
                    l1_rel_errors.append(l1_rel_error)
                    ic(s_idx, l1_rel_error)

        self.sp_max_rel_error = f"{max(rel_errors):.4f}"
        self.sp_max_l1_rel_error = f"{max(l1_rel_errors):.4f}"


    def compare_spectra(self, C):
        if len(self.expected_data) != self.n_spectra_to_receive:
            return False
        if C.num_spectra_packets() != self.n_spectra_to_receive:
            print("ERROR: received data contains wrong number of spectra")
            return False

        result = True
        for s_idx, spectra in enumerate(C.spectra):
            real_weight = spectra["meta"].base.weight
            expected_weight = len(self.expected_accepted[s_idx])
            if real_weight != expected_weight:
                print(f"ERROR: spectrum idx = {s_idx}, expected to accept {expected_weight}, real weight = {real_weight}")
                result = result and False
            if real_weight:
                for prod_idx in range(N_PRODUCTS):
                    received_prod = spectra[prod_idx].data
                    expected_prod = self.expected_data[s_idx][prod_idx, :]
                    if not received_prod.size == self.n_received_channels() == expected_prod.size:
                        ic(received_prod.size, expected_prod.size, self.n_received_channels(), self.navgf)
                        assert False
                    rel_error = self.get_rel_error(received_prod, expected_prod)
                    l1_rel_error = self.get_rel_error(received_prod, expected_prod)
                    ic(s_idx, l1_rel_error)
                    if l1_rel_error > self.max_l1_rel_error() or rel_error > self.max_rel_error():
                        print(f"ERROR: compare_spectra, spectrum idx = {s_idx}, prod_idx = {prod_idx}, real weight = {real_weight}, {rel_error=}, {l1_rel_error=}")
                        result = result and False

        return result

    def are_weights_ok(self, C):
        result = 1
        for s_idx, spectra in enumerate(C.spectra):
            real_weight = spectra["meta"].base.weight
            expected_weight = len(self.expected_accepted[s_idx])
            if real_weight != expected_weight:
                print(f"ERROR: spectrum idx = {s_idx}, expected to accept {expected_weight}, real weight = {real_weight}")
                result = 0

        return result

    def spectra_number_ok(self, C):
        result = 1
        if len(self.expected_data) != self.n_spectra_to_receive:
            result = 0
        if C.num_spectra_packets() != self.n_spectra_to_receive:
            print("ERROR: received data contains wrong number of spectra")
            result = 0
        return result

    def n_received_channels(self):
        if self.navgf == 1:
            return N_CHANNELS
        if self.navgf == 2:
            return N_CHANNELS // 2
        if self.navgf in [3, 4]:
            return N_CHANNELS // 4

    def max_rel_error(self):
        if self.format in [cl.OUTPUT_16BIT_4_TO_5, cl.OUTPUT_16BIT_10_PLUS_6]:
            return 0.15
        else:
            return 0.01

    def max_l1_rel_error(self):
        if self.format in [cl.OUTPUT_16BIT_4_TO_5, cl.OUTPUT_16BIT_10_PLUS_6]:
            return 0.005
        else:
            return 0.001


    def rel_error_ok(self, C):
        rel_error_computed = False

        for s_idx, spectra in enumerate(C.spectra):
            real_weight = spectra["meta"].base.weight
            expected_weight = len(self.expected_accepted[s_idx])
            if real_weight != expected_weight:
                print(f"ERROR: spectrum idx = {s_idx}, expected to accept {expected_weight}, real weight = {real_weight}")
                return 0
            if not real_weight:
                continue


            for prod_idx in range(N_PRODUCTS):
                rel_error_computed = True
                received_prod = spectra[prod_idx].data
                expected_prod = self.expected_data[s_idx][prod_idx, :]
                assert received_prod.size == self.n_received_channels() and expected_prod.size == self.n_received_channels()
                # rel_error = np.sum(np.abs(received_prod - expected_prod)) / np.sum(np.abs(expected_prod))
                rel_error = self.get_rel_error(received_prod, expected_prod)
                l1_rel_error = self.get_l1_rel_error(received_prod, expected_prod)
                if rel_error > self.max_rel_error() or l1_rel_error > self.max_l1_rel_error():
                    print(f"ERROR: spectrum idx = {s_idx}, prod_idx = {prod_idx}, real weight = {real_weight}, {rel_error=}")
                    return 0

        if not rel_error_computed:
            print(f"ERROR: rel_error never computed, all weights are 0!")
            return 0
        return 1


    def plot_weights(self, C, figures_dir):
        """Plot received weights and expected weights if they differ"""
        real_weights = []
        expected_weights = []

        for s_idx, spectra in enumerate(C.spectra):
            real_weight = spectra["meta"].base.weight
            expected_weight = len(self.expected_accepted[s_idx])
            real_weights.append(real_weight)
            expected_weights.append(expected_weight)

        fig, ax = plt.subplots(figsize=(10, 6))

        x = np.arange(len(real_weights))

        # Check if weights match
        weights_match = all(r == e for r, e in zip(real_weights, expected_weights))

        if weights_match:
            # Only plot real weights if they match expected
            ax.bar(x, real_weights, color='green', alpha=0.7, label='Received weights')
        else:
            # Plot both if they don't match
            width = 0.35
            ax.bar(x - width/2, real_weights, width, color='blue', alpha=0.7, label='Received weights')
            ax.bar(x + width/2, expected_weights, width, color='red', alpha=0.7, label='Expected weights')

        ax.set_xlabel('Spectrum Index')
        ax.set_ylabel('Weight')
        ax.set_title('Spectrum Weights Comparison')
        ax.set_xticks(x)
        ax.set_xticklabels([str(i) for i in x])
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, max(max(real_weights, default=0), max(expected_weights, default=0)) + 1)

        plt.tight_layout()
        plt.savefig(os.path.join(figures_dir, "weights.pdf"))
        plt.close()

    def plot_spectra(self, C, figures_dir):
        """Plot the first 3 spectra with 4x4 grid of products"""
        n_spectra_to_plot = min(8, len(C.spectra))

        for spec_idx in range(n_spectra_to_plot):
            fig, axes = plt.subplots(4, 4, figsize=(16, 12))
            fig.suptitle(f'Spectrum {spec_idx + 1}', fontsize=14)

            spectra = C.spectra[spec_idx]
            real_weight = spectra["meta"].base.weight

            for prod_idx in range(N_PRODUCTS):
                row = prod_idx // 4
                col = prod_idx % 4
                ax = axes[row, col]

                received_prod = spectra[prod_idx].data
                expected_prod = self.expected_data[spec_idx][prod_idx, :]

                # Calculate relative error if weight > 0
                if real_weight > 0:
                    rel_error = self.get_rel_error(received_prod, expected_prod)
                    l1_rel_error = self.get_l1_rel_error(received_prod, expected_prod)
                else:
                    rel_error = float('inf')  # Force special handling for zero weight
                    l1_rel_error = float('inf')

                # Use log scale for first 4 products (auto-correlations)
                if prod_idx < 4:
                    ax.set_yscale('log')

                channels = np.arange(self.n_received_channels())


                if real_weight == 0:
                    # Special color for zero weight - plot only received
                    ax.plot(channels, received_prod, color='orange', linewidth=0.5,
                           label='Received (weight=0)', alpha=0.8)
                elif rel_error > 0.001:
                    # Plot both if error is too high
                    ax.plot(channels, received_prod, color='blue', linewidth=0.5,
                           label='Received', alpha=0.7)
                    ax.plot(channels, expected_prod, color='red', linewidth=0.5,
                           label='Expected', alpha=0.7, linestyle='--')
                else:
                    # Just plot received if error is acceptable
                    ax.plot(channels, received_prod, color='green', linewidth=0.5,
                           label='Received', alpha=0.8)

                ax.set_title(f'Product {prod_idx}, rel. error {rel_error:.4f}, L1: {l1_rel_error:.4f}', fontsize=10)
                ax.set_xlabel('Channel', fontsize=8)
                ax.set_ylabel('Value', fontsize=8)
                ax.tick_params(axis='both', labelsize=6)
                ax.grid(True, alpha=0.3)

                # Add legend only if both are plotted
                if real_weight > 0 and rel_error > 0.001:
                    ax.legend(fontsize=6, loc='upper right')
                elif real_weight == 0:
                    ax.legend(fontsize=6, loc='upper right')

            plt.tight_layout()
            plt.savefig(os.path.join(figures_dir, f"spectra{spec_idx + 1}.pdf"))
            plt.close()


    def analyze(self, C, uart, commander, figures_dir):
        """ Analyzes the results of the test.
            Returns true if test has passed.
        """
        self.setup_data()
        self.results = {}
        passed = True

        self.results['packets_received'] = len(C.cont)

        if len(C.cont) == 0:
            print ("No packets received, aborting")
            self.results['result'] = 0
            return 

        self.get_versions(C)

        if not self.compare_spectra(C):
            passed = False

        self.compute_errors(C)

        num_hb = C.num_heartbeats()
        num_sp = C.num_spectra_packets()
        num_hk = C.num_housekeeping_packets()
        hb_tmin = C.heartbeat_min_dt()
        hb_tmax = C.heartbeat_max_dt()
        hk_start = C.housekeeping_packets[0] if num_hk > 0 else None
        hk_end = C.housekeeping_packets[-1] if num_hk > 1 else None
        heartbeat_counter_ok = C.heartbeat_counter_ok()

        self.results["heartbeat_received"] = num_hb
        self.results["hearbeat_count"] = int(num_hb)
        self.results["heartbeat_not_missing"] = int(heartbeat_counter_ok)
        self.results["heartbeat_mindt"] = f"{hb_tmin:.3f}"
        self.results["heartbeat_maxdt"] = f"{hb_tmax:.3f}"
        self.results["sp_packets_received"] = num_sp
        self.results["hk_packets_received"] = num_hk

        if (hk_start is not None) and (hk_end is not None):
            delta_t = hk_end.time - hk_start.time
            self.results["timer_ok"] = int ((delta_t>0)& (delta_t<10000)) ## let"s be generous here
            self.results["no_errors"] =  int(hk_start.core_state.base.errors == 0 and hk_end.core_state.base.errors == 0)
        else:
            self.results["timer_ok"] = 0
            self.results["no_errors"] = 0

        crc_ok = C.all_spectra_crc_ok()
        sp_all = C.has_all_products()

        sp_number_ok = self.spectra_number_ok(C)
        sp_weights_ok = self.are_weights_ok(C)
        sp_rel_error_ok = self.rel_error_ok(C)

        if len(C.spectra)>0:
            self.results["sp_crc"] = int(crc_ok)
            self.results["sp_all"] = int(sp_all)
            self.results["sp_num"] = len(C.spectra)
            self.results["meta_error_free"] = C.all_meta_error_free()
            self.results["sp_weights_ok"] = sp_weights_ok
            self.results["sp_number_ok"] = sp_number_ok
            self.results["sp_rel_error_ok"] = sp_rel_error_ok
        else:
            self.results["sp_crc"] = 0
            self.results["sp_all"] = 0
            self.results["sp_pk_ok"] = 0
            self.results["sp_num"] = 0
            self.results["sp_weights_ok"] = 0
            self.results["sp_number_ok"] = 0
            self.results["rel_error_ok"] = 0
            self.results["meta_error_free"] = 0
            self.results["sp_rel_error_ok"] = 0

        self.results["sp_max_rel_error"] = self.sp_max_rel_error
        self.results["sp_max_l1_rel_error"] = self.sp_max_l1_rel_error

        passed = (passed and crc_ok and sp_all and sp_number_ok and sp_weights_ok and sp_rel_error_ok)

        self.results["result"] = int(passed)

        self.plot_weights(C, figures_dir)
        self.plot_spectra(C, figures_dir)
