from uart_comm import LuSEE_UART
from ethernet_comm import LuSEE_ETHERNET
import os
import sys
import select
import sys
import time 
import socket
import shutil


class clogger:
    def __init__(self, fname):
        self.f = open(fname, "w")
        self.stime = int(time.time())


    def log(self, msg):
        self.f.write(msg)
        self.f.flush()

    def logt (self,msg):
        dt = int(time.time()) - self.stime
        self.log(f"[ {dt}s ]: {msg}")
        
    def close(self):
        self.f.close()
        

def remove_LR(data):
    return data.replace(b'\x0A', b'')

def read_script(fname):
    script = []
    try:
        f = open(fname)
    except:
        return []
    for line in f.readlines():
        line = line.strip()
        line = line.split("#")[0]
        line = line.split()
        if len(line)>0:
            script.append((int(line[0]), line[1:]))
    return script

class Commander:
    
    def __init__ (self):
        print ("Starting commander.")
        self.session="session"
        self.prepare_directory()


        self.clog.log("Attempting to open UART serial...\n")
        self.uart = None
        luseeUart = LuSEE_UART(self.clog)
        if luseeUart.get_connections():
            if luseeUart.connect_usb(timeout = luseeUart.timeout_reg):
                self.uart = luseeUart
        self.ether = LuSEE_ETHERNET(self.clog, self.session)

        self.s = socket.socket()
        self.s.bind(('172.30.192.1', 8051))
        self.s.listen(5)
        self.clog.log('Listening on port 8051 for commander commanding...\n')


    def reset(self):
       self.clog.logt('Resetting....') 
       
       self.prepare_directory()
       self.cdi_command(0x02, 0)
       #self.ether.reset(self.clog)
        
    def run(self):
        self.clog.log("\n\nEntering main loop.\n")   

        stime = int(time.time())
        script = []
        while True:

            if self.uart is not None:
                uart_data = self.uart.read()
                uart_data = remove_LR(uart_data)
                self.uart_log.write(uart_data) 
                self.uart_log.flush()
            ready_to_read, _, _ = select.select([self.s], [], [], 0)

            have_cmd = False
            if self.s in ready_to_read:
                c, addr = self.s.accept()
                input_data = c.recv(1024).decode()       
                input_data = input_data.split() 
                have_cmd = True
            else:
                if len(script)>0:
                    dt, cmd = script[0]
                    ctime = time.time()
                    if ctime-script_last>dt:
                        input_data = cmd
                        have_cmd = True
                        script.pop(0)
                        script_last = ctime
            if have_cmd:
                err =0 
                if len(input_data)==0:
                    input_data=[""]
                cmd = input_data[0]
                if cmd=='CMD':
                    cmd,arg = input_data[1:]
                    try:
                        cmd = int(cmd,16)
                        arg = int(arg,16)
                    except:
                        err = 1
                    if (err == 0):
                        self.ether cdi_command(cmd, arg)
                        self.clog.logt (f" Sent CDI command {hex(cmd)} with argument {hex(arg)} .\n")
                elif cmd == 'reset':
                    self.reset()
                elif cmd == 'save':
                    os.system(f'cp -r {self.session} {input_data[1]}')
                elif input_data[0] == 'script':
                    script = read_script(input_data[1])) +script
                    script_last = time.time()
                else:
                    self.clog.logt(f"Unknown command: {input_data}\n")
                    err = 1
                if err:
                    self.clog.logt(f"Error processing command: {input_data}\n")
            self.ether.ListenForData()


            if len(script)>0:
                ctime = time.time()




        
    def prepare_directory(self):
        if hasattr(self,"clog"):
            self.clog.close()
        if hasattr(self,"uart_log"):
            self.uart_log.close()
            
        if os.path.exists(self.session):
            shutil.rmtree(self.session)

        os.makedirs(self.session)
        os.makedirs(os.path.join(self.session,'cdi_output'))
        self.commander_fn = os.path.join(self.session, "commander.log")
        self.clog = clogger(self.commander_fn)
        self.uart_fn = os.path.join(self.session, "uart.log")
        self.uart_log = open(self.uart_fn, "wb")
        self.clog.log("*************\n")
        self.clog.log("* Commander *  \n")
        self.clog.log("*************\n\n")
        self.clog.log(f"Cleared session directory: {self.session} \n")
        


if __name__ == "__main__":
        C=Commander()
        C.run()



