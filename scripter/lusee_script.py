import sys, os, math

import bootloader as bl


# LuSEE script module

if os.environ.get("CORELOOP_DIR") is not None:
    sys.path.append(os.environ.get("CORELOOP_DIR"))

# now try to import pycoreloop
try:
    from pycoreloop import command as lc
    from pycoreloop import pystruct as pst
except ImportError:
    print("Can't import pycoreloop\n")
    print(
        "Please install the package or setup CORELOOP_DIR to point at CORELOOP repo. [lusee_script.py]"
    )
    sys.exit(1)


def lusee_command(func):
    def wrapper(*args, **kwargs):

        desc = f"{func.__name__} ("
        first = True
        for a in args[1:]:
            if not first:
                desc += ", "
            first = False
            desc += repr(a)
        for k, v in kwargs.items():
            if not first:
                desc += ", "
            desc += f"{k}="+repr(v)
            first = False
        desc += ") "
        args[0].human_script.append(desc)
        return func(*args, **kwargs)
    return wrapper


class Scripter:

    def __init__(self):
        self.script = []
        self.human_script = []
        self.total_time = 0


    def export(self, filename, meta=[]):
        """ Export the script to a file """
        with open(filename, 'w') as f:
            for line in meta:
                f.write(f"# {line}\n")
            f.write ("\n# ---- script start ---- \n")
            assert(len (self.script) == len(self.human_script))
            
            for (cmd,arg), hum in zip(self.script,self.human_script):
                if type(cmd)==str:
                    f.write(f"# {cmd}\n")
                else:
                    if hum is not None and cmd in [0x10,0x11,0xE0]:
                        f.write(f"\n# {hum}\n")
                    if cmd==0x10 or cmd==0x11:
                        f.write(f"C {cmd:02X}{arg:04X}\n")
                    if cmd==0xE0:
                        f.write(f"W {arg*10}\n")
            f.write ("\n# ---- script end ---- \n")

    def command(self, cmd, arg):
        self.total_time += (
            0.01  ## assume 10ms for a real command, already overestimated
        )
        assert (cmd >= 0) and (cmd < 256)
        assert (arg >= 0) and (arg < 65536)
        self.script.append((cmd, arg))
        while len(self.human_script) < len(self.script):
            self.human_script.append(None)

    def spectrometer_command(self, cmd, arg):
        assert arg < 256
        assert cmd < 256
        self.command(0x10, (cmd << 8) + arg)

    def spectrometer_command(self,cmd,arg):
        assert(arg<256)
        assert(cmd<256)
        self.command(lc.RFS_SETTINGS,(cmd<<8)+arg)

    @lusee_command
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
    
    @lusee_command
    def wait_eos(self,arg=0):
        """ Wait until you get an EOS packet"""
        self.command(lc.CTRL_WAIT_EOS,arg)

    @lusee_command
    def request_eos(self, arg=0):
        if (arg==0):
            arg=1 ## zero won't do anything
        self.spectrometer_command(lc.RFS_SET_SEQ_OVER,arg)

    @lusee_command
    def cdi_wait_ticks(self, dt):
        """Wait for dt in ticks (10ms) executed on the spectrometer board"""
        self.spectrometer_command(lc.RFS_SET_WAIT_TICKS, int(dt))

    @lusee_command
    def cdi_wait_seconds(self, dt):
        """Wait for dt in seconds executed on the spectrometer board"""
        self.spectrometer_command(lc.RFS_SET_WAIT_SECS, int(dt))

    @lusee_command
    def cdi_wait_minutes(self, dt):
        """Wait for dt in seconds executed on the spectrometer board"""
        self.spectrometer_command(lc.RFS_SET_WAIT_MINS, int(dt))


    @lusee_command
    def cdi_wait_spectra(self, nspectra):
        """ Wait until n stage 2 spectra are acquired"""
        assert((nspectra>0) and (nspectra<255))
        self.spectrometer_command(lc.RFS_SET_WAIT_SPECTRA,int(nspectra))

    @lusee_command
    def set_cdi_delay(self,delay):
        self.spectrometer_command(lc.RFS_SET_CDI_FW_DLY, delay)

    @lusee_command
    def set_dispatch_delay(self,delay):
        self.spectrometer_command(lc.RFS_SET_CDI_SW_DLY, delay)


    @lusee_command
    def reset(self, stored_state = 'delete_all', cdi_clear = False, special = True):
        if stored_state == 'load':
            arg_low = 0
        elif stored_state == "ignore":
            arg_low = 1
        elif stored_state == "delete_all":
            arg_low = 2
        if not cdi_clear:
            arg_low += 4
        else:
            raise ValueError("Unknown stored_state")
        master = lc.RFS_SPECIAL if special else lc.RFS_SETTINGS
        self.command(master, (lc.RFS_SET_RESET<<8)+arg_low) ## special CO

    @lusee_command
    def reboot(self):
        # there are low-level commands outside coreloop
        self.command(bl.CMD_REBOOT, 0);

    @lusee_command
    def reboot_hard(self):
        # there are low-level commands outside coreloop
        self.write_register(0x0,0x1)




    @lusee_command
    def bootloader_stay(self):
        self.command(bl.CMD_BOOTLOADER, bl.BL_STAY)

    @lusee_command
    def bootloader_check(self):
        self.command(bl.CMD_BOOTLOADER, bl.BL_GET_INFO)

    @lusee_command
    def bootloader_load_region(self, region):
        self.command(bl.CMD_BOOTLOADER, bl.BL_LOAD_REGION+(region-1))
        # there are low-level commands outside coreloop

    @lusee_command
    def bootloader_launch(self):
        self.command(bl.CMD_BOOTLOADER, bl.BL_LAUNCH)

    @lusee_command
    def bootloader_delete_region(self,region):
        self.write_register(0x630,0xDEAD0000+region)
        self.command(bl.CMD_BOOTLOADER, bl.BL_DELETE_REGION+(region<<8))
        self.wait(2)
        self.write_register(0x630,0)


    @lusee_command
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


    @lusee_command
    def write_register(self, reg, val):
        self.command(bl.CMD_REG_LSB, val & 0xFFFF)
        self.command(bl.CMD_REG_MSB, val >> 16)
        self.command(bl.CMD_REG_ADDR, reg)

    @lusee_command
    def write_register_next (self,val):
        self.command(bl.CMD_REG_LSB, val & 0xFFFF)
        self.command(bl.CMD_REG_MSB_NEXT, val >> 16)




    @lusee_command
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



    @lusee_command
    def ADC_special_mode (self, mode='normal'):
        print (mode)
        assert(mode in ['normal', 'ramp','zeros', 'ones'])
        arg = ['normal', 'ramp','zeros', 'ones'].index(mode)
        self.spectrometer_command(lc.RFS_SET_ADC_SPECIAL, arg)

    @lusee_command
    def house_keeping(self, req_type):
        assert req_type < 4
        self.spectrometer_command(lc.RFS_SET_HK_REQ, req_type)

    @lusee_command
    def section_break(self):
        self.spectrometer_command(lc.RFS_SET_HK_REQ, 99)

    @lusee_command
    def adc_range(self):
        self.spectrometer_command(lc.RFS_SET_RANGE_ADC, 0x0)

    @lusee_command
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

    @lusee_command
    def set_ana_gain(self, gains):
        assert len(gains) == 4
        cmd = lc.RFS_SET_GAIN_ANA_SET
        arg = 0
        for c in gains[::-1]:
            assert c in "LMHA"
            arg = (arg << 2) + "LMHA".index(c)
        self.spectrometer_command(cmd, arg)

    @lusee_command
    def set_notch(self, Nshift=4, disable_subtract=False, notch_detector=False):
        if (Nshift%2==1) and not disable_subtract:
            print("Warning: Nshift in notch should be even!")
            
        cmd = lc.RFS_SET_AVG_NOTCH
        arg = Nshift
        if disable_subtract:
            arg+=16
        elif notch_detector:
            arg+=32
        self.spectrometer_command(cmd, arg)

    @lusee_command
    def waveform(self, ch):
        arg = ch
        self.spectrometer_command(lc.RFS_SET_WAVEFORM, arg)

    @lusee_command
    def disable_ADC(self, bitmask=None):
        if bitmask is None:
            bitmask = 0b1111
        self.spectrometer_command(lc.RFS_SET_DISABLE_ADC, bitmask)

    @lusee_command
    def enable_heartbeat (self, enable=True):
        self.spectrometer_command(lc.RFS_SET_HEARTBEAT, int(enable))

    @lusee_command
    def enable_watchdogs(self, enable=0xFF):
        self.spectrometer_command(lc.RFS_SET_ENABLE_WATCHDOGS, enable)


    @lusee_command
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

    @lusee_command
    def set_bitslice_auto(self, keep_bits):
        cmd = lc.RFS_SET_BITSLICE_AUTO
        if keep_bits == False:
            keep_bits = 0
        arg = keep_bits
        self.spectrometer_command(cmd, arg)


    @lusee_command
    def set_avg_mode(self, mode='float'):
        if mode=='int':
            arg = pst.AVG_INT32
        elif mode=='40bit':
            arg = pst.AVG_INT_40_BITS
        elif mode=='float':
            arg = pst.AVG_FLOAT
        else:
            print("Unknown mode for set_avg_mode:", mode)
            print ("Must be one of, int, 40bit, float")
            raise ValueError
        self.spectrometer_command(lc.RFS_SET_AVG_MODE, arg)

    @lusee_command
    def range_ADC(self):
        cmd = lc.RFS_SET_RANGE_ADC
        arg = 0
        self.spectrometer_command(cmd, arg)

    @lusee_command
    def select_products(self, mask):
        if type(mask) == str:
            if mask == "auto_only":
                mask = 0b1111
            elif mask == 'all':
                mask = 0b11111111
            elif type(mask) == str:
                print("Unknown mask type for select_products:", mask)
                raise ValueError

        assert type(mask) == int
        low = mask & 0x00FF
        high = (mask & 0xFF00) >> 8
        self.spectrometer_command(lc.RFS_SET_PRODMASK_LOW, low)
        self.spectrometer_command(lc.RFS_SET_PRODMASK_HIGH, high)

    @lusee_command
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

    @lusee_command
    def set_Navg(self, Navg1, Navg2):
        assert (Navg1 < 24) and (Navg1>=8) and (Navg2 < 16) and (Navg2>=0)
        val = (Navg1-8) + (Navg2 << 4)
        self.spectrometer_command(lc.RFS_SET_AVG_SET, val)

    @lusee_command
    def set_avg_set_hi(self, frac: int):
        self.spectrometer_command(lc.RFS_SET_AVG_SET_HI, frac)

    @lusee_command
    def set_avg_set_mid(self, frac: int):
        self.spectrometer_command(lc.RFS_SET_AVG_SET_MID, frac)

    @lusee_command
    def set_avg_freq(self, val: int):
        assert val in [1, 2, 3, 4]
        self.spectrometer_command(lc.RFS_SET_AVG_FREQ, val)

    @lusee_command
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
    @lusee_command
    def _set_tr_start_lsb(self, val: int):
        assert val < 0xFF
        self.spectrometer_command(lc.RFS_SET_TR_START_LSB, val)

    @lusee_command
    def _set_tr_stop_lsb(self, val: int):
        assert val < 0xFF
        self.spectrometer_command(lc.RFS_SET_TR_STOP_LSB, val)

    @lusee_command
    def set_tr_avg_shift(self, val: int):
        self.spectrometer_command(lc.RFS_SET_TR_AVG_SHIFT, val)

    @lusee_command
    def set_spectra_format(self, val: int):
        self.spectrometer_command(lc.RFS_SET_OUTPUT_FORMAT, val)

    @lusee_command
    def time_to_die(self):
        cmd = lc.RFS_SET_TIME_TO_DIE
        arg = 0
        self.command(lc.RFS_SPECIAL, cmd<<8+arg)

    @lusee_command
    def start(self, no_flash=True):
        cmd = lc.RFS_SET_START
        arg = 0
        if no_flash:
            arg += 1
        self.spectrometer_command(cmd, arg)

    @lusee_command
    def stop(self, no_flash=True):
        cmd = lc.RFS_SET_STOP
        arg = 0
        if no_flash:
            arg += 1
        self.spectrometer_command(cmd, arg)

    @lusee_command
    def awg_init(self):
        self.script.append("AWG INIT")

    @lusee_command
    def awg_close(self):
        self.script.append("AWG STOP")

    @lusee_command
    def awg_tone(self, ch, freq, amplitude):
        self.script.append(f"AWG TONE  {ch}  {freq} {amplitude}")


    @lusee_command
    def awg_cal_on(self, alpha):
        self.script.append(f"AWG CAL ON {alpha}")

    @lusee_command
    def awg_cal_off(self):
        self.script.append("AWG CAL OFF")

    @lusee_command
    def cal_enable(self, enable=True, mode=0x10):
        if enable:
            arg = mode
        else:
            arg = 0xFF
        self.spectrometer_command(lc.RFS_SET_CAL_ENABLE,arg )

    @lusee_command
    def cal_set_pfb_bin(self,ndx):
        self.spectrometer_command(lc.RFS_SET_CAL_PFB_NDX_LO,ndx&0x00FF)
        self.spectrometer_command(lc.RFS_SET_CAL_PFB_NDX_HI,(ndx&0xFF00)>>8)


    @lusee_command
    def cal_set_avg(self, avg2, avg3):
        assert(avg2 in [5,6,7,8])
        avg2 = avg2-5
        avg = (avg3<<2)+avg2
        self.spectrometer_command(lc.RFS_SET_CAL_AVG, avg)

    @lusee_command
    def cal_set_zoom_ch(self, ch1=0, ch2=1, mode='all'):
        assert mode in ['auto00', 'auto_both', 'all']
        assert (ch1>=0 & ch1<4)
        assert (ch2>=0 & ch2<4)

        if mode == 'auto00':
            mode_val = 0
        elif mode == 'auto_both':
            mode_val = 1
        else:
            mode_val = 2
        arg = (mode_val << 6) + (ch2 << 3) + ch1
        self.spectrometer_command(lc.RFS_SET_ZOOM_CH, arg)

    @lusee_command
    def cal_set_zoom_navg(self, avg):
        self.spectrometer_command(lc.RFS_SET_ZOOM_NAVG, avg)

    @lusee_command
    def cal_set_single_weight(self,bin,weight,zero_first=False):
        if zero_first:
            self.spectrometer_command(lc.RFS_SET_CAL_WEIGHT_ZERO,0x0)
        if (bin<256):
            self.spectrometer_command(lc.RFS_SET_CAL_WEIGHT_NDX_LO,bin)
        else:
            self.spectrometer_command(lc.RFS_SET_CAL_WEIGHT_NDX_HI,bin-256)
        self.spectrometer_command(lc.RFS_SET_CAL_WEIGHT_VAL,weight)


    @lusee_command
    def cal_set_weights(self,weights):
        assert len(weights) == 512
        self.spectrometer_command(lc.RFS_SET_CAL_WEIGHT_ZERO,0x0)
        self.spectrometer_command(lc.RFS_SET_CAL_WEIGHT_NDX_LO,90)
        for i,w in enumerate(weights[90:]):
            #self.spectrometer_command(lc.RFS_SET_CAL_WEIGHT_VAL, (i+90)%256)

            self.spectrometer_command(lc.RFS_SET_CAL_WEIGHT_VAL, int(round(w * 255)))

    @lusee_command
    def cal_antenna_enable(self,mask):
        self.spectrometer_command(lc.RFS_SET_CAL_ANT_EN,mask)

    @lusee_command
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

    @lusee_command
    def cal_set_drift_step(self, step):
        self.spectrometer_command(lc.RFS_SET_CAL_DRIFT_STEP,step)

    @lusee_command
    def cal_set_corrAB(self, corrA, corrB):
        corrA = int (corrA*16)
        corrB = int (corrB*16)
        self.spectrometer_command(lc.RFS_SET_CAL_CORRA_LSB, corrA & 0xFF)
        if corrA > 255:
            self.spectrometer_command(lc.RFS_SET_CAL_CORRA_MSB, (corrA >> 8) & 0xFF)
        self.spectrometer_command(lc.RFS_SET_CAL_CORRB_LSB, corrB & 0xFF)
        if corrB > 255:
            self.spectrometer_command(lc.RFS_SET_CAL_CORRB_MSB, (corrB >> 8) & 0xFF)

    @lusee_command
    def set_alarm_setpoint(self, val):
        assert (val < 256)
        self.spectrometer_command(lc.RFS_SET_TEMP_ALARM, val)

    @lusee_command
    def cal_set_slicer (self, auto=None, powertop=None, sum1=None, sum2=None, prod1=None, prod2=None, delta_powerbot=None, fd_slice=None, sd2_slice=None):
        def cal_slicer_command (reg, val):
            self.spectrometer_command (lc.RFS_SET_CAL_BITSLICE, (reg<<5)+val)

        if fd_slice is not None:
            cal_slicer_command(0, fd_slice)
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

        if auto is not None:
            self.spectrometer_command(lc.RFS_SET_CAL_BITSLICE_AUTO, int(auto))



    # this is drift min / max ,i.e. 1.2ppm = 120 at x16, but we supply number/20
    @lusee_command
    def cal_set_drift_guard(self, guard):
        guard = int(guard/20)
        if (guard>255):
            guard = 255
            print ("Warning: guard too large, setting to 255*20")

        self.spectrometer_command(lc.RFS_SET_CAL_DRIFT_GUARD, guard)




    # this is delta drift
    @lusee_command
    def cal_set_ddrift_guard(self, guard):
        guard = int(guard/25)
        if (guard>255):
            guard = 255
            print ("Warning: guard too large, setting to 255*25")

        self.spectrometer_command(lc.RFS_SET_CAL_DDRIFT_GUARD, guard)

    @lusee_command
    def cal_set_gphase_guard(self, guard):
        guard = int(guard/2000)
        if (guard>255):
            guard = 255
            print ("Warning: guard too large, setting to 255*2000")

        self.spectrometer_command(lc.RFS_SET_CAL_GPHASE_GUARD, guard)


    @lusee_command
    def cal_weights_save (self, slot):
        assert (slot >= 0) and (slot < 16)
        self.spectrometer_command(lc.RFS_SET_CAL_WSAVE, slot)

    @lusee_command
    def cal_weights_load (self, slot):
        assert (slot >= 0) and (slot < 16)
        self.spectrometer_command(lc.RFS_SET_CAL_WLOAD, slot)

    @lusee_command
    def cal_raw11_every(self, value):
        """ Set the raw11 every value, i.e. how many compress 11 packets to average before sending raw11 data.
            Value is in range 0-255, 0x00 means all packets are raw, 0xFF means never
        """
        assert (value >= 0) and (value < 256)
        self.spectrometer_command(lc.RFS_SET_CAL_RAW11_EVERY, value)

    @lusee_command
    def notch_detector (self, enable=True):
        self.spectrometer_command(lc.RFS_SET_NOTCH_DETECTOR, int(enable))

    ## flow control part
    @lusee_command
    def seq_begin(self):
        self.command(lc.RFS_SPECIAL, lc.RFS_SET_SEQ_BEGIN<<8)

    @lusee_command
    def seq_end(self, store_flash=False):
        self.command(lc.RFS_SPECIAL, (lc.RFS_SET_SEQ_END<<8) + (1 if store_flash else 0))

    @lusee_command
    def seq_break(self):
        self.command(lc.RFS_SPECIAL, lc.RFS_SET_BREAK<<8)

    @lusee_command
    def flash_clear(self):
        self.spectrometer_command(lc.RFS_SET_FLASH_CLR,0)

    @lusee_command
    def loop_start(self, repetitions):
        self.spectrometer_command(lc.RFS_SET_LOOP_START, repetitions)

    @lusee_command
    def loop_next(self):
        self.spectrometer_command(lc.RFS_SET_LOOP_NEXT,0)

    @lusee_command
    def reject_enable(self, enable=True, reject_frac = 16, max_bad = 20):
        if enable == False:
            self.spectrometer_command(lc.RFS_SET_REJ_SET,0)
        else:
            self.spectrometer_command(lc.RFS_SET_REJ_SET,reject_frac)
            self.spectrometer_command(lc.RFS_SET_REJ_NBAD, max_bad)

    @lusee_command
    def enable_grimm_tales(self, enable=True):
        self.spectrometer_command(lc.RFS_SET_GRIMMS_TALES, int(enable))

    @lusee_command
    def grimm_tales_weight (self, ndx, val):
        assert (ndx<32)
        assert (val>=0) and (val<=255)
        self.spectrometer_command(lc.RFS_SET_GRIMM_W_NDX, ndx)
        self.spectrometer_command(lc.RFS_SET_GRIMM_W_VAL, val)
        