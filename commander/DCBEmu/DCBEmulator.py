from .uart_comm import LuSEE_UART
from .ethernet_comm import LuSEE_ETHERNET
import threading
import time

class DCBEmulator:
    def __init__ (self, clog, uart_log, session):
        self.clog = clog
        self.uart_log = uart_log
        self.session = session

        self.clog.log ("DCB Emulator backend initializing\n\n")
        
        self.clog.log("Attempting to open UART serial...\n")
        self.uart = None
        self.uartStop = False
        luseeUart = LuSEE_UART(self.clog)
        if luseeUart.get_connections():
            if luseeUart.connect_usb(timeout = luseeUart.timeout_reg):
                self.uart = luseeUart
        self.ether = LuSEE_ETHERNET(self.clog, self.session)

        
    def uart_thread (self):
        if self.uart is not None:
            while not self.uartStop:
                uart_data = self.uart.read()
                if not self.uart_log.closed:
                    self.uart_log.write(uart_data) 
                    self.uart_log.flush()


    def reset(self):
        self.ether.reset(self.clog)

    def stop(self):
        self.uartStop = True
        self.ether.etherStop = True
        # give time for threads to stop
        time.sleep(1)

    def send_command(self, cmd, arg):
        self.ether.cdi_command(cmd, arg)
        
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
    
        from .uart_comm import LuSEE_UART
from .ethernet_comm import LuSEE_ETHERNET
from BackendBase import BackendBase
import threading
import time

class DCBEmulator:
    def __init__ (self, clog, uart_log, session):
        super().__init__(clog, uart_log, session)
        self.clog.log ("DCB Emulator backend initializing\n\n")
        
        self.clog.log("Attempting to open UART serial...\n")
        self.uart = None
        self.uartStop = False
        luseeUart = LuSEE_UART(self.clog)
        if luseeUart.get_connections():
            if luseeUart.connect_usb(timeout = luseeUart.timeout_reg):
                self.uart = luseeUart
        self.ether = LuSEE_ETHERNET(self.clog, self.save_data)

        
    def uart_thread (self):
        if self.uart is not None:
            while not self.uartStop:
                uart_data = self.uart.read()
                if not self.uart_log.closed:
                    self.uart_log.write(uart_data) 
                    self.uart_log.flush()


    def reset(self):
        self.ether.reset(self.clog)

    def stop(self):
        self.uartStop = True
        self.ether.etherStop = True
        # give time for threads to stop
        time.sleep(1)

    def send_command(self, cmd, arg):
        self.ether.cdi_command(cmd, arg)
        
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
    
        