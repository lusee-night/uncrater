from uart_comm import LuSEE_UART
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
        
 

def remove_LR(data):
    return data.replace(b'\x0A', b'')

def loop(clog, uart, uart_log,s):
    stime = int(time.time())
    
    while True:
        if uart is not None:
            uart_data = luseeUart.read()
            uart_data = remove_LR(uart_data)
            uart_log.write(uart_data) 
            uart_log.flush()
        ready_to_read, _, _ = select.select([s], [], [], 0)
        if s in ready_to_read:
            c, addr = s.accept()
            input_data = c.recv(1024).decode()       
            print(f"got data: {input_data}")
            clog.logt (f" Received: {input_data}\n")
    
def create_or_clear_directory(directory):
    if os.path.exists(directory):
        shutil.rmtree(directory)

    os.makedirs(directory)


if __name__ == "__main__":
    session="session"
    create_or_clear_directory(session)
    commander_fn = os.path.join(session, "commander.log")
    clog = clogger(commander_fn)
    clog.log("*************\n")
    clog.log("* Commander *  \n")
    clog.log("*************\n\n")
    clog.log(f"Cleared session directory: {session} \n")

    uart_fn = os.path.join(session, "uart.log")
    uart_log = open(uart_fn, "wb")
    clog.log("Attempting to open UART serial...\n")
    uart = None
    luseeUart = LuSEE_UART(clog)
    if luseeUart.get_connections():
        if luseeUart.connect_usb(timeout = luseeUart.timeout_reg):
           uart = LuSEE_UART
        
    s = socket.socket()
    s.bind(('127.0.0.1', 8051))
    s.listen(5)
    clog.log('Listening on port 8051...\n')


    clog.log("\n\nEntering main loop.\n")   
    loop(clog, uart, uart_log,s)

    



