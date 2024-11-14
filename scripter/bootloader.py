# Low level commands

CMD_REBOOT = 0xFF

CMD_REG_MSB = 0xA0
CMD_REG_LSB = 0xA1
CMD_REG_ADDR = 0xA2

CMD_BOOTLOADER = 0xB0

BL_STAY = 0x00
BL_LOAD_REGION =0x01
BL_LAUNCH = 0x07
BL_GET_INFO = 0x08
BL_WRITE_FLASH = 0x0B
BL_WRITE_METADATA = 0x0C
BL_DELETE_REGION = 0x0D


def convert_checksum(val, bits):
    mask = 0
    inverse = 0
    for i in range(bits):
        mask += 0x1 << i
        original_bit = ((0x1 << i) & val) >> i
        if (original_bit):
            new_bit = 0
        else:
            new_bit = 1
        inverse += new_bit << i
    return (inverse + 1) & mask

