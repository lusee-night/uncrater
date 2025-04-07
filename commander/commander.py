import os
import sys
import select
import sys
import time
import socket
import shutil
from DCBEmu import DCBEmulator
from DCB import DCB
from CoreloopBackend import CoreloopBackend
from AWGBackendLab7 import AWGBackendLab7
from AWGBackendSSL import AWGBackendSSL

try:
    import pycoreloop as cl
    from pycoreloop import command_from_value, format_from_value
except ImportError:
    print("Can't import pycoreloop\n")
    print(
        "Please install the package or setup CORELOOP_DIR to point at CORELOOP repo. [commander.py]"
    )
    sys.exit(1)


class clogger:
    def __init__(self, fname):
        self.f = open(fname, "w")
        self.stime = int(time.time())

    def log(self, msg):
        self.f.write(msg)
        self.f.flush()

    def runtime(self):
        return int(time.time()) - self.stime

    def logt(self, msg):

        self.log(f"[ {self.runtime()}s ]: {msg}")

    def close(self):
        self.f.close()


def read_script(fname):
    script = []
    try:
        f = open(os.path.join("scripts", fname + ".scr"))
    except:
        return []
    for line in f.readlines():
        line = line.strip()
        line = line.split("#")[0]
        line = line.split()
        if len(line) > 0:
            script.append((float(line[0]), line[1:]))
    return script


class Commander:

    def __init__ (self, session = "session", script = None, commanding_ip=None, commanding_port = None, backend = 'DCBEmu', awg_backend = None):
        print ("Starting commander.")
        self.session=session
        if script is None:
            script = []
        elif type(script) == str:
            raise ValueError("Script should be a list of tuples now.")
            script = read_script(script)
        else:
            assert type(script) == list  ## oterhwise better be script.

        self.script = script

        self.prepare_directory()

        if backend == "DCBEmu":
            self.backend = DCBEmulator(self.clog, self.uart_log, self.session)
        elif backend == "DCBEmu_nouart":
            self.backend = DCBEmulator(self.clog, None, self.session)
        elif backend == "coreloop":
            self.backend = CoreloopBackend(self.clog, self.uart_log, self.session)
        elif backend == "DCB":
            print("Using the SSL DCB")
            self.backend = DCB(self.clog, self.uart_log, self.session)
        else:
            raise ValueError("Unknown backend.")

        if awg_backend is not None:
            if awg_backend[:4] == "lab7":
                if "_ch" in awg_backend:
                    ch = int(awg_backend.split("_ch")[1])
                else:
                    ch = 3
                self.awg = AWGBackendLab7(channel=ch)
            elif awg_backend == "ssl":
                self.awg = AWGBackendSSL()
            else:
                raise ValueError("Unknown AWG backend:", awg_backend)
        else:
            self.awg = None

        if commanding_port is not None:
            self.s = socket.socket()
            self.s.bind((commanding_ip, commanding_port))
            self.s.listen(5)
            self.clog.log("Listening on port 8051 for commander commanding...\n")
        else:
            self.s = None

    def reset(self):
        self.clog.logt("Resetting....")

        self.prepare_directory()
        self.backend.reset()

    def run(self):
        self.backend.run()

        stime = int(time.time())
        script_last = time.time()
        # wait for 1 second
        dt = 1.0
        wait_eos = False
        try:
            while True:
                ctime = time.time()
                have_cmd = False
                if self.s is not None:
                    ready_to_read, _, _ = select.select([self.s], [], [], 0)
                    if self.s in ready_to_read:
                        c, addr = self.s.accept()
                        input_data = c.recv(1024).decode()
                        input_data = input_data.split()
                        have_cmd = True
                else:
                    if len(self.script) > 0:                        
                        if (ctime - script_last > dt) and not wait_eos:
                            dt = 0
                            have_cmd = True
                            command = self.script[0]
                            self.script.pop(0)
                            script_last = ctime
                if have_cmd:
                    err = 0
                    if type(command) == str:
                        ## This is an out-of-band command
                        cmdx = command.split()[0]
                        if cmdx != "AWG":
                            self.clog.logt("Unknown string command:" + cmdx + "\n")
                        else:
                            print("Received AWG command: ", command[4:])
                            self.clog.logt("Received AWG command: " + command[4:] + "\n")
                            if self.awg is not None:
                                self.awg.process_command(command[4:])
                    else:
                        cmd, arg = command
                        if cmd == 0xE0:
                            # wait command
                            dt = arg / 10 if arg < 65000 else 1e100  # 65000 is forever
                            self.clog.logt(f"Waiting for {dt}s.\n")
                        elif cmd == 0xE1: 
                            # wait EOS
                            wait_eos = True
                        else:
                            if (cmd ==0x10) or (cmd == 0x11):
                                pretty_cmd = command_from_value[cmd] if cmd in command_from_value else f"UNKNOWN! {hex(cmd)} refresh pycoreloop? "
                                arg_hi, arg_lo = (arg & 0xFF00) >> 8, arg & 0x00FF
                                pretty_arg_cmd = command_from_value[arg_hi] if arg_hi in command_from_value else f"UNKNOWN {hex(arg_hi)}! refresh pycoreloop? "
                                if arg_hi == cl.value_from_command["RFS_SET_OUTPUT_FORMAT"]:
                                    arg_str = f"{format_from_value[arg_lo] if arg_lo in format_from_value else 'UNKNOWN_FORMAT'} = {arg_lo} = {hex(arg_lo)}"
                                    log_str = f"Sending command {pretty_cmd}, {pretty_arg_cmd} with argument {arg_str}.\n"
                                else:
                                    log_str = f"Sending command {pretty_cmd}, {pretty_arg_cmd} with argument {arg_lo} = {hex(arg_lo)}.\n"
                            else:
                                log_str = f"Sending FW command {hex(cmd)} with argument {hex(arg)}."

                            print(log_str)
                            self.backend.send_command(cmd, arg)
                            self.clog.logt(log_str)
                            # now wait
                            dt = 0.01
                if wait_eos and self.backend.eos_flag:
                    self.backend.drop_eos_flag()
                    wait_eos = False
                if (len(self.script) == 0) and (ctime - script_last > dt) and (not wait_eos) :
                    break

        except KeyboardInterrupt:
            print("Interrupted.")

        self.backend.stop()
        if self.awg is not None:
            self.awg.stop()
        print(f"Total test time: {self.clog.runtime()}s")
        open(os.path.join(self.session, "runtime"), "w").write(
            f"{self.clog.runtime()}\n"
        )
        print("Exiting commander.")

    def prepare_directory(self):
        if hasattr(self, "clog"):
            self.clog.close()
        if hasattr(self, "uart_log"):
            self.uart_log.close()

        if os.path.exists(self.session):
            shutil.rmtree(self.session)

        os.makedirs(self.session)
        os.makedirs(os.path.join(self.session, "cdi_output"))
        self.commander_fn = os.path.join(self.session, "commander.log")
        self.clog = clogger(self.commander_fn)
        self.uart_fn = os.path.join(self.session, "uart.log")
        self.uart_log = open(self.uart_fn, "wb")
        self.clog.log("*************\n")
        self.clog.log("* Commander *  \n")
        self.clog.log("*************\n\n")
        self.clog.log(f"Cleared session directory: {self.session} \n")


if __name__ == "__main__":
    C = Commander(commanding_ip="172.30.192.1", commanding_port=8051)
    C.run()
