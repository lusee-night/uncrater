import sys, os, math

import bootloader as bl


# LuSEE script module

if os.environ.get("CORELOOP_DIR") is not None:
    sys.path.append(os.environ.get("CORELOOP_DIR"))

# now try to import pycoreloop
try:
    from pycoreloop import command as lc
except ImportError:
    print("Can't import pycoreloop\n")
    print(
        "Please install the package or setup CORELOOP_DIR to point at CORELOOP repo. [lusee_script.py]"
    )
    sys.exit(1)



class Scripter:

    def __init__(self):
        self.script = []
        self.total_time = 0

    def command(self, cmd, arg):
        self.total_time += (
            0.01  ## assume 10ms for a real command, already overestimated
        )
        assert (cmd >= 0) and (cmd < 256)
        assert (arg >= 0) and (arg < 65536)
        self.script.append((cmd, arg))

    def spectrometer_command(self, cmd, arg):
        assert arg < 256
        assert cmd < 256
        self.command(0x10, (cmd << 8) + arg)

    def spectrometer_command(self,cmd,arg):
        assert(arg<256)
        assert(cmd<256)
        self.command(lc.RFS_SETTINGS,(cmd<<8)+arg)


    def wait (self, dt):
        """ Wait for dt in seconds, rounted to 100ms. If negative, wait forever"""
        if dt<0:
            dt = 65000
        else:
            if dt < 0.1:
                print("Warning: wait time too short")
            elif dt > 6500.0:
                print("Warning: wait time too long, rounding down")
                dt = 6499.9
            dt = int(dt * 10)
            self.total_time += dt / 10
        self.command(lc.CTRL_WAIT, dt)

    def wait_eos(self,arg=0):
        """ Wait until you get an EOS packet"""
        self.command(lc.CTRL_WAIT_EOS,arg)

    def request_eos(self, arg=0):
        if (arg==0):
            arg=1 ## zero won't do anything
        self.spectrometer_command(lc.RFS_SET_SEQ_OVER,arg)

    def cdi_wait_ticks(self, dt):
        """Wait for dt in ticks (10ms) executed on the spectrometer board"""
        self.spectrometer_command(lc.RFS_SET_WAIT_TICKS, int(dt))

    def cdi_wait_seconds(self, dt):
        """Wait for dt in seconds executed on the spectrometer board"""
        self.spectrometer_command(lc.RFS_SET_WAIT_SECS, int(dt))

    def cdi_wait_minutes(self, dt):
        """Wait for dt in seconds executed on the spectrometer board"""
        self.spectrometer_command(lc.RFS_SET_WAIT_MINS, int(dt))


    def cdi_wait_spectra(self, nspectra):
        """ Wait until n stage 2 spectra are acquired"""
        assert((nspectra>0) and (nspectra<255))
        self.spectrometer_command(lc.RFS_SET_WAIT_SPECTRA,int(nspectra))

    def set_cdi_delay(self,delay):
        self.spectrometer_command(lc.RFS_SET_CDI_FW_DLY, delay)

    def set_dispatch_delay(self,delay):
        self.spectrometer_command(lc.RFS_SET_CDI_SW_DLY, delay)


    def reset(self, stored_state = 'ignore', special = True):
        if stored_state == 'load':
            arg_low = 0
        elif stored_state == "ignore":
            arg_low = 1
        elif stored_state == "delete_all":
            arg_low = 2
        else:
            raise ValueError("Unknown stored_state")
        master = lc.RFS_SPECIAL if special else lc.RFS_SETTINGS
        self.command(master, (lc.RFS_SET_RESET<<8)+arg_low) ## special CO

    def reboot(self):
        # there are low-level commands outside coreloop
        self.command(bl.CMD_REBOOT, 0);
    
    def reboot_hard(self):
        # there are low-level commands outside coreloop
        self.write_register(0x0,0x1)




    def bootloader_stay(self):
        self.command(bl.CMD_BOOTLOADER, bl.BL_STAY)

    def bootloader_check(self):
        self.command(bl.CMD_BOOTLOADER, bl.BL_GET_INFO)

    def bootloader_load_region(self, region):
        self.command(bl.CMD_BOOTLOADER, bl.BL_LOAD_REGION+(region-1))

    def bootloader_launch(self):
        self.command(bl.CMD_BOOTLOADER, bl.BL_LAUNCH)

    def bootloader_delete_region(self,region):
        self.write_register(0x630,0xDEAD0000+region)
        self.command(bl.CMD_BOOTLOADER, bl.BL_DELETE_REGION+(region<<8))
        self.wait(2)
        self.write_register(0x630,0)


    def bootloader_write_region(self, region, write_array, slow=False):

        def write_hex_page(page, page_num, region, slow):
            #Jack does 16 bit checksums for each page, so I need to split the 32 bit int to add it for the running checksum
            running_sum = 0
            for num,chunk in enumerate(page):
                running_sum += chunk & 0xFFFF
                running_sum += (chunk & 0xFFFF0000) >> 16
                # the pre 0x22a way is 
                #self.write_register(0x640 + num, chunk)
                if num == 0:
                    self.write_register(0x640, chunk)
                else:
                    self.write_register_next(chunk)
                
            print(f"Page {page_num} checksum is {hex(bl.convert_checksum(running_sum, 16))}")
            self.write_register(0x621, bl.convert_checksum(running_sum, 16))
            self.write_register(0x620, page_num)
            self.command(bl.CMD_BOOTLOADER, bl.BL_WRITE_FLASH + (region << 8))
            self.wait(2 if slow else 0.1)

        print(f"Rearranged the input data.")
        array_length = len(write_array)  #Total number of 32 bit chunks
        pages = array_length // 64 #Each page in Flash is 64 of these 32 bit chunks, for 256 bytes (2048 bits) total
        leftover = array_length % 64 #The last page may not be filled, so we need to know when to start padding 0s
        effective_pages = pages
        if leftover:
            effective_pages += 1
        program_size = effective_pages * 64
        program_checksum = bl.convert_checksum(sum(write_array), 32)
        print(f"Program size is {hex(program_size)} and program checksum is {hex(program_checksum)}")
        self.write_register(0x630, 0xFEED0000 + region)
        #Run through all full pages
        for i in range(pages):
            print(f"Writing page {i}/{pages}")
            page = write_array[i*64:(i+1)*64]
            write_hex_page(page, i, region, slow)
        #And do the final partial page if necessary
        if (leftover):
            print(f"Writing page {pages}/{pages}")
            #Fill the rest of this partial page with 0s
            final_page = write_array[pages*64:]
            filled_zeros = [0] * (64-leftover)
            final_page.extend(filled_zeros)
            write_hex_page(final_page, pages, region,slow)

        self.write_register(0x630, 0)

        #Write all the metadata
        self.write_register(0x632, 0xFEED0000 + region)
        self.write_register(0x630, program_size)
        self.write_register(0x631, program_checksum)
        self.command(bl.CMD_BOOTLOADER, bl.BL_WRITE_METADATA + (region << 8))
        self.wait(1)
        self.write_register(0x632, 0)


    def write_register(self, reg, val):
        self.command(bl.CMD_REG_LSB, val & 0xFFFF)
        self.command(bl.CMD_REG_MSB, val >> 16)
        self.command(bl.CMD_REG_ADDR, reg)

    def write_register_next (self,val):
        self.command(bl.CMD_REG_LSB, val & 0xFFFF)
        self.command(bl.CMD_REG_MSB_NEXT, val >> 16)

        


    def write_adc_register(self,adc, reg, val):
        assert(reg < 256)
        assert(val < 256)
        final_val = reg + (val << 8)
        ADC_REG_DATA = 0x303
        ADC_FUNCTION = 0x302
        self.write_register(ADC_REG_DATA, final_val)
        self.write_register(ADC_FUNCTION, 1 << adc)
        self.wait(0.1)
        self.write_register(ADC_FUNCTION, 0)

    

    def ADC_special_mode (self, mode='normal'):
        print (mode)
        assert(mode in ['normal', 'ramp','zeros', 'ones'])
        arg = ['normal', 'ramp','zeros', 'ones'].index(mode)
        self.spectrometer_command(lc.RFS_SET_ADC_SPECIAL, arg)

    def house_keeping(self, req_type):
        assert req_type < 2
        self.spectrometer_command(lc.RFS_SET_HK_REQ, req_type)

    def section_break(self):
        self.spectrometer_command(lc.RFS_SET_HK_REQ, 99)

    def adc_range(self):
        self.spectrometer_command(lc.RFS_SET_RANGE_ADC, 0x0)

    def set_route(self, ch, plus, minus=None, gain="M"):
        assert (ch >= 0) and (ch < 4)
        cmd = lc.RFS_SET_ROUTE_SET1 + ch
        if minus is None:
            minus = 4
        if plus is None:
            plus = 4
        print("route", plus, minus, gain, ch)
        assert gain in "LMHD"
        gain = "LMHD".index(gain)
        arg = (gain << 6) + (minus << 3) + plus
        self.spectrometer_command(cmd, arg)

    def set_ana_gain(self, gains):
        assert len(gains) == 4
        cmd = lc.RFS_SET_GAIN_ANA_SET
        arg = 0
        for c in gains[::-1]:
            assert c in "LMHA"
            arg = (arg << 2) + "LMHA".index(c)
        self.spectrometer_command(cmd, arg)

    def set_notch(self, Nshift=4):
        if (Nshift%2==1):
            print("Warning: Nshift in notch should be even!")
            raise ValueError
        cmd = lc.RFS_SET_AVG_NOTCH
        arg = Nshift
        self.spectrometer_command(cmd, arg)

    def waveform(self, ch):
        arg = ch
        self.spectrometer_command(lc.RFS_SET_WAVEFORM, arg)

    def disable_ADC(self, bitmask=None):
        if bitmask is None:
            bitmask = 0b1111
        self.spectrometer_command(lc.RFS_SET_DISABLE_ADC, bitmask)

    def enable_heartbeat (self, enable=True):
        self.spectrometer_command(lc.RFS_SET_HEARTBEAT, int(enable))

    def set_bitslice(self, ch, value):
        assert value < 32
        if ch=='all':
            for ch in range(16):
                self.set_bitslice(ch, value)
            return
        if ch < 8:
            cmd = lc.RFS_SET_BITSLICE_LOW
        else:
            cmd = lc.RFS_SET_BITSLICE_HIGH
            ch -= 8

        arg = ch + (value << 3)
        self.spectrometer_command(cmd, arg)

    def set_bitslice_auto(self, keep_bits):
        cmd = lc.RFS_SET_BITSLICE_AUTO
        if keep_bits == False:
            keep_bits = 0
        arg = keep_bits
        self.spectrometer_command(cmd, arg)

    def range_ADC(self):
        cmd = lc.RFS_SET_RANGE_ADC
        arg = 0
        self.spectrometer_command(cmd, arg)

    def select_products(self, mask):
        if type(mask) == str:
            if mask == "auto_only":
                mask = 0b1111
            else:
                print("Unknown mask type for select_products:", mask)
                raise ValueError

        assert type(mask) == int
        low = mask & 0x00FF
        high = (mask & 0xFF00) >> 8
        self.spectrometer_command(lc.RFS_SET_PRODMASK_LOW, low)
        self.spectrometer_command(lc.RFS_SET_PRODMASK_HIGH, high)

    def set_agc_settings(self, ch, low=256, mult=8):
        assert low < 1024
        assert mult < 16
        assert ch < 4
        if (low % 16) != 0:
            print("Warning: low should be a multiple of 16. Rouding down")
        low = low // 16
        arg1 = (low << 2) + ch
        arg2 = (mult << 2) + ch
        print("AGC settings", arg1, arg2)
        self.spectrometer_command(lc.RFS_SET_GAIN_ANA_CFG_MIN, arg1)
        self.spectrometer_command(lc.RFS_SET_GAIN_ANA_CFG_MULT, arg2)

    def set_Navg(self, Navg1, Navg2):
        val = Navg1 + (Navg2 << 4)
        self.spectrometer_command(lc.RFS_SET_AVG_SET, val)

    def set_avg_set_hi(self, frac: int):
        self.spectrometer_command(lc.RFS_SET_AVG_SET_HI, frac)

    def set_avg_set_mid(self, frac: int):
        self.spectrometer_command(lc.RFS_SET_AVG_SET_MID, frac)

    def set_avg_freq(self, val: int):
        assert val in [1, 2, 3, 4]
        self.spectrometer_command(lc.RFS_SET_AVG_FREQ, val)

    def set_tr_start_stop(self, start: int, stop: int):
        assert 0 <= start <= 2048 and 0 <= stop <= 2048
        start_lsb, stop_lsb = start & 0xFF, stop & 0xFF
        start_msb_part, stop_msb_part  = (start >> 8) & 0x0F, (stop >> 8) & 0x0F
        # combine bits 12-8 of start and stop into one byte tr_st
        tr_st = (stop_msb_part << 4) | start_msb_part
        self.spectrometer_command(lc.RFS_SET_TR_START_LSB, start_lsb)
        self.spectrometer_command(lc.RFS_SET_TR_STOP_LSB, stop_lsb)
        self.spectrometer_command(lc.RFS_SET_TR_ST_MSB, tr_st)

    # low-level commands are not supposed to be used directly, keep just in case
    def _set_tr_start_lsb(self, val: int):
        assert val < 0xFF
        self.spectrometer_command(lc.RFS_SET_TR_START_LSB, val)

    def _set_tr_stop_lsb(self, val: int):
        assert val < 0xFF
        self.spectrometer_command(lc.RFS_SET_TR_STOP_LSB, val)

    def set_tr_avg_shift(self, val: int):
        self.spectrometer_command(lc.RFS_SET_TR_AVG_SHIFT, val)

    def set_spectra_format(self, val: int):
        self.spectrometer_command(lc.RFS_SET_OUTPUT_FORMAT, val)

    def time_to_die(self):
        cmd = lc.RFS_SET_TIME_TO_DIE
        arg = 0
        self.spectrometer_command(cmd, arg)

    def start(self, no_flash=True):
        cmd = lc.RFS_SET_START
        arg = 0
        if no_flash:
            arg += 1
        self.spectrometer_command(cmd, arg)

    def stop(self, no_flash=True):
        cmd = lc.RFS_SET_STOP
        arg = 0
        if no_flash:
            arg += 1
        self.spectrometer_command(cmd, arg)

    def awg_init(self):
        self.script.append("AWG INIT")

    def awg_close(self):
        self.script.append("AWG STOP")

    def awg_tone(self, ch, freq, amplitude):
        self.script.append(f"AWG TONE  {ch}  {freq} {amplitude}")


    def awg_cal_on(self, alpha):
        self.script.append(f"AWG CAL ON {alpha}")
    
    def awg_cal_off(self):
        self.script.append("AWG CAL OFF")
        
    def cal_enable(self, enable=True, mode=0x10):
        if enable:
            arg = mode
        else:
            arg = 0xFF
        self.spectrometer_command(lc.RFS_SET_CAL_ENABLE,arg )

    def cal_set_pfb_bin(self,ndx):
        self.spectrometer_command(lc.RFS_SET_CAL_PFB_NDX_LO,ndx&0x00FF)
        self.spectrometer_command(lc.RFS_SET_CAL_PFB_NDX_HI,(ndx&0xFF00)>>8)


    def cal_set_avg(self, avg2, avg3):
        assert(avg2 in [5,6,7,8])
        avg2 = avg2-5
        avg = (avg3<<2)+avg2
        self.spectrometer_command(lc.RFS_SET_CAL_AVG, avg)


    def cal_set_single_weight(self,bin,weight,zero_first=False):
        if zero_first:
            self.spectrometer_command(lc.RFS_SET_CAL_WEIGHT_ZERO,0x0)
        if (bin<256):
            self.spectrometer_command(lc.RFS_SET_CAL_WEIGHT_NDX_LO,bin)
        else:
            self.spectrometer_command(lc.RFS_SET_CAL_WEIGHT_NDX_HI,bin-256)
        self.spectrometer_command(lc.RFS_SET_CAL_WEIGHT_VAL,weight)

    
    def cal_set_weights(self,weights):
        assert len(weights) == 512
        self.spectrometer_command(lc.RFS_SET_CAL_WEIGHT_ZERO,0x0)
        self.spectrometer_command(lc.RFS_SET_CAL_WEIGHT_NDX_LO,90)
        for w in weights[90:]:
            self.spectrometer_command(lc.RFS_SET_CAL_WEIGHT_VAL, int(round(w * 255)))

    def cal_antenna_enable(self,mask):
        self.spectrometer_command(lc.RFS_SET_CAL_ANT_EN,mask)

    def cal_SNRonff(self,snron,snroff):
        # after fix, those numbers are in Q16.4 format, so let's bump them up by 4 bits
        snron = int (snron * 16)
        snroff = int (snroff * 16)
        snron_low = snron &  0xFF
        snron_high = (snron & 0xFF00) >> 8
        self.spectrometer_command(lc.RFS_SET_CAL_SNR_ON,snron_low)
        if snron_high>0:
            self.spectrometer_command(lc.RFS_SET_CAL_SNR_ON_HIGH,snron_high)
        self.spectrometer_command(lc.RFS_SET_CAL_SNR_OFF,snroff)

    
    def set_alarm_setpoint(self, val):
        assert (val < 256)
        self.spectrometer_command(lc.RFS_SET_TEMP_ALARM, val)

    def cal_set_slicer (self, auto=None, powertop=None, sum1=None, sum2=None, prod1=None, prod2=None, delta_powerbot=None, sd2_slice=None):
        def cal_slicer_command (reg, val):
            self.spectrometer_command (lc.RFS_SET_CAL_BITSLICE, (reg<<5)+val)
        
        if auto is not None:
            cal_slicer_command(0, int(auto))
        if powertop is not None:
            cal_slicer_command(1, powertop)
        if sum1 is not None:
            cal_slicer_command(2, sum1)
        if sum2 is not None:
            cal_slicer_command(3, sum2)
        if prod1 is not None:
            cal_slicer_command(4, prod1)
        if prod2 is not None:
            cal_slicer_command(5, prod2)
        if delta_powerbot is not None:
            cal_slicer_command(6, delta_powerbot)
        if sd2_slice is not None:
            cal_slicer_command(7, sd2_slice)
