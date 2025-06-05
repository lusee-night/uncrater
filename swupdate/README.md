# LuSEE-Night Spectrometer SW Update

This document defines the procedure for uploading the spectometer flight software into spectrometer.
It includes a reference implementation that successfully uploads the spectrometer software using DCBEmulator. Thsi functionality should be implemented into DCB itself.

There are two pieces to this process. The first piece is converting the output binary in the [Intel hex format](https://en.wikipedia.org/wiki/Intel_HEX) into a custom `.lsn` files that are a compressed binary representation of the blob with precomputed checksum. The format is described below. The .lsn blob for the current software is 83kB long. It can be gzipped into 52k, but not worth the trouble. 


## The process of uploading the flight software

The flight sofware resides in one of the 6 regions in the spectrometer. The bootloader can launch any of the 6 regions and will, by default, launch just the first one with matching checksum.

The process of uploading consists of the following steps:

 * Reboot the spectrometer and make it stay in the bootloader
 * Erase data in the region of interest
 * Write new data in the region of interest:
    - loop over 64 32-bit words pages and write binary data together with their page checksums, followed by write request
    - write metadata with the final checksum
 * Optionally request bootloader to return its calculated and metatadat checksums to confirm a successful upload


The implementation requires, at the minimum, the following interfaces:
 * send command taking 3 bytes that are delivered to spectrometer as a command
 * wait states (typically 100ms after each page commit, but 2s for erase command)

To confirm successful upload in-situ, the interface also requires the binary access to the last bootloader packet (0x208).


## The LSN format

The `.lsn` format contains a 16 byte header followed by the payload. Words in header are little endian.

Header has the following contents:

| Offset  | Field             | Size      | Description                |
|---------|-------------------|-----------|----------------------------|
| 0x00    | "LNSS" string     | 4 bytes   | Magic header               |
| 0x04    | SW version        | 4 bytes   | Flight SW version          |
| 0x08    | Program checksum  | 4 bytes   | Checksum of the program    |
| 0x0C    | Number of pages   | 2 bytes   | Number of pages            | 
| 0x0E    | Reserved          | 2 bytes   | Reseved                    |


The payload starts at 0x10 and contains (number of pages)x(260 bytes). Each 260 page is 256 bytes page data + 4 byte checksum.

The converter from `.hex` to `.lsn` is provided in `hex2lsn.py` script


## Uploading script

The uploading script is provided in the `upload.py`. It uses the commander interface (which is somewhat hackilishy accessed here). It can be used to implement DCB version of the uploading. The meat of contained in the following functions:

 * `reboot` - reboots the spectrometer and makes it stay in the bootloader
 * `delete_region` - deletes a region
 * `write_flash` - actual upload, including metadata upload
 * `check_checksums` - asks spectomter to return the checkum information and checks against expectations to confirm upload succeeded

 There all, under the hood work with `send_command` function and the utility functions `write_register` and `write_register_next`, which in turn issue a 3 or 2 individual commands.
 