import argparse
from pathlib import Path
import h5py
from typing import List, Dict, Any, Optional
import uncrater as unc
from uncrater.utils import *
import ctypes
import enum
import os
import hashlib
import struct
import sys
import time
from datetime import datetime
from icecream import ic

if os.environ.get("CORELOOP_DIR") is not None:
    sys.path.append(os.environ.get("CORELOOP_DIR"))

try:
    import pycoreloop
except ImportError:
    print("Can't import pycoreloop\n")
    print("Please install the package or setup CORELOOP_DIR to point at CORELOOP repo.")
    sys.exit(1)

from pycoreloop import appId
from pycoreloop import core_loop as cl


def decode_ccsds_header(pkt) -> dict:
    """Decode CCSDS packet header."""
    formatted_data = struct.unpack_from(f">3H", pkt[:6])
    header = {}
    header['version'] = (formatted_data[0] >> 13)
    header['packet_type'] = ((formatted_data[0] >> 12) & 0x1)
    header['secheaderflag'] = ((formatted_data[0] >> 11) & 0x1)
    header['appid'] = (formatted_data[0] & 0x7FF)
    header['groupflags'] = (formatted_data[1] >> 14)
    header['sequence_cnt'] = (formatted_data[1] & 0x3FFF)
    header['packetlen'] = (formatted_data[2])
    # print(header)
    return header


def crc16_ccitt(data: bytearray) -> int:
    """Compute CRC-16-CCITT checksum.
        We use 16-bit big-endian CRC-CCITT (polynomial=0x1021, initial value=0xFFFF) """
    crc = 0xFFFF
    for b in data:
        crc ^= (b << 8)
        for _ in range(8):
            if (crc & 0x8000) != 0:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF  # Keep CRC as 16-bit value
    return crc


class PState(enum.Enum):
    FINDING_SYNC = enum.auto()
    READING_LEN = enum.auto()
    READING_DATA = enum.auto()


def L0_to_ccsds(data) -> list:
    """Convert L0 data to list of CCSDS packets (bytearray)"""
    pkts = []
    state = PState.FINDING_SYNC
    sync = 0
    garb = 0
    for v in data:
        match state:
            case PState.FINDING_SYNC:
                sync = ((sync << 8) | v) & 0xFFFF
                if v == 0xA5:
                    # 0xA5 is used for padding, ignore it
                    continue
                if sync == 0xECA0:
                    state = PState.READING_LEN
                    pkt_head = bytearray()
                    pkt_body = bytearray()
                    sync = 0
                    garb -= 1  # Compensate for earlier garb count when we see 0xEC
                    continue
                else:
                    garb += 1
                    continue

            case PState.READING_LEN:
                pkt_head.append(v)
                if len(pkt_head) == 6:
                    state = PState.READING_DATA
                    header = decode_ccsds_header(pkt_head)
                    pllen = header['packetlen']
                    sequence_cnt = header['sequence_cnt']
                    # print ('apid=', hex(header['appid']), 'seq=', sequence_cnt, 'len=', pllen)
                    continue

            case PState.READING_DATA:
                pkt_body.append(v)
                if len(pkt_body) >= pllen + 3:
                    # Check CRC
                    pktcrc = struct.unpack('>H', pkt_body[-2:])[0]
                    compcrc = crc16_ccitt(pkt_head + pkt_body[:-2])

                    if pktcrc != compcrc:
                        print(f"CRC mismatch in packet (pktcrc=0x{pktcrc:04X} compcrc=0x{compcrc:04X})")

                    pkts.append((sequence_cnt, pkt_head, pkt_body[:-2]))
                    state = PState.FINDING_SYNC

    print(f"Found {len(pkts)} packets, garb={garb}")
    return pkts


def reorder(data):
    cdata = bytearray(len(data))
    cdata[::2] = data[1::2]
    cdata[1::2] = data[::2]
    return cdata


