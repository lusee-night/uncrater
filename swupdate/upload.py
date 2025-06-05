
#!/usr/bin/env python
import sys, os
import time
import glob

sys.path.append(".")
sys.path.append("./commander/")
from DCBEmu import DCBEmulator 


# Command constants
CMD_REBOOT = 0xFF
CMD_REG_MSB = 0xA0
CMD_REG_LSB = 0xA1
CMD_REG_ADDR = 0xA2
CMD_REG_MSB_NEXT = 0xA4
CMD_BOOTLOADER = 0xB0

# Bootloader subcommands
BL_STAY = 0x00
BL_LOAD_REGION =0x01
BL_LAUNCH = 0x07
BL_GET_INFO = 0x08
BL_WRITE_FLASH = 0x0B
BL_WRITE_METADATA = 0x0C
BL_DELETE_REGION = 0x0D


# registers we need
REG_SFL_SP_1 = 0x630
REG_SFL_SP_2 = 0x631
REG_SFL_SP_3 = 0x632


# AppID of bootloader packets
AppID_BL = 0x208  # DCBEmu Hello packet


if "CORELOOP_DIR" in os.environ:
    sys.path.append(os.environ["CORELOOP_DIR"])

import argparse
import shutil
import numpy as np

class clog:
    @staticmethod
    def log(message):
        print(message)

    def logt(a,message):
        pass


def main():

    parser = argparse.ArgumentParser(description="Uploads an .lsn file to the device via DCBEmu")
    parser.add_argument("filename", nargs="?", default=None,       help="Name of the input .lsn file")
    parser.add_argument("-r", "--region",  default=1, type=int, help="Region to upload the lsn file to (default: 1, range: 1-6)")

    # ---
    args = parser.parse_args()

    input_file = args.filename
    if not input_file:
        parser.print_help()
        sys.exit(1)


    region = args.region
    if ((region<1) or (region>6)):
        print("Region must be between 0 and 6.")
        sys.exit(1)
    
    # Here you would add the logic to upload the .lsn file
    print(f"Uploading {input_file} to region {region}")

    upload (input_file, region)

def parse_lsn_file(filename):
    """
    Parses the .lsn file to extract version and data.
    The .lsn format is as follows:
      0x00: "LNSS" (4 bytes)
      0x04: SW version (4 bytes)
      0x08: program checksum (4 bytes)
      0x0C: Number of pages (2 bytes)    
      0x0E: Reserved (2 bytes)
      0x10: Data

      Data is (number of pages x 260 bytes (256+ 4 bytes for checksum))      
    """

    if not os.path.exists(filename):
        print(f"File {filename} does not exist.")
        sys.exit(1)

    with open(filename, "rb") as f:
        header = f.read(4)
        if header != b"LNSS":
            print("Invalid file format: missing LNSS header.")
            sys.exit(1)
        version_bytes = f.read(4)
        version = int.from_bytes(version_bytes, byteorder="little")
        checksum_bytes = f.read(4)
        program_checksum = int.from_bytes(checksum_bytes, byteorder="little")
        num_pages_bytes = f.read(2)
        num_pages = int.from_bytes(num_pages_bytes, byteorder="little")
        f.read(2)  # Reserved, skip
        try:
            data = [f.read(260) for _ in range(num_pages)]
        except Exception as e:
            print(f"Error reading data from file: {e}")
            sys.exit(1)
        
        # Each page: 256 bytes data + 4 bytes checksum
        parsed_pages = []
        for page in data:
            page_data = page[:256]
            checksum = int.from_bytes(page[256:260], byteorder="little")
            # Convert 256 bytes to 64 32-bit integers (little endian)
            ints = [int.from_bytes(page_data[i:i+4], byteorder="little") for i in range(0, 256, 4)]
            parsed_pages.append((ints, checksum))
        data = parsed_pages        
        return version, program_checksum, data

def write_register(D, reg, val):
    """
    Writes a value to a register using the DCBEmu emulator.
    This sense three commands to the device
    """
    D.send_command(CMD_REG_LSB, val & 0xFFFF)
    D.send_command(CMD_REG_MSB, val >> 16)
    D.send_command(CMD_REG_ADDR, reg)


def write_register_next(D, val):
    D.send_command(CMD_REG_LSB, val & 0xFFFF)
    D.send_command(CMD_REG_MSB_NEXT, val >> 16)

def wait_for_packet(appid):
    """
    Waits for a packet with the specified AppID from the DCBEmu emulator.
    This is a blocking call that will wait until the packet is received.
    """
    print(f"Waiting for packet with AppID: 0x{appid:x}")
    while True:
        files = sorted(glob.glob("tmp/cdi_output/*.bin"))
        last_file = files[-1] if files else None
        
        if last_file:
            last_id = last_file.split("_")[-1].split(".")[0]
            if int(last_id,16) == appid:
                print ("Got it:", last_file)
                return last_file
        time.sleep(0.1)  # Sleep to avoid busy waiting


