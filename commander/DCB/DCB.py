from .uart_comm import LuSEE_UART
from .ethernet_comm import LuSEE_ETHERNET
from BackendBase import BackendBase
import threading
import time

class DCB(BackendBase):
    def __init__ (self, clog, uart_log, session):
        super().__init__(clog, uart_log, session)
        self.clog.log ("DCB backend initializing\n\n")
        
        self.clog.log("Attempting to open UART serial...\n")
        self.uart = None
        self.uartStop = False
        luseeUart = LuSEE_UART(self.clog)
        if luseeUart.get_connections():
            if luseeUart.connect_usb(timeout = luseeUart.timeout_reg):
                self.uart = luseeUart
        self.tm_file = open(session+"/DCB_telemetry.json",'wb')
        self.ether = LuSEE_ETHERNET(self.clog, self.save_ccsds, self.tm_file)
        

        
    def uart_thread (self):
        if self.uart is not None:
            while not self.uartStop:
                try:
                    uart_data = self.uart.read()
                except:
                    pass
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
        self.te1.join()
        self.te2.join()
        self.uart_log.close()
        self.tm_file.close()
        


    def send_command(self, cmd, arg):
        self.ether.cdi_command(cmd, arg)
        time.sleep(0.2)
        
    def run(self):
        self.clog.log('Starting UART thread \n')
        tu = threading.Thread (target = self.uart_thread, daemon = True)
        self.uartStop = False
        tu.start()    
        self.clog.log("\n\nStarting data collection threads.\n")   
        self.te1 = threading.Thread(target = self.ether.ListenForData, daemon=True)
        self.te2 = threading.Thread(target = self.ether.ListenForData_TM, daemon=True)
        self.te1.start()
        self.te2.start()
