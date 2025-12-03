## `reconstruct_packets.py`
### Requirements
- `h5py` package must be installed in the venv.
- `CORELOOP_DIR` environment variable must point to the root of `coreloop`
repo
- Code assumes that it is located inside `reconstruct` subdirectory and it appends
the parent directory to `sys.path` to be able to import `uncrater`
 
### Usage
`python reconstruct_packets.py input_dir [output_dir]`

`input_dir` must contain `b00`..`b08` directories (e.g., `20251105_112220/fs/FLASH_TLMFS`).
Inside `output_dir`, the code will
1. Create `sessions` directory. For each session found in `input_dir`, its output will be written
to the `sessions\cdi_output_{session_id}` subdirectory. Files are never overwritten.
If (inside the code) you change `check_existing` to `True`, it will compare the MD5 hash
of what it's going to write and the existing file on disk and report an error if there is
inconsistency. TODO: maybe, compare sizes and overwrite, if new file is bigger (we got more data)?
2. For each session, create an HDF5 file `session_{session_start_data}.h5`. Use `h5ls -r` to see the structure.

### Details

- CCSDS packets are collated by function `collate_packets`, it returns a list of object of helper class `CollatedPacket` (could be named tuple).
- UIDs are assigned to collated packets by `assign_uids`: if we can extract it from the packet itself, `extract_unique_id` will do it, otherwise we walk back until we find a 
  packet with UID set and take it.
- Packets are sorted by UID and split into sessions.
- A new session starts when we see one or more AppID_uC_Start packets in a row.
Splitting the list of collated binary packets into sessions is done `split_into_sessions` function.
- Every session is written to its own cdi_output directory. This directory will then be used by HDF5 writer to read its contents using uncrater code.
- Since zoom spectra packets do not have timestamp, it is assigned by looking at the closest Metadata packet preceding the packet (`HDF5Writer._assign_zoom_timestamps`).

## Sanity check visualization

`plot_*` scripts will visualize spectra, time-resolved spectra and zoom spectra from the HDF5 file.

Example usage: `python plot_tr_spectra.py output_dir/session_20251105_120504.h5`.
They will also print some statistics (missing packets count as NaNs).
The scripts are interactive, press q to quit them, when done.