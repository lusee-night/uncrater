import sys, os

# LuSEE script module

if os.environ.get("CORELOOP_DIR") is not None:
    sys.path.append(os.environ.get("CORELOOP_DIR"))

# now try to import pycoreloop
try:
    from pycoreloop import command as lc
    from pycoreloop import command_from_value, value_from_command
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

    def wait(self, dt):
        """Wait for dt in seconds, rounted to 100ms. If negative, wait forever"""
        if dt < 0:
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

    def cdi_wait_ticks(self, dt):
        """Wait for dt in ticks (10ms) executed on the spectrometer board"""
        self.spectrometer_command(lc.RFS_SET_WAIT_TICKS, int(dt))

    def cdi_wait_seconds(self, dt):
        """Wait for dt in seconds executed on the spectrometer board"""
        self.spectrometer_command(lc.RFS_SET_WAIT_SECS, int(dt))

    def reset(self, stored_state="ignore"):
        if stored_state == "load":
            arg_low = 0
        elif stored_state == "ignore":
            arg_low = 1
        elif stored_state == "delete_all":
            arg_low = 2
        else:
            raise ValueError("Unknown stored_state")
        self.spectrometer_command(lc.RFS_SET_RESET, arg_low)

    def ADC_special_mode(self, mode="normal"):
        print(mode)
        assert mode in ["normal", "ramp", "zeros", "ones"]
        arg = ["normal", "ramp", "zeros", "ones"].index(mode)
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

    def waveform(self, ch):
        arg = ch
        self.spectrometer_command(lc.RFS_SET_WAVEFORM, arg)

    def disable_ADC(self, bitmask=None):
        if bitmask is None:
            bitmask = 0b1111
        self.spectrometer_command(lc.RFS_SET_DISABLE_ADC, bitmask)

    def set_bitslice(self, ch, value):
        assert value < 32
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

    def set_tr_start_lsb(self, val: int):
        assert val < 0xFF
        self.spectrometer_command(lc.RFS_SET_TR_START_LSB, val)

    def set_tr_stop_lsb(self, val: int):
        assert val < 0xFF
        self.spectrometer_command(lc.RFS_SET_TR_STOP_LSB, val)

    def set_tr_avg_shift(self, val: int):
        self.spectrometer_command(lc.RFS_SET_TR_AVG_SHIFT, val)

    def time_to_die(self):
        cmd = lc.RFS_SET_TIME_TO_DIE
        arg = 0
        self.spectrometer_command(cmd, arg)

    def start(self, no_flash=False):
        cmd = lc.RFS_SET_START
        arg = 0
        if no_flash:
            arg += 1
        self.spectrometer_command(cmd, arg)

    def stop(self, no_flash=False):
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