def reboot(D):
    """
    Reboots the device using the DCBEmu emulator, wait for the wakeup packet and stays in the bootloader
    
    """
    print("Rebooting device...")
    D.send_command(CMD_REBOOT, 0)
    # Here you can instead of waiting to get bootloader packet, just wait for 2 seconds (but less than 5!!)
    wait_for_packet (AppID_BL) 
    # Stay in bootloader mode
    D.send_command(BL_STAY, 0)  


def delete_region(D, region):
    """
    Deletes a region in the device's flash memory.
    This function sends a command to the device to delete the specified region.
    Erasing a region is a prerequisite for writing new data to it.
    """
    print(f"Deleting region {region}...")
    write_register(D,REG_SFL_SP_1, 0xDEAD0000+region)
    D.send_command(CMD_BOOTLOADER, BL_DELETE_REGION + (region << 8))
    time.sleep(2)  # Wait for the command to be processed
    
def write_flash(D, data, program_checksum, region):
    """
    Writes the provided data to the device's flash memory in the specified region.
    This is performed by writing each page of the data into the intermediary buffer and then commanding the device to write it to flash.
    The last piece needs to wait for 100ms.
    After all pages are written, the metadata is written to the device including the checksum.
    
    """

    write_register(D,REG_SFL_SP_1, 0xFEED0000 + region)
    for page_num, (page_data, checksum) in enumerate(data):
        print(f"Writing page {page_num+1}/{len(data)} to region {region}...")                       
        write_register(D,0x640, page_data[0])
        for val in page_data[1:]:
            write_register_next(D,val)
        write_register(D,0x621, checksum)
        write_register(D,0x620, page_num)
        D.send_command(CMD_BOOTLOADER, BL_WRITE_FLASH + (region << 8))
        time.sleep(0.1)  # Wait for the command to be processed

    write_register(D,REG_SFL_SP_1, 0)
    write_register(D,REG_SFL_SP_3, 0xFEED0000 + region)
    write_register(D,REG_SFL_SP_1, len(data)*64)
    write_register(D,REG_SFL_SP_2, program_checksum)
    D.send_command(CMD_BOOTLOADER, BL_WRITE_METADATA + (region << 8))
    time.sleep(0.1)  # Wait for the command to be processed
    write_register(D,REG_SFL_SP_3, 0)

def check_checksums(D, program_checksum, region):
    """
    Checks the checksums of the uploaded data.
    There are three checksums that should all match:
     - the checksum that we got from the .lsn file
     - the checksum that was commited to the metadata (same as above, in principle)
     - the checksum just calculated from the device when we requested the info.
    If all three match, the upload was successful.
    If any of them do not match, an error is raised.
    The bootload will refuse to launch the application if metadata and calculated checksums do not match.
    """    
    D.send_command(CMD_BOOTLOADER, BL_GET_INFO)
    time.sleep(2)
    fname = wait_for_packet(AppID_BL)
    with open(fname, "rb") as f:
        data = np.frombuffer(f.read(), dtype=np.uint32)
    msg_type = data[0]
    if (msg_type!=0x02):
        print ('Error: Expected message type 0x02, got 0x{:02X}'.format(msg_type))
        sys.exit(1)
    checksum_calc = data[3*(region-1)+9]
    checksum_meta = data[3*(region-1)+10]
    if (checksum_calc == program_checksum) and (checksum_meta == program_checksum):
        print(f"Checksums match for region {region}: expected = calculated = metadata = 0x{program_checksum:X} OK")
    else:
        print(f"Checksum fail! Expected: 0x{program_checksum:X}, Calculated: 0x{checksum_calc:X}, Metadata: 0x{checksum_meta:X}")
        sys.exit(1)


def upload(filename, region):
    """
    Uploads the .lsn file to the device via DCBEmu.
    This is a placeholder function; actual implementation will depend on the DCBEmu API.
    """
    if not os.path.exists(filename):
        print(f"File {filename} does not exist.")
        sys.exit(1)

    # Here you would implement the actual upload logic
    version, program_checksum, data = parse_lsn_file(filename)
    print (f"Loaded version: 0x{version:x}")
    print (f"Number of pages: {len(data)}")

    dir = "tmp/cdi_output"
    if os.path.exists(dir):
        shutil.rmtree(dir)
    os.makedirs(dir, exist_ok=True)
    D = DCBEmulator(clog(),None,"tmp")  # Assuming DCBEmu is a class that handles the upload
    D.run()  # Start the DCBEmu emulator data collection

    # This is the meat of the upload code, fairly self-explanatory
    # --------------------------------------------------------------------------------------------
    reboot(D)
    delete_region(D, region)
    write_flash (D, data, program_checksum, region)
    check_checksums (D, program_checksum, region)
    print (f"Upload of {filename} to region {region} completed successfully.")
    # --------------------------------------------------------------------------------------------


if __name__ == "__main__":
    main()



