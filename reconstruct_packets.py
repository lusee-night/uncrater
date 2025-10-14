import os
import time

import pylab as p
from icecream import ic
import sys
import struct
import enum
import ctypes
from typing import List, Optional

# from uncrater.utils import appid_is_metadata, appid_is_spectrum

if os.environ.get("CORELOOP_DIR") is not None:
    sys.path.append(os.environ.get("CORELOOP_DIR"))

# now try to import pycoreloop
try:
    import pycoreloop
except ImportError:
    print("Can't import pycoreloop\n")
    print("Please install the package or setup CORELOOP_DIR to point at CORELOOP repo.")
    sys.exit(1)

from pycoreloop import appId
from pycoreloop import core_loop as cl

def appid_is_spectrum(appid: int) -> bool:
    return ((appid>=appId.AppID_SpectraHigh) and (appid<appId.AppID_SpectraLow+16))

def appid_is_tr_spectrum(appid):
    if appId.AppID_SpectraTRHigh <= appid < appId.AppID_SpectraTRHigh + 16:
        return True

    if appId.AppID_SpectraTRMed <= appid < appId.AppID_SpectraTRMed + 16:
        return True

    if appId.AppID_SpectraTRLow <= appid < appId.AppID_SpectraTRLow + 16:
        return True

    return False


def appid_is_zoom_spectrum(appid):
    if appId.AppID_ZoomSpectra <= appid < appId.AppID_ZoomSpectra + 16:
        return True
    return False


def appid_is_metadata(appid):
    return (appid==appId.AppID_MetaData)

# we have 4 waveform packets
def appid_is_raw_adc(appid):
    return appId.AppID_RawADC <= appid < appId.AppID_RawADC + 4


# we have 8 different calibrator debug modes,
# according to lusee_appids
def appid_is_cal_debug(appid: int) -> bool:
    return appId.AppID_Calibrator_Debug <= appid < appId.AppID_Calibrator_Debug + 8


def decode_ccsds_header(pkt) -> dict:
    """Decode CCSDS packet header."""
    formatted_data = struct.unpack_from(f">3H",pkt[:6])
    header = {}
    header['version'] = (formatted_data[0] >> 13)
    header['packet_type'] = ((formatted_data[0] >> 12) & 0x1)
    header['secheaderflag'] = ((formatted_data[0] >> 11) & 0x1)
    header['appid'] = (formatted_data[0] & 0x7FF)
    header['groupflags'] = (formatted_data[1] >> 14)
    header['sequence_cnt'] = (formatted_data[1] & 0x3FFF)
    header['packetlen'] = (formatted_data[2])
    #print(header)
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
                    garb-=1 # Compensate for earlier garb count when we see 0xEC
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
                    #print ('apid=', hex(header['appid']), 'seq=', sequence_cnt, 'len=', pllen)
                    continue

            case PState.READING_DATA:
                pkt_body.append(v)
                if len(pkt_body) >= pllen + 3:
                    # Check CRC
                    pktcrc = struct.unpack('>H', pkt_body[-2:])[0]
                    compcrc = crc16_ccitt(pkt_head+pkt_body[:-2])

                    if pktcrc != compcrc:
                        print(f"CRC mismatch in packet (pktcrc=0x{pktcrc:04X} compcrc=0x{compcrc:04X})")

                    pkts.append((sequence_cnt, pkt_head, pkt_body[:-2]))
                    state = PState.FINDING_SYNC

    print(f"Found {len(pkts)} packets, garb={garb}")
    return pkts


def reorder(data):
    cdata = bytearray(len(data))
    cdata[::2]= data[1::2]
    cdata[1::2] = data[::2]
    return cdata


def collate_packets(pkts) -> list:
    """ Collate logical packets that have been split into multiple CCSDS packets."""
    collated = []
    pkt = bytearray()
    last_apid = None
    start_seq = None
    single_packet = True
    for p in pkts:
        seq, head, body = p

        pkt += reorder(body)
        header = decode_ccsds_header(head)
        cur_apid = header['appid']
        #print (f"Seq={seq} APID={hex(cur_apid)} GF={header['groupflags']} Len={len(body)} TotalLen={len(pkt)}")

        #if (seq>100):
        #    stop()

        if last_apid is not None and last_apid != cur_apid:
            print(f"Warning: APID changed from {hex(last_apid)} to {hex(cur_apid)} in sequence {seq}")
        if header['groupflags']==3:
            # end of multi-packet
            if single_packet:
                start_seq = seq
            collated.append((start_seq, seq, cur_apid, pkt))
            pkt = bytearray()
            last_apid = None
            single_packet = True
        else:
            last_apid = cur_apid
            start_seq = seq
            single_packet = False

    return collated