class CollatedPacket:
    def __init__(self, start_seq: int, seq: int,
                 app_id: int, blob, single_packet: bool, unique_packet_id: Optional[int] = None):
        self.start_seq = start_seq
        self.seq = seq
        self.app_id = app_id
        self.blob = blob
        self.single_packet = single_packet
        self.unique_packet_id = unique_packet_id


def collate_packets(pkts) -> List[CollatedPacket]:
    """ Collate logical packets that have been split into multiple CCSDS packets."""
    collated = []
    pkt = bytearray()
    last_apid = None
    start_seq = None
    single_packet = True
    app_ids = dict()
    for p in pkts:
        seq, head, body = p
        pkt += reorder(body)
        header = decode_ccsds_header(head)
        cur_apid = header['appid']
        # print (f"Seq={seq} APID={hex(cur_apid)} GF={header['groupflags']} Len={len(body)} TotalLen={len(pkt)}")
        if last_apid is not None and last_apid != cur_apid:
            print(f"Warning: APID changed from {hex(last_apid)} to {hex(cur_apid)} in sequence {seq}")
        if header['groupflags'] == 3:
            # end of multi-packet
            if single_packet:
                start_seq = seq
            collated.append(CollatedPacket(start_seq=start_seq,
                                           seq=seq, app_id=cur_apid,
                                           blob=pkt, single_packet=single_packet))
            if cur_apid not in app_ids:
                app_ids[cur_apid] = 0
            else:
                app_ids[cur_apid] += 1
            pkt = bytearray()
            last_apid = None
            single_packet = True
        else:
            last_apid = cur_apid
            start_seq = seq
            single_packet = False
    return collated


def assign_uids(pkts: List[CollatedPacket]):
    # try to get uid from the packet itself
    for pkt in pkts:
        extract_unique_id(pkt)
    # for waveform packets, assign the uid of the nearest preceding packet that has it
    for i, pkt in enumerate(pkts):
        if appid_is_raw_adc(pkt.app_id) or pkt.app_id in [appId.AppID_uC_Bootloader]:
            pred = i
            while pkts[pred].unique_packet_id is None and pred > 0:
                pred -= 1
            pkt.unique_packet_id = pkts[pred].unique_packet_id


def decode_directory(path):
    begin = time.time()
    files = [path + f'/b0{i}/FFFFFFFE' for i in [5, 6, 7, 8, 9]]
    allpkts = []
    # uncomment file_to_seq lines to plot seq in the order it is read
    # file_to_seq = dict()
    for f in files:
        if not os.path.exists(f):
            print(f"WARNING: file {f} not found, skipping")
            continue
        print(f"Decoding file {f}")
        data = open(f, 'rb').read()
        pkts = L0_to_ccsds(data)
        # file_to_seq[f] = [ p[0] for p in pkts]
        collated = collate_packets(pkts)
        allpkts.extend(collated)

    # for f, seq_nums in file_to_seq.items():
    #     plt.figure()
    #     plt.plot(seq_nums, marker='o', linestyle='-', markersize=4)
    #     plt.title(os.path.basename(f))  # Just the filename without any directory
    #     plt.xlabel('Packet Index')
    #     plt.ylabel('Sequence Number')
    #     plt.grid()
    #     plt.show()  # Or plt.savefig(f"{os.path.basename(f)}_plot.png") to save the plo

    assign_uids(allpkts)
    no_uid_appids = set([hex(p.app_id) for p in allpkts if p.unique_packet_id is None])
    ic(no_uid_appids)

    all_with_uid = [p for p in allpkts if p.unique_packet_id is not None]
    ic(len(allpkts), len(all_with_uid))

    all_with_uid.sort(key=lambda x: (x.unique_packet_id, x.seq))
    elapsed = time.time() - begin
    ic(elapsed)

    return all_with_uid


