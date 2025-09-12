import os
import os.path
import numpy as np
import warnings
from typing import List, Tuple, Optional

from icecream import ic

# warnings.simplefilter("once", UserWarning)


N_PRODUCTS = 16
N_AUTO_PRODUCTS = 4
N_CHANNELS = 2048
INT32_MAX = np.iinfo(np.int32).max
INT32_MIN = np.iinfo(np.int32).min

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


def create_trig_spectra(fname: str, n_spectra: int=4, max_amplitude: int= 3 * INT32_MAX // 4, seed: int=42, **kwargs) -> np.ndarray:
    np.random.seed(seed)

    apply_noise = True

    # Noise parameters (as variables, not function parameters)
    normal_noise_std = 0.002  # Standard deviation for normal noise (as fraction of signal)
    salt_pepper_prob = 0.0001  # Probability of salt-and-pepper noise
    salt_pepper_intensity = 0.2  # Intensity of salt-and-pepper noise (as fraction of max_amplitude)
    spectrum_variation_std = 0.005  # Small variation between spectra

    data = np.zeros((n_spectra, N_PRODUCTS, N_CHANNELS), dtype=np.float64)

    # Create channel indices for trigonometric functions
    x = np.linspace(0, 4 * np.pi, N_CHANNELS)

    # Generate base signal for each product (consistent across spectra)
    for product in range(N_PRODUCTS):
        # Decide if this product should be large or small amplitude
        is_large_amplitude = (product % 3 == 0)  # Every 3rd product is large
        if is_large_amplitude:
            base_amplitude = max_amplitude * np.random.uniform(0.6, 0.9)
        else:
            base_amplitude = np.random.uniform(50, 150)

        # Decide if this product should be smooth or have patches
        has_patches = (product % 4 == 1 or product % 4 == 2)  # Half the products have patches

        # Generate base trigonometric signal
        n_frequencies = np.random.randint(1, 4)  # 1 to 3 frequencies
        base_signal = np.zeros(N_CHANNELS)

        for _ in range(n_frequencies):
            freq = np.random.uniform(0.5, 3.0)
            phase = np.random.uniform(0, 2 * np.pi)
            amplitude_fraction = np.random.uniform(0.3, 1.0)

            # Mix sine and cosine with random coefficients
            sin_coeff = np.random.uniform(-1, 1)
            cos_coeff = np.random.uniform(-1, 1)

            base_signal += amplitude_fraction * (
                sin_coeff * np.sin(freq * x + phase) +
                cos_coeff * np.cos(freq * x + phase)
            )

        # Add patches for localized peaks if needed
        if has_patches:
            n_patches = np.random.randint(2, 5)
            for _ in range(n_patches):
                patch_center = np.random.randint(N_CHANNELS // 4, 3 * N_CHANNELS // 4)
                patch_width = np.random.randint(20, 80)
                patch_amplitude = np.random.uniform(0.5, 2.0)

                # Create Gaussian-like patch
                patch_indices = np.arange(max(0, patch_center - patch_width),
                                        min(N_CHANNELS, patch_center + patch_width))
                if len(patch_indices) > 0:
                    patch_signal = patch_amplitude * np.exp(
                        -0.5 * ((patch_indices - patch_center) / (patch_width / 3)) ** 2
                    )
                    base_signal[patch_indices] += patch_signal

        # Normalize and scale to desired amplitude
        if np.std(base_signal) > 0:
            base_signal = base_signal / np.std(base_signal) * base_amplitude * 0.3
        else:
            base_signal = np.full(N_CHANNELS, base_amplitude * 0.1)

        # Apply base signal to all spectra for this product
        for spectrum in range(n_spectra):
            data[spectrum, product, :] = base_signal.copy()

    # Add small variations between spectra
    for spectrum in range(n_spectra):
        for product in range(N_PRODUCTS):
            variation = np.random.normal(0, spectrum_variation_std * np.abs(data[spectrum, product, :]).mean(), N_CHANNELS)
            data[spectrum, product, :] += variation

    if apply_noise:

        # Add normal noise
        for spectrum in range(n_spectra):
            for product in range(N_PRODUCTS):
                signal_std = np.std(data[spectrum, product, :])
                if signal_std > 0:
                    noise = 0.05 * np.random.normal(0, normal_noise_std * signal_std, N_CHANNELS)
                    data[spectrum, product, :] += noise

        # Add salt-and-pepper noise (scaled per product amplitude)
        for spectrum in range(n_spectra):
            for product in range(N_PRODUCTS):
                product_amp = np.max(np.abs(data[spectrum, product, :]))
                # Scale noise based on product amplitude
                noise_level = salt_pepper_intensity * product_amp
                salt_pepper_mask = np.random.random(N_CHANNELS) < salt_pepper_prob
                salt_pepper_values = np.random.choice([-1, 1], size=N_CHANNELS) * noise_level
                data[spectrum, product, :] += salt_pepper_mask * salt_pepper_values

    # Convert to int32
    data = np.clip(data, INT32_MIN, INT32_MAX).astype(np.int32)

    # Ensure the first N_AUTO_PRODUCTS components are non-negative
    data[:, :N_AUTO_PRODUCTS, :] = np.abs(data[:, :N_AUTO_PRODUCTS, :])

    assert data.shape[0] == n_spectra and data.shape[1] == N_PRODUCTS and data.shape[2] == N_CHANNELS
    save_to_file(data, fname)
    return data


def average_spectra(spectra: np.ndarray,
                    navg2: int,
                    accepted: List[int],
                    avg_mode: str,
                    navgf: int) -> np.ndarray:

    assert spectra.shape[0] <= navg2
    assert navgf in [1, 2, 3, 4]

    if accepted is None:
        accepted = list(range(spectra.shape[0]))

    if len(accepted) == 0:
        warnings.warn("average_spectra: for all-rejected, just return something")
        accepted = list(range(spectra.shape[0]))

    assert all([i < spectra.shape[0] for i in accepted])

    assert len(accepted) == len(set(accepted))

    assert len(accepted) > 0, "This function does not handle all-rejected case"

    if navgf == 1:
        if avg_mode == "int":
            result = np.sum(spectra[accepted, :, :] // navg2, axis=0, dtype=np.int32)
        elif avg_mode == "40bit":
            result = (np.sum(spectra[accepted, :, :].astype(np.int64), axis=0) // np.int64(navg2)).astype(np.int32)
        elif avg_mode == "float":
            result = (np.sum(spectra[accepted, :, :].astype(np.float32), axis=0) / np.float32(navg2)).astype(np.int32)
    elif navgf == 2:
        if avg_mode == "int":
            x = spectra[accepted, :, ::2] // np.int32(2 * navg2) + spectra[accepted, :, 1::2] // np.int32(2 * navg2)
            result = np.sum(x, axis=0, dtype=np.int32)
        elif avg_mode == "40bit":
            x = spectra[accepted, :, ::2].astype(np.int64) + spectra[accepted, :, 1::2].astype(np.int64)
            result = (np.sum(x, axis=0) // np.int64(2 * navg2)).astype(np.int32)
        elif avg_mode == "float":
            x = spectra[accepted, :, ::2].astype(np.float32) + spectra[accepted, :, 1::2].astype(np.float32)
            result = (np.sum(x, axis=0) / np.float32(2 * navg2)).astype(np.int32)
    elif navgf == 3:
        if avg_mode == "int":
            x = spectra[accepted, :, ::4] // np.int32(4 * navg2) + spectra[accepted, :, 1::4] // np.int32(4 * navg2)
            x += spectra[accepted, :, 2::4] // np.int32(4 * navg2)
            result = np.sum(x, axis=0, dtype=np.int32)
        elif avg_mode == "40bit":
            x = spectra[accepted, :, ::4].astype(np.int64) + spectra[accepted, :, 1::4].astype(np.int64)
            x += spectra[accepted, :, 2::4].astype(np.int64)
            x = x // np.int64(4)
            result = (np.sum(x, axis=0) // np.int64(navg2)).astype(np.int32)
        elif avg_mode == "float":
            x = spectra[accepted, :, ::4].astype(np.float32) + spectra[accepted, :, 1::4].astype(np.float32)
            x += spectra[accepted, :, 2::4].astype(np.float32)
            result = (np.sum(x, axis=0) / np.float32(4 * navg2)).astype(np.int32)
    elif navgf == 4:
        if avg_mode == "int":
            x = spectra[accepted, :, ::4] // np.int32(4 * navg2) + spectra[accepted, :, 1::4] // np.int32(4 * navg2)
            x += spectra[accepted, :, 2::4] // np.int32(4 * navg2) + spectra[accepted, :, 3::4] // np.int32(4 * navg2)
            result = np.sum(x, axis=0, dtype=np.int32)
        elif avg_mode == "40bit":
            x = spectra[accepted, :, ::4].astype(np.int64) + spectra[accepted, :, 1::4].astype(np.int64)
            x += spectra[accepted, :, 2::4].astype(np.int64) + spectra[accepted, :, 3::4].astype(np.int64)
            x = x // np.int64(4)
            result = (np.sum(x, axis=0) // np.int64(navg2)).astype(np.int32)
        elif avg_mode == "float":
            x = spectra[accepted, :, ::4].astype(np.float32) + spectra[accepted, :, 1::4].astype(np.float32)
            x += spectra[accepted, :, 2::4].astype(np.float32) + spectra[accepted, :, 3::4].astype(np.float32)
            result = (np.sum(x, axis=0) / np.float32(4 * navg2)).astype(np.int32)

    # above we imitated coreloop logic: always divide by Navg2, not by len(accepted)
    # this is accounted for in the reading code (Packet_Spectrum)

    if len(accepted) != navg2:
        result = result.astype(np.float64) / len(accepted) * navg2

    return result


def filter_and_average(spectra: np.ndarray, avg_iter: int, navg2: int, reject_ratio: int,
                       max_bad: int, prev_accepted, avg_mode: str, navgf: int) -> Tuple[np.ndarray, List[int]]:
    assert reject_ratio >= 0
    if avg_iter == 0:
        # all packets are accepted
        spectra = spectra[:navg2, :, :]
        accepted = list(range(navg2))
        avg = average_spectra(spectra, navg2=navg2, accepted=accepted, avg_mode=avg_mode, navgf=navgf)
    else:
        n_avg_iters = spectra.shape[0] // navg2
        curr_avg_iter, prev_avg_iter = avg_iter % n_avg_iters, (avg_iter - 1) % n_avg_iters

        curr_spectra = spectra[curr_avg_iter * navg2:(curr_avg_iter + 1) * navg2, :, :]

        if len(prev_accepted) <= navg2 // 2:
            # we accepted too few packets in previous iteration to compare with average, accepting all now
            accepted = list(range(navg2))
        else:
            prev_spectra = spectra[prev_avg_iter * navg2:(prev_avg_iter + 1) * navg2, :N_AUTO_PRODUCTS, :]
            # TODO: actual logic is more delicate
            # prev_spectra = prev_spectra[prev_accepted, :, :]
            # prev_avg = np.mean(prev_spectra, axis=0, dtype=np.int64)
            # this is for spectra_in logic, navgf=1 means we don't average over different bins
            if avg_mode == "40bit":
                prev_spectra = prev_spectra[prev_accepted, :, :]
                prev_avg = np.sum(prev_spectra, axis=0, dtype=np.int64) // np.int64(len(prev_accepted))
            elif avg_mode == "float":
                prev_spectra = prev_spectra[prev_accepted, :, :].astype(np.float32)
                prev_avg = np.sum(prev_spectra, axis=0, dtype=np.float32) / np.float32(len(prev_accepted))
            elif avg_mode == "int":
                prev_spectra = prev_spectra[prev_accepted, :, :].astype(np.int32)
                prev_avg = np.sum(prev_spectra, axis=0, dtype=np.int32) // np.int32(len(prev_accepted))
                prev_avg = prev_avg * np.int32(navg2)

            # prev_avg = average_spectra(spectra=prev_spectra, navg2=navg2, accepted=prev_accepted, avg_mode=avg_mode, navgf=1)

            accepted = []

            for spec_idx in range(navg2):
                spectrum = curr_spectra[spec_idx, :N_AUTO_PRODUCTS, :]
                if spectrum.shape != prev_avg.shape:
                    ic(spectrum.shape)
                    assert spectrum.shape == prev_avg.shape
                if avg_mode in ["40bit", "int"]:
                    delta = np.abs(spectrum.astype(np.int64) - prev_avg.astype(np.int64))
                else:
                    delta = np.abs(spectrum.astype(np.float32) - prev_avg)

                n_bad = 0
                if reject_ratio > 0:
                    bad_channels = []
                    for p_idx in range(N_AUTO_PRODUCTS):
                        for channel_idx in range(N_CHANNELS):
                            if avg_mode == "float":
                                if delta[p_idx, channel_idx] > prev_avg[p_idx, channel_idx] / np.float32(reject_ratio):
                                    bad_channels.append((p_idx, channel_idx))
                            else:
                                if delta[p_idx, channel_idx] > prev_avg[p_idx, channel_idx] // reject_ratio:
                                    bad_channels.append((p_idx, channel_idx))
                    # if avg_iter == 1 and spec_idx == 0:
                    #     ic(avg_iter, spec_idx, bad_channels)
                    n_bad = len(bad_channels)

                # if reject_ratio > 0:
                #     n_bad = np.sum(delta > prev_avg // reject_ratio)
                # else:
                #     n_bad = 0
                ic(avg_iter, spec_idx, n_bad)
                if n_bad <= max_bad:
                    accepted.append(spec_idx)


        avg = average_spectra(spectra=curr_spectra, navg2=navg2, accepted=accepted, avg_mode=avg_mode, navgf=navgf)
        # ic(avg_iter, len(accepted), avg.shape)

    return avg, accepted


def simulate_averaging(spectra, navg2, reject_ratio, max_bad, avg_mode, n_avg_iters, navgf: int):
    # initialize with None, will be removed at the end
    results = [None]
    all_accepted = [None]

    for avg_iter in range(n_avg_iters):
        avg, accepted = filter_and_average(spectra=spectra, avg_iter=avg_iter, navg2=navg2,
                                           reject_ratio=reject_ratio, max_bad=max_bad, prev_accepted=all_accepted[-1],
                                           avg_mode=avg_mode, navgf=navgf)
        results.append(avg)
        all_accepted.append(accepted)
        # ic(avg_iter, len(accepted))

    results = results[1:]
    all_accepted = all_accepted[1:]

    return results, all_accepted




import matplotlib.pyplot as plt

def visualize_spectra(data):
    # Channel indices for x-axis
    channels = np.arange(N_CHANNELS)

    # Actually, let me reorganize this better - separate figure for each spectrum
    for spectrum_idx in range(3):
        fig, axes = plt.subplots(4, 4, figsize=(16, 12))
        fig.suptitle(f'Spectrum {spectrum_idx} - All Products', fontsize=16, fontweight='bold')

        for product_idx in range(N_PRODUCTS):
            row = product_idx // 4
            col = product_idx % 4
            ax = axes[row, col]

            # Get data for this product in this spectrum
            product_data = data[spectrum_idx, product_idx, :]

            # Plot the data
            ax.plot(channels, product_data, linewidth=0.8)
            ax.set_title(f'Product {product_idx}', fontsize=10)
            ax.grid(True, alpha=0.3)

            # Color code by amplitude range
            max_val = np.max(np.abs(product_data))
            if max_val > 1e8:  # Large amplitude
                ax.set_facecolor('#fff0f0')  # Light red background
            else:  # Small amplitude
                ax.set_facecolor('#f0f0ff')  # Light blue background

            # Format y-axis
            if max_val > 1e6:
                ax.ticklabel_format(style='scientific', axis='y', scilimits=(0,0))

            # Highlight auto products (first 4) with different border
            if product_idx < N_AUTO_PRODUCTS:
                for spine in ax.spines.values():
                    spine.set_color('red')
                    spine.set_linewidth(2)

            # Set x-axis label only for bottom row
            if row == 3:
                ax.set_xlabel('Channel', fontsize=8)

            # Set y-axis label only for leftmost column
            if col == 0:
                ax.set_ylabel('Amplitude', fontsize=8)

        plt.tight_layout()
        plt.show()

def visualize_spectra_comparison(data):
    """Alternative visualization: compare same product across first 3 spectra"""

    # Create figure showing product comparison across spectra
    fig, axes = plt.subplots(4, 4, figsize=(16, 12))
    fig.suptitle('Product Comparison Across First 3 Spectra', fontsize=16, fontweight='bold')

    channels = np.arange(N_CHANNELS)
    colors = ['blue', 'red', 'green']

    for product_idx in range(N_PRODUCTS):
        row = product_idx // 4
        col = product_idx % 4
        ax = axes[row, col]

        # Plot same product from first 3 spectra
        for spectrum_idx in range(3):
            product_data = data[spectrum_idx, product_idx, :]
            ax.plot(channels, product_data, color=colors[spectrum_idx],
                   alpha=0.7, linewidth=0.8, label=f'Spectrum {spectrum_idx}')

        ax.set_title(f'Product {product_idx}', fontsize=10)
        ax.grid(True, alpha=0.3)

        # Highlight auto products
        if product_idx < N_AUTO_PRODUCTS:
            for spine in ax.spines.values():
                spine.set_color('red')
                spine.set_linewidth(2)

        # Format axes
        max_val = np.max(np.abs(data[:3, product_idx, :]))
        if max_val > 1e6:
            ax.ticklabel_format(style='scientific', axis='y', scilimits=(0,0))

        if row == 3:
            ax.set_xlabel('Channel', fontsize=8)
        if col == 0:
            ax.set_ylabel('Amplitude', fontsize=8)

        # Add legend only to first subplot
        if product_idx == 0:
            ax.legend(fontsize=8)

    plt.tight_layout()
    plt.show()

def print_data_summary(data):

    print("Data Summary:")
    print(f"Shape: {data.shape}")
    print(f"Data type: {data.dtype}")
    print(f"Overall range: [{np.min(data)}, {np.max(data)}]")
    print(f"Overall mean: {np.mean(data):.2e}")
    print(f"Overall std: {np.std(data):.2e}")

    print("\nAuto products (first 4) - should be non-negative:")
    for i in range(N_AUTO_PRODUCTS):
        min_val = np.min(data[:, i, :])
        max_val = np.max(data[:, i, :])
        print(f"  Product {i}: range [{min_val}, {max_val}]")

    print("\nAmplitude categories:")
    for i in range(N_PRODUCTS):
        max_amplitude = np.max(np.abs(data[:, i, :]))
        category = "LARGE" if max_amplitude > 1e8 else "small"
        print(f"  Product {i}: {category} (max amplitude: {max_amplitude:.2e})")

    print("\nSpectrum consistency (std across spectra for each product/channel):")
    consistency = np.std(data, axis=0)  # std across spectra
    avg_consistency = np.mean(consistency, axis=1)  # average across channels
    print(f"  Average consistency per product: {avg_consistency}")
    print(f"  Overall consistency: {np.mean(avg_consistency):.2e}")

if __name__ == "__main__":
    # Run all visualizations
    print("Generating data and creating visualizations...")

    data = create_trig_spectra("test_spectra.txt", n_spectra=4, seed=42)
    # Print summary first
    print_data_summary(data)

    print("\nCreating individual spectrum plots...")
    visualize_spectra(data)

    print("\nCreating comparison plot...")
    visualize_spectra_comparison(data)

    print("Visualization complete!")