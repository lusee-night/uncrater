from uart_comm import LuSEE_UART
from ethernet_comm import LuSEE_ETHERNET
import os
import sys
import select
import sys
import time 
import socket
import shutil
import threading


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
        

def read_script(fname):
    script = []
    try:
        f = open(os.path.join("scripts",fname+".scr"))
    except:
        return []
    for line in f.readlines():
        line = line.strip()
        line = line.split("#")[0]
        line = line.split()
        if len(line)>0:
            script.append((float(line[0]), line[1:]))
    return script

class Commander:
    
    def __init__ (self, session = "session", script = None):
        print ("Starting commander.")
        self.session=session
        if script is None:
            script = []
        elif type(script)==str:
            script = read_script(script)
        else:
            assert(type(script)==list) ## oterhwise better be script.
        
        self.script = script
            
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
       self.ether.reset(self.clog)
        
        
    def uart_thread (self):
        if self.uart is not None:
            while not self.uartStop:
                uart_data = self.uart.read()
                if not self.uart_log.closed:
                    self.uart_log.write(uart_data) 
                    self.uart_log.flush()
    
    def run(self):
        self.clog.log('Starting UART thread \n')
        tu = threading.Thread (target = self.uart_thread, daemon = True)
        self.uartStop = False
        tu.start()    
        self.clog.log("\n\nStarting data collection threads.\n")   
        te1 = threading.Thread(target = self.ether.ListenForData, args = (0,), daemon=True)
        te2 = threading.Thread(target = self.ether.ListenForData, args = (1,), daemon=True)
        te1.start()
        te2.start()
        
        

        stime = int(time.time())
        while True:

            ready_to_read, _, _ = select.select([self.s], [], [], 0)
            have_cmd = False
            if self.s in ready_to_read:
                c, addr = self.s.accept()
                input_data = c.recv(1024).decode()       
                input_data = input_data.split() 
                have_cmd = True
            else:
                if len(self.script)>0:
                    dt, cmd = self.script[0]
                    ctime = time.time()
                    if ctime-script_last>dt:
                        input_data = cmd
                        have_cmd = True
                        self.script.pop(0)
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
                        self.ether.cdi_command(cmd, arg)
                        self.clog.logt (f" Sent CDI command {hex(cmd)} with argument {hex(arg)} .\n")
                elif cmd == 'reset':
                    self.reset()
                elif cmd == 'save':
                    tgt = input_data[1]
                    self.clog.logt(f"Saving to {input_data[1]}")
                    if os.path.exists(tgt):
                        os.system(f'rm -rf {tgt}')
                    os.system(f'cp -r {self.session} {tgt}')
                elif cmd == 'script':
                    self.script = read_script(input_data[1]) + self.script
                    script_last = time.time()
                elif cmd == 'exit':
                    break
                else:
                    self.clog.logt(f"Unknown command: {input_data}\n")
                    err = 1
                if err:
                    self.clog.logt(f"Error processing command: {input_data}\n")
        
        self.uartStop = True
        self.ether.etherStop = True
        print ('Exiting commander.')



        
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