def extract_unique_id(pkt: CollatedPacket):
    # if we have the corresponding header struct which was memcpy-d to TLM_BUF,
    # instantiate it and read the corresponding unique_packet_id field
    # sometimes we just directly write unique_packet_id, e.g., in spectra_out
    # in this case, uid_start is the offset from TLM_BUF at which uid is written (normally 0)
    # if neither header_class nor uid are set, the packet does not contain unique_packet_id (e.g., waveform packet)
    header_class = None
    uid_start = None
    if pkt.app_id == appId.AppID_uC_Housekeeping:
        header_class = cl.housekeeping_data_base
    elif pkt.app_id == appId.AppID_uC_Start:
        header_class = cl.startup_hello
    elif pkt.app_id == appId.AppID_uC_Heartbeat:
        # check: heartbeat does not have unique_packet_id
        header_class = cl.heartbeat
        header = header_class.from_buffer(pkt.blob[:ctypes.sizeof(header_class)])
        pkt.unique_packet_id = header.time32
        raise RuntimeError("heartbeats should be filtered out")
    elif appid_is_spectrum(pkt.app_id):
        uid_start = 0
    elif appid_is_tr_spectrum(pkt.app_id):
        uid_start = 0
    elif appid_is_zoom_spectrum(pkt.app_id):
        uid_start = 0
    elif pkt.app_id == appId.AppID_Calibrator_MetaData:
        header_class = cl.calibrator_metadata
    elif pkt.app_id in [appId.AppID_Calibrator_Data, appId.AppID_Calibrator_RawPFB]:
        uid_start = 0
    elif appid_is_cal_debug(pkt.app_id):
        uid_start = 0
    elif pkt.app_id == appId.AppID_SpectraGrimm:
        uid_start = 0
    elif appid_is_metadata(pkt.app_id):
        header_class = cl.meta_data
    elif pkt.app_id == appId.AppID_RawADC_Meta:
        header_class = cl.waveform_metadata

    if header_class is not None:
        header = header_class.from_buffer(pkt.blob[:ctypes.sizeof(header_class)])
        pkt.unique_packet_id = header.unique_packet_id

    if uid_start is not None:
        pkt.unique_packet_id = struct.unpack_from("<I", pkt.blob[uid_start:uid_start + 4])[0]