class CollatedPacket:
    def __init__(self, start_seq: int, seq: int,
                 app_id: int, blob, single_packet: bool, unique_packet_id: Optional[int]=None):
        self.start_seq = start_seq
        self.seq = seq
        self.app_id = app_id
        self.blob = blob
        self.single_packet = single_packet
        self.unique_packet_id = unique_packet_id




def collate_packets_1(pkts) -> List[CollatedPacket]:
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
        #print (f"Seq={seq} APID={hex(cur_apid)} GF={header['groupflags']} Len={len(body)} TotalLen={len(pkt)}")

        if last_apid is not None and last_apid != cur_apid:
            print(f"Warning: APID changed from {hex(last_apid)} to {hex(cur_apid)} in sequence {seq}")
        if header['groupflags']==3:
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

    for app_id in app_ids:
        ic(hex(app_id), app_ids[app_id])

    return collated


def decode_directory(path):
    files = [path+f'/b0{i}/FFFFFFFE' for i in [5,6,7,8,9]]
    allpkts = []
    for f in files:
        ft = os.path.basename(f)
        if len(ft) != 8:
            continue
        print(f"Decoding file {f}")
        data = open(f,'rb').read()
        pkts = L0_to_ccsds(data)
        collated = collate_packets(pkts)
        last_seq = None
        bin = -1
        cpkts = []
        for pkt in collated:
            sseq, eseq,  appid, body = pkt
            if last_seq is None or last_seq>eseq:
               bin+= 1
               cpkts.append([])
            cpkts[bin].append(pkt)
            last_seq = eseq
        print(f"Found {len(pkts)} packets in file {f}, collated to {len(collated)} logical packets fitting into {len(cpkts)} chunks.")
        allpkts.append(cpkts)

    return allpkts


def assign_uids(pkts: List[CollatedPacket]):
    # try to get uid from the packet itself
    for pkt in pkts:
        extract_unique_id(pkt)
    # for waveform packets, assign the uid of the nearest preceding packet that has it
    for i, pkt in enumerate(pkts):
        if appid_is_raw_adc(pkt.app_id) or pkt.app_id in [appId.AppID_ZoomSpectra, appId.AppID_uC_Bootloader]:
            pred = i
            while pkts[pred].unique_packet_id is None and pred > 0:
                pred -= 1
            pkt.unique_packet_id = pkts[pred].unique_packet_id


def decode_directory_1(path):
    files = [path+f'/b0{i}/FFFFFFFE' for i in [5,6,7,8,9]]
    allpkts = []
    for f in files:
        ft = os.path.basename(f)
        if len(ft) != 8:
            continue
        print(f"Decoding file {f}")
        data = open(f,'rb').read()
        pkts = L0_to_ccsds(data)
        collated = collate_packets_1(pkts)
        allpkts.extend(collated)
        # cpkts = []
        # for pkt in collated:
        #     sseq, eseq,  appid, body = pkt
        #     if last_seq is None or last_seq>eseq:
        #        bin+= 1
        #        cpkts.append([])
        #     cpkts[bin].append(pkt)
        #     last_seq = eseq
        # print(f"Found {len(pkts)} packets in file {f}, collated to {len(collated)} logical packets fitting into {len(cpkts)} chunks.")
        # allpkts.append(cpkts)

    assign_uids(allpkts)
    no_uid_appids = set([hex(p.app_id) for p in allpkts if p.unique_packet_id is  None])
    ic(no_uid_appids)

    all_with_uid = [ p for p in allpkts if p.unique_packet_id is not None]
    ic(len(allpkts), len(all_with_uid))

    begin = time.time()
    all_with_uid.sort(key=lambda x: (x.unique_packet_id, x.seq))
    elapsed = time.time() - begin
    ic(elapsed)


    return allpkts



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
        header_class = None
    elif appid_is_spectrum(pkt.app_id):
        uid_start = 0
    elif appid_is_tr_spectrum(pkt.app_id):
        uid_start = 0
    elif appid_is_zoom_spectrum(pkt.app_id):
        # TODO: add unique_packet_id to calibrator_zoom.c
        pass
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
    elif pkt.app_id == appId.AppID_uC_Bootloader:
        # sent by the firmware? no code in coreloop
        pass

    if header_class is not None:
        header = header_class.from_buffer(pkt.blob[:ctypes.sizeof(header_class)])
        pkt.unique_packet_id = header.unique_packet_id

    if uid_start is not None:
        pkt.unique_packet_id = struct.unpack_from("<I", pkt.blob[uid_start:uid_start+4])[0]



def write_session (path, pkts):
    os.makedirs(path, exist_ok=True)
    cdi_out = path+'/cdi_output'
    os.makedirs(cdi_out, exist_ok=True)
    for i,p in enumerate(pkts):
        seq, seqend,apid, body = p
        fname = f"{cdi_out}/{i:05d}_{apid:04x}.bin"
        with open(fname,'wb') as f:
            f.write(body)

pkts = decode_directory_1('data2')
print (len(pkts), 'collated packets found')