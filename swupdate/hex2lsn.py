
#!/usr/bin/env python
import sys, os


sys.path.append(".")
sys.path.append("./scripter/")
if "CORELOOP_DIR" in os.environ:
    sys.path.append(os.environ["CORELOOP_DIR"])

import argparse

def main():

    parser = argparse.ArgumentParser(description="Converts .hex to .lsn files for SW update")
    parser.add_argument("input", nargs="?", default=None,       help="Name of the input .hex file")
    parser.add_argument("output", nargs="?", default=None,      help="Name of the output .lsn file")
    parser.add_argument("-w", "--sw-version",  default="auto",  help="SW version to burn into the lsn file, or 'auto' to use the version from the hex filename")
    
    # ---
    args = parser.parse_args()

    input_file = args.input
    output_file = args.output
    if args.sw_version == "auto":
        # Extract version from the input file name
        if input_file and input_file.endswith(".hex"):
            sw_version = input_file.split("_")[-1].replace(".hex", "")
            try:
                sw_version = int(sw_version, 16)  # Convert hex string to integer
            except ValueError:
                print("Invalid SW version format in filename. Ensure it is a valid hex number.")
                sys.exit(1)
        else:
            print ("Cannot guess SW version from the filename.")
            sys.exit(1)
    else:
        try:
            sw_version = int(args.sw_version.replace('0x', ''), 16)
        except ValueError:
            print("Invalid SW version format. Use 'auto' or a hex number (e.g., 0x1234).")
            sys .exit(1)

    if not input_file:
       print("Specify at the minimum the input file.")
       sys.exit (1)  
    if not output_file:
        output_file = input_file.replace(".hex", ".lsn")

    if input_file == output_file:
        print("Input and output files cannot be the same.")
        sys.exit(1)

    # Here you would add the logic to convert the .hex file to .lsn
    print(f"Converting {input_file} to {output_file} with SW version 0x{sw_version:x}")
    convert (input_file, output_file, sw_version)


def convert_checksum(val, bits):
    """
    Convert a value to its checksum representation.
    The checksum is the bitwise inverse of the value, plus one, masked to the specified number of bits.
    """
    mask = (1 << bits) - 1  # Create a mask for the specified number of bits
    inverse = ~val & mask  # Bitwise NOT and apply mask
    return (inverse + 1) & mask  # Add one and apply mask again

def hex_line_error_checking(num, line):
    #Check basic conformance
    if (len(line) < 3):
        sys.exit(f"Line {num} has a length of {len(line)}, the full line is {line}")
    if (line[0:1] != bytes(":","utf-8")):
        sys.exit(f"Line {num} does not start with a ':', it starts with a {line[0:1]}")

    #Valid data starts after the initial colon and goes until before the last 2 nibbles, which are the line checksum
    #More details here: https://en.wikipedia.org/wiki/Intel_HEX#Checksum_calculation
    line_length = len(line[1:-2])
    #len() gives you length in nibbles, we want bytes
    bytes_length = int(line_length/2)

    #This starts after the colon and takes two consecutive nibbles at a time and converts them to their integer values, and stops before the line checksum
    val = [int(line[1+(j*2):1+(j*2)+2], 16) for j in range(bytes_length)]
    running_sum = sum(val)
    calculated_checksum = convert_checksum(running_sum, 8)

    #Last 2 characters are the 8 bit checksum, interpreted as hex
    line_checksum = int(line[-2:], 16)

    if (calculated_checksum != line_checksum):
        sys.exit(f"Line {num} has a calculated checksum of {hex(calculated_checksum)} and a checksum at the end of the line of {hex(line_checksum)}. The total line is {line}")

def read_file(filename):        
    if (not os.path.isfile(filename)):
        sys.exit(f"The given path {filename} is not a valid file. Point to a microcontroller hex file")
    f = open(filename, mode="rb")
    lines = f.read().splitlines() #Because line usually ends with \r\n
    #We will end up with an array of 32 bit integers, because that's how all this data is written to the FPGA registers
    write_array = []
    
    for num,i in enumerate(lines):
        hex_line_error_checking(num, i)
        assert(i[0]==58) ##58 == :
        ll = int(i[1:3],16)
        aa = int(i[3:7],16)            
        tt = int(i[7:9],16)
        
        dd = [int(i[9+j*2:9+j*2+2],16) for j in range(ll)]
        
        if tt==0x04 or tt==0x05:
            print (f'Ignoring address record at line {num}')
            continue # ignore extended address records
        if tt==0x01:
            break   # end of file
        if (tt!=0):
            raise ValueError(f"Unknown record type {tt} in line {num}, {i}")
        
        # this section below checks is there was an "address skip" -- it adds zeros to the existing
        # array so that we "catch up" with the address
        if len(write_array*4)<aa:
            print (f'Appending zeros at line {i}')
            write_array += [0]*(aa//4-len(write_array))


        ## now rearrange data:
        #print (i)
        #print (f"{len(write_array)*4:x}")
        for j in range(0,ll,4):  
            try:
                val = dd[j] + (dd[j+1]<<8) + (dd[j+2]<<16) + (dd[j+3]<<24)
            except:
                # do just two
                val = (dd[j] + (dd[j+1]<<8))
            write_array.append(val)
    return write_array


def get_checksum(page):
    running_sum = 0
    for chunk in page:
        running_sum += chunk & 0xFFFF
        running_sum += (chunk & 0xFFFF0000) >> 16

    return convert_checksum(running_sum, 16)


def convert(input_file, output_file, sw_version):
    write_array = read_file(input_file)
    program_checksum = convert_checksum(sum(write_array),32)
    print ("Read %d bytes from the hex file." % (len(write_array)*4))
    num_pages = len(write_array) // 64
    if len(write_array) % 64 != 0:
        num_pages += 1
    print ("Number of pages: %d" % num_pages)
    """ THe structure of the lsn file is:
      0x00: "LNSS" (4 bytes)
      0x04: SW version (4 bytes)
      0x08: program checksum (4 bytes)
      0x0C: Number of pages (2 bytes)    
      0x0E: Reserved (2 bytes)
      0x10: Data

      Data is (number of pages x 260 bytes (256+ 4 bytes for checksum))      
    """
    with open(output_file, "wb") as f:
        f.write(b"LNSS")  # Magic number
        f.write(sw_version.to_bytes(4, 'little'))  # SW version
        f.write(program_checksum.to_bytes(4, 'little'))  # Program checksum
        f.write(num_pages.to_bytes(2, 'little'))  # Number of pages
        f.write((0).to_bytes(2, 'little'))  # Reserved

        for i in range(num_pages):
            page_data = write_array[i * 64:(i + 1) * 64]
            page_data += [0] * (64 - len(page_data))  # Pad to 64 words
            checksum = get_checksum(page_data)
            page_data.append(checksum)  # Append checksum
            assert(len(page_data) == 65)
            for word in page_data:
                f.write(word.to_bytes(4, 'little'))
            

    print(f"Conversion complete. Output written to {output_file}")



if __name__ == "__main__":
    main()



