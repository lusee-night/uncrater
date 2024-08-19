from BackendBase import BackendBase
import os
import threading
import socket
import subprocess
import sys

class CoreloopBackend(BackendBase):

    def __init__(self, clog, uart_log, session):
        super().__init__(clog, uart_log, session)
        self.clog.logt("Coreloop Backend initialized\n")
        self.coreloop_exe = os.path.join(os.environ['CORELOOP_DIR'],'build','coreloop')
        if not os.path.exists(self.coreloop_exe):
            print ("Coreloop executable not found: ",self.coreloop_exe)
            sys.exit(1)
        # Open a UDP socket
        self.sockout = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.port = 32100

    def send_command(self, cmd, arg):
        b=bytearray(4)
        b[0] = ord('C')
        b[1] = cmd
        b[2]=(arg&0xFF00)>>8
        b[3]=(arg&0x00FF)
        self.sockout.sendto(b, ('localhost', self.port))


    def exec_thread(self):
        self.clog.logt("Executing Coreloop\n")
        options = f"-m port -o {os.path.join(self.session, 'cdi_output')}"
        self.clog.logt(f"Executing {self.coreloop_exe} {options}\n")
        self.process = subprocess.Popen([self.coreloop_exe]+options.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = self.process.communicate()
        self.uart_log.write(stdout)
        if stderr:
            self.uart_log.write(f"Coreloop stderr:\n".encode())
            self.uart_log.write(f"----------------\n".encode())
            self.uart_log.write(stderr)

    def reset(self):
        pass

    def stop(self):
        self.process.terminate()
        self.sockout.close()
        self.thread.join()

    def run(self):
        self.clog.logt("Starting Coreloop backend\n")
        self.thread = threading.Thread (target = self.exec_thread, daemon = True)        
        self.thread.start()    