def md5_file(filepath):
    """Compute MD5 hash of the file at filepath."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def write_sessions(base_path: str, sessions: List[List[CollatedPacket]], check_existing: bool = False) -> List[str]:
    """Write each session to its own directory."""
    os.makedirs(base_path, exist_ok=True)
    session_dirs = []

    for session_idx, session_packets in enumerate(sessions):
        # Get session ID from first uC_Start packet
        session_id = None
        for pkt in session_packets:
            if pkt.app_id == appId.AppID_uC_Start:
                header = cl.startup_hello.from_buffer(pkt.blob[:ctypes.sizeof(cl.startup_hello)])
                # Use Time2Time to convert to proper timestamp
                session_id = unc.utils.Time2Time(header.time_32, header.time_16)
                break

        if session_id is None:
            session_id = 0

        # Create directory name with session ID (as integer seconds)
        dir_name = f"cdi_output_{int(session_id)}"
        session_dir = os.path.join(base_path, dir_name)
        os.makedirs(session_dir, exist_ok=True)
        session_dirs.append(session_dir)

        # Determine format string based on number of packets
        n_packets = len(session_packets)
        if n_packets >= 1000000:
            fmt_str = "{:06d}_{:04x}.bin"
        else:
            fmt_str = "{:05d}_{:04x}.bin"

        # Write packets
        for i, p in enumerate(session_packets):
            fname = os.path.join(session_dir, fmt_str.format(i, p.app_id))
            if p.app_id in [appId.AppID_SpectraHigh, appId.AppID_ZoomSpectra]:
                ic(p.unique_packet_id)
            if os.path.exists(fname) and check_existing:
                existing_hash = md5_file(fname)
                new_hash = hashlib.md5(p.blob).hexdigest()
                if existing_hash != new_hash:
                    raise ValueError(f"File {fname} exists but content is different.")
                else:
                    continue
            with open(fname, 'wb') as f:
                f.write(p.blob)

    return session_dirs


def split_into_sessions(pkts: List[CollatedPacket]) -> List[List[CollatedPacket]]:
    """
    Split packets into sessions. A sequence of AppID_uC_Start packets
    (1, 2 or more in a row) signals the beginning of a new session.
    Sessions are cut when new AppID_uC_Start packets are encountered.
    """
    sessions = []
    current_session = []

    for i, pkt in enumerate(pkts):
        if pkt.app_id == appId.AppID_uC_Start:
            # Check if this is part of a sequence of uC_Start packets
            # or if it's a new start after other packets
            if current_session and current_session[-1].app_id != appId.AppID_uC_Start:
                # We have a non-empty session and the last packet wasn't uC_Start
                # This means we're starting a new session
                sessions.append(current_session)
                current_session = [pkt]
            else:
                # Either starting fresh or continuing a sequence of uC_Start packets
                current_session.append(pkt)
        else:
            # Regular packet, just add to current session
            current_session.append(pkt)

    # last session
    if current_session:
        sessions.append(current_session)

    return sessions


class HDF5Writer:
    """Class to handle HDF5 writing with separate methods for each data type."""

    def __init__(self, output_file: str, cdi_dir: str):
        self.output_file = output_file
        self.cdi_dir = cdi_dir
        self.coll = None

    def write(self):
        """Main method to write HDF5 file."""
        # Load uncrater Collection
        self.coll = unc.Collection(self.cdi_dir)

        self._assign_zoom_timestamps()

        with h5py.File(self.output_file, 'w') as f:
            # Store session-level info
            f.attrs['cdi_directory'] = self.cdi_dir

            # Track metadata changes
            metadata_groups = self._group_by_metadata()

            # Write each metadata group to HDF5
            for group_idx, group in enumerate(metadata_groups):
                group_name = f'group_{group_idx:03d}'
                h5_group = f.create_group(group_name)

                # Store metadata as attributes
                for key, value in group['metadata_dict'].items():
                    h5_group.attrs[key] = value

                # Write different data types
                self._write_waveforms(h5_group, group['waveform'])
                self._write_spectra(h5_group, group['spectra'])
                self._write_tr_spectra(h5_group, group['tr_spectra'])
                self._write_housekeeping(h5_group, group['housekeeping'])
                self._write_zoom_spectra(h5_group, group['zoom_spectra'])
                self._write_calibrator_data(h5_group, group['calibrator_data'])

            # Add summary information
            f.attrs['n_groups'] = len(metadata_groups)

    def _group_by_metadata(self) -> List[Dict]:
        """Group data by metadata configuration."""
        metadata_groups = []
        current_metadata_dict = None

        # Group data by metadata configuration
        for sp_dict in self.coll.spectra:
            meta_pkt = sp_dict['meta']
            meta_dict = metadata_to_dict(meta_pkt)

            if current_metadata_dict != meta_dict:
                # New metadata configuration
                current_metadata_dict = meta_dict
                metadata_groups.append({
                    'metadata': meta_pkt,
                    'metadata_dict': meta_dict,
                    'spectra': [],
                    'tr_spectra': [],
                    'housekeeping': [],
                    'waveform': [],
                    'zoom_spectra': [],
                    'calibrator_data': [],
                    'calibrator_debug': []
                })

            # Add this spectrum set to current group
            metadata_groups[-1]['spectra'].append(sp_dict)

        # Match TR spectra to metadata groups
        for trs_dict in self.coll.tr_spectra:
            meta_pkt = trs_dict['meta']
            meta_dict = metadata_to_dict(meta_pkt)

            # Find matching metadata group
            for group in metadata_groups:
                if group['metadata_dict'] == meta_dict:
                    group['tr_spectra'].append(trs_dict)
                    break
            else:
                print(f"Warning: TR spectrum with unmatched metadata")

        # Assign other packets to groups
        if metadata_groups:
            last_group = metadata_groups[-1]
            last_group['housekeeping'].extend(self.coll.housekeeping_packets)
            last_group['waveform'].extend(self.coll.waveform_packets)
            last_group['zoom_spectra'].extend(self.coll.zoom_spectra_packets)
            if hasattr(self.coll, 'calib_data') and len(self.coll.calib_data) > 0:
                last_group['calibrator_data'].extend(self.coll.calib_data)
            if hasattr(self.coll, 'calib_debug') and len(self.coll.calib_debug) > 0:
                last_group['calibrator_debug'].extend(self.coll.calib_debug)

        return metadata_groups

    def _write_waveforms(self, h5_group, waveform_packets):
        """Write waveform packets to HDF5."""
        if not waveform_packets:
            return

        wf_group = h5_group.create_group('waveform')

        # Group waveforms by channel
        waveforms_by_channel = {}
        for wf_pkt in waveform_packets:
            wf_pkt._read()
            if wf_pkt.ch not in waveforms_by_channel:
                waveforms_by_channel[wf_pkt.ch] = []
            waveforms_by_channel[wf_pkt.ch].append(wf_pkt)

        # Write each channel's waveforms
        for ch, wf_list in waveforms_by_channel.items():
            ch_group = wf_group.create_group(f'channel_{ch}')

            n_waveforms = len(wf_list)
            waveform_array = np.zeros((n_waveforms, 16384), dtype=np.int16)
            timestamps = []

            for i, wf_pkt in enumerate(wf_list):
                waveform_array[i] = wf_pkt.waveform
                timestamps.append(wf_pkt.timestamp)

            ch_group.create_dataset('waveforms', data=waveform_array, compression='gzip')
            ch_group.create_dataset('timestamps', data=timestamps)
            ch_group.attrs['count'] = n_waveforms
            ch_group.attrs['channel'] = ch

        wf_group.attrs['total_count'] = len(waveform_packets)
        wf_group.attrs['channels'] = list(waveforms_by_channel.keys())

    def _write_spectra(self, h5_group, spectra_dicts):
        """Write spectra to HDF5."""
        if not spectra_dicts:
            return

        n_time = len(spectra_dicts)

        spectra_array = np.full((n_time, NPRODUCTS, NCHANNELS), np.nan, dtype=np.float32)
        spectra_uids = []

        for t_idx, sp_dict in enumerate(spectra_dicts):
            spectra_uids.append(sp_dict['meta'].unique_packet_id)

            for prod_idx in range(NPRODUCTS):
                if prod_idx in sp_dict:
                    spectrum = sp_dict[prod_idx].data
                    spectra_array[t_idx, prod_idx, :len(spectrum)] = spectrum

        h5_group.create_dataset('spectra/data', data=spectra_array, compression='gzip')
        h5_group.create_dataset('spectra/unique_ids', data=spectra_uids)
        h5_group.attrs['spectra_count'] = n_time

    def _write_tr_spectra(self, h5_group, tr_spectra_dicts):
        """Write time-resolved spectra to HDF5."""
        if not tr_spectra_dicts:
            return

        n_time = len(tr_spectra_dicts)

        # Get dimensions from first packet
        first_trs = tr_spectra_dicts[0]
        meta = first_trs['meta']

        tr_length = meta.base.tr_stop - meta.base.tr_start
        if meta.base.tr_avg_shift > 0:
            tr_length = tr_length // (1 << meta.base.tr_avg_shift)

        Navg2 = 1 << meta.base.Navg2_shift

        tr_array = np.full((n_time, NPRODUCTS, Navg2, tr_length), np.nan, dtype=np.float32)
        tr_uids = []

        for t_idx, trs_dict in enumerate(tr_spectra_dicts):
            tr_uids.append(trs_dict['meta'].unique_packet_id)

            for prod_idx in range(NPRODUCTS):
                if prod_idx in trs_dict:
                    tr_spectrum = trs_dict[prod_idx].data
                    if tr_spectrum.ndim == 2:
                        tr_array[t_idx, prod_idx, :tr_spectrum.shape[0], :tr_spectrum.shape[1]] = tr_spectrum
                    else:
                        print(f"Warning: TR spectrum has unexpected shape {tr_spectrum.shape}")
                        flat_len = min(len(tr_spectrum), Navg2 * tr_length)
                        tr_array[t_idx, prod_idx].flat[:flat_len] = tr_spectrum.flat[:flat_len]

        h5_group.create_dataset('tr_spectra/data', data=tr_array, compression='gzip')
        h5_group.create_dataset('tr_spectra/unique_ids', data=tr_uids)
        h5_group.attrs['tr_spectra_count'] = n_time
        h5_group.attrs['tr_spectra_Navg2'] = Navg2
        h5_group.attrs['tr_spectra_tr_length'] = tr_length

    def _write_housekeeping(self, h5_group, housekeeping_packets):
        """Write housekeeping packets to HDF5."""
        if not housekeeping_packets:
            return

        hk_group = h5_group.create_group('housekeeping')

        for i, hk_pkt in enumerate(housekeeping_packets):
            hk_pkt._read()

            pkt_group = hk_group.create_group(f'packet_{i}')
            pkt_group.attrs['hk_type'] = hk_pkt.hk_type
            pkt_group.attrs['version'] = hk_pkt.version
            pkt_group.attrs['unique_packet_id'] = hk_pkt.unique_packet_id
            pkt_group.attrs['errors'] = hk_pkt.errors

            if hk_pkt.hk_type == 0:
                if hasattr(hk_pkt, 'time'):
                    pkt_group.attrs['time'] = hk_pkt.time
            elif hk_pkt.hk_type == 1:
                if hasattr(hk_pkt, 'min'):
                    pkt_group.attrs['adc_min'] = hk_pkt.min
                if hasattr(hk_pkt, 'max'):
                    pkt_group.attrs['adc_max'] = hk_pkt.max
                if hasattr(hk_pkt, 'mean'):
                    pkt_group.attrs['adc_mean'] = hk_pkt.mean
                if hasattr(hk_pkt, 'rms'):
                    pkt_group.attrs['adc_rms'] = hk_pkt.rms
                if hasattr(hk_pkt, 'actual_gain'):
                    pkt_group.attrs['actual_gain'] = ''.join(hk_pkt.actual_gain)
            elif hk_pkt.hk_type == 2:
                if hasattr(hk_pkt, 'time'):
                    pkt_group.attrs['time'] = hk_pkt.time
                if hasattr(hk_pkt, 'ok'):
                    pkt_group.attrs['ok'] = hk_pkt.ok
                if hasattr(hk_pkt, 'telemetry'):
                    for k, v in hk_pkt.telemetry.items():
                        pkt_group.attrs[f'telemetry_{k}'] = v
            elif hk_pkt.hk_type == 3:
                if hasattr(hk_pkt, 'checksum'):
                    pkt_group.attrs['checksum'] = hk_pkt.checksum
                if hasattr(hk_pkt, 'weight_ndx'):
                    pkt_group.attrs['weight_ndx'] = hk_pkt.weight_ndx

        hk_group.attrs['count'] = len(housekeeping_packets)

    def _write_zoom_spectra(self, h5_group, zoom_packets):
        """Write zoom spectra as concatenated arrays."""
        if not zoom_packets:
            return

        zoom_group = h5_group.create_group('calibrator/zoom_spectra')

        n_packets = len(zoom_packets)
        fft_size = 64

        # Initialize arrays
        ch1_autocorr_all = np.zeros((n_packets, fft_size), dtype=np.float32)
        ch2_autocorr_all = np.zeros((n_packets, fft_size), dtype=np.float32)
        ch1_2_corr_real_all = np.zeros((n_packets, fft_size), dtype=np.float32)
        ch1_2_corr_imag_all = np.zeros((n_packets, fft_size), dtype=np.float32)
        unique_ids = []
        pfb_indices = []
        timestamps = []

        for i, zoom_pkt in enumerate(zoom_packets):
            zoom_pkt._read()

            ch1_autocorr_all[i] = zoom_pkt.ch1_autocorr
            ch2_autocorr_all[i] = zoom_pkt.ch2_autocorr
            ch1_2_corr_real_all[i] = zoom_pkt.ch1_2_corr_real
            ch1_2_corr_imag_all[i] = zoom_pkt.ch1_2_corr_imag

            uid = zoom_pkt.unique_packet_id[0] if isinstance(zoom_pkt.unique_packet_id, tuple) else zoom_pkt.unique_packet_id
            pfb_idx = zoom_pkt.pfb_index[0] if isinstance(zoom_pkt.pfb_index, tuple) else zoom_pkt.pfb_index

            unique_ids.append(uid)
            pfb_indices.append(pfb_idx)

            # Use the assigned timestamp
            timestamps.append(zoom_pkt.zoom_timestamp if hasattr(zoom_pkt, 'zoom_timestamp') else 0.0)

        # Store as datasets
        zoom_group.create_dataset('ch1_autocorr', data=ch1_autocorr_all, compression='gzip')
        zoom_group.create_dataset('ch2_autocorr', data=ch2_autocorr_all, compression='gzip')
        zoom_group.create_dataset('ch1_2_corr_real', data=ch1_2_corr_real_all, compression='gzip')
        zoom_group.create_dataset('ch1_2_corr_imag', data=ch1_2_corr_imag_all, compression='gzip')
        zoom_group.create_dataset('unique_ids', data=unique_ids)
        zoom_group.create_dataset('pfb_indices', data=pfb_indices)
        zoom_group.create_dataset('timestamps', data=timestamps)
        zoom_group.attrs['count'] = n_packets

    def _write_calibrator_data(self, h5_group, calibrator_data):
        """Write calibrator data to HDF5."""
        if not calibrator_data:
            return

        cal_data_group = h5_group.create_group('calibrator/data')

        for i, cal_data in enumerate(calibrator_data):
            for ch_idx, ch_data in enumerate(cal_data):
                if ch_data is not None:
                    cal_data_group.create_dataset(f'packet_{i}_ch_{ch_idx}',
                                                 data=ch_data, compression='gzip')
        cal_data_group.attrs['count'] = len(calibrator_data)


    def _assign_zoom_timestamps(self):
        """Assign timestamps to zoom spectrum packets efficiently."""
        if not self.coll.zoom_spectra_packets:
            return

        # Start from the beginning of spectra list
        spectra_idx = 0

        for zoom_pkt in self.coll.zoom_spectra_packets:
            zoom_pkt._read()

            # Get the packet index from the zoom packet
            zoom_packet_index = zoom_pkt.packet_index

            # Find the metadata packet that comes before this zoom packet
            # by looking through spectra dictionaries
            meta_time = None

            # Move forward through spectra until we pass the zoom packet index
            while spectra_idx < len(self.coll.spectra):
                spectra_dict = self.coll.spectra[spectra_idx]
                meta_pkt = spectra_dict['meta']

                # Check if metadata packet index is past zoom packet
                if meta_pkt.packet_index > zoom_packet_index:
                    # Use the previous metadata if available
                    if spectra_idx > 0:
                        prev_meta = self.coll.spectra[spectra_idx - 1]['meta']
                        meta_time = prev_meta.time
                    break

                # This metadata is still before or at zoom packet, keep it as candidate
                meta_time = meta_pkt.time
                spectra_idx += 1

            # Assign the timestamp to zoom packet
            zoom_pkt.zoom_timestamp = meta_time if meta_time is not None else 0.0

def save_to_hdf5(cdi_dir: str, output_file: str):
    """
    Save a session of packets to HDF5 file.

    Args:
        cdi_dir: Directory containing CDI output files
        output_file: Path to output HDF5 file
    """
    writer = HDF5Writer(output_file, cdi_dir)
    writer.write()


def metadata_to_dict(meta: unc.Packet_Metadata) -> Dict[str, Any]:
    """Convert metadata packet to dictionary for comparison and storage."""
    meta._read()  # Ensure packet is read
    return {
        'Navgf': meta.base.Navgf,
        'Navg1_shift': meta.base.Navg1_shift,
        'Navg2_shift': meta.base.Navg2_shift,
        'notch': meta.base.notch,
        'format': meta.base.format,
        'corr_products_mask': meta.base.corr_products_mask,
        'tr_start': meta.base.tr_start,
        'tr_stop': meta.base.tr_stop,
        'tr_avg_shift': meta.base.tr_avg_shift,
        'grimm_enable': meta.base.grimm_enable,
        'averaging_mode': meta.base.averaging_mode,
        'reject_ratio': meta.base.reject_ratio,
        'reject_maxbad': meta.base.reject_maxbad,
        'bitslice_keep_bits': meta.base.bitslice_keep_bits,
        'weight': meta.base.weight,
        'weight_current': meta.base.weight_current,
        # Include gain settings for all 4 inputs
        'gain': [meta.base.gain[i] for i in range(4)],
        'actual_gain': [meta.base.actual_gain[i] for i in range(4)],
        # Include bitslice settings for all 16 spectra
        'bitslice': [meta.base.bitslice[i] for i in range(NPRODUCTS)],
        'actual_bitslice': [meta.base.actual_bitslice[i] for i in range(NPRODUCTS)],
    }


def app_id_category(curr_app_id):
    if appid_is_spectrum(curr_app_id):
        curr_app_id = appId.AppID_SpectraHigh
    if appid_is_tr_spectrum(curr_app_id):
        curr_app_id = appId.AppID_SpectraTRHigh
    if appid_is_raw_adc(curr_app_id):
        curr_app_id = appId.AppID_RawADC
    if appid_is_zoom_spectrum(curr_app_id):
        curr_app_id = appId.AppID_ZoomSpectra
    if appid_is_grimm_spectrum(curr_app_id):
        curr_app_id = appId.AppID_SpectraGrimm
    for app_str in dir(appId):
        if "AppID" not in app_str:
            continue
        if getattr(appId, app_str) == curr_app_id:
            return app_str
    raise RuntimeError(f"AppID {curr_app_id} not found in appId module")


def print_packet_categories(pkts):
    # print accumulated statistics: how many packets of the same category we have in a row
    prev_app_id = None
    cat_count = 0
    for p in pkts:
        curr_app_id = app_id_category(p.app_id)
        if prev_app_id is None or curr_app_id != prev_app_id:
            if prev_app_id is not None:
                print(f"{prev_app_id.ljust(25, " ")}: {cat_count} packets")
            cat_count = 1  # Start with 1 for the current packet
            prev_app_id = curr_app_id
        else:
            cat_count += 1
    # the last group
    if prev_app_id is not None:
        print(f"{prev_app_id.ljust(25, " ")}:\t {cat_count} packets")


if __name__ == "__main__":
    verbose = True
    parser = argparse.ArgumentParser(description='Save sessions to HDF5')
    parser.add_argument('input_dir', type=str, help='Input directory containing telemetry data')
    parser.add_argument('output_dir', type=str, nargs='?', default='.',
                        help='Output directory for session files (default: current directory)')

    args = parser.parse_args()

    # Ensure output directory exists
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Decode packets from input directory
    pkts = decode_directory(args.input_dir)
    if verbose:
        print(len(pkts), " collated packets found")

    if verbose:
        print_packet_categories(pkts)

    # Split into sessions
    sessions = split_into_sessions(pkts)
    if verbose:
        print(f"Found {len(sessions)} sessions")

    # Write sessions to directories
    base_output = str(output_path / "sessions")
    session_dirs = write_sessions(base_output, sessions)

    # Save each session to HDF5
    for i, session_dir in enumerate(session_dirs):
        # Get session ID from directory name
        session_id = session_dir.split('_')[-1]

        # Create output filename with session number and ID
        # Convert Unix timestamp to readable date if possible
        try:
            timestamp = int(session_id)
            date_str = datetime.fromtimestamp(timestamp).strftime('%Y%m%d_%H%M%S')
            output_file = str(output_path / f"session_{date_str}.h5")
        except:
            output_file = str(output_path / f"session_{i:03d}_{session_id}.h5")

        if verbose:
            print(f"Processing session {i}: {session_dir} -> {output_file}")
        save_to_hdf5(session_dir, output_file)