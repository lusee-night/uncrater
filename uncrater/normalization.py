"""Explicit relative power normalization for decoded zoom spectra."""

import numpy as np

from .constants import BITSLICE_REFERENCE, ZOOM_BINS, ZOOM_COMPONENTS


def normalize_zoom(data, *, convention="sdu"):
    """Return a float64 copy of native zoom power in the named convention.

    Input has shape (..., 4, 64), ordered AA, BB, ABR, ABI. ``sdu`` divides
    by 2**37 to match bit-31 normal SDU; ``pfb`` divides by 64 for raw PFB
    power. No bitslice, averaging, notch, or absolute gain factor applies.
    The input is never modified. Call only on native, unnormalized values.
    """
    if convention not in ("sdu", "pfb"):
        raise ValueError("zoom convention must be 'sdu' or 'pfb'")
    values = np.asarray(data)
    if values.ndim < 2 or values.shape[-2:] != (ZOOM_COMPONENTS, ZOOM_BINS):
        raise ValueError(
            f"zoom data must have shape (..., {ZOOM_COMPONENTS}, {ZOOM_BINS})"
        )
    if values.dtype.kind not in "iuf":
        raise TypeError("zoom components must be real numeric values")
    divisor = ZOOM_BINS * (2**BITSLICE_REFERENCE if convention == "sdu" else 1)
    return values.astype(np.float64) / divisor
