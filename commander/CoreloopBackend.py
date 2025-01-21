from BackendBase import BackendBase
import os
import threading
import socket
import subprocess
import sys
import time
import glob 

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
        self.stop_threads = False

    def send_command(self, cmd, arg):
        b=bytearray(4)
        b[0] = ord('C')
        b[1] = cmd
        b[2]=(arg&0xFF00)>>8
        b[3]=(arg&0x00FF)
        self.sockout.sendto(b, ('localhost', self.port))

    def cdi_output_dir(self):
        return os.path.join(self.session, 'cdi_output')

    def exec_thread(self):
        self.clog.logt("Executing Coreloop\n")
        options = f"-m port -o {self.cdi_output_dir()}"
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

    def exec_poll_thread(self):
        npackets = 0
        glb = self.cdi_output_dir()+"/*.bin"
        while not self.stop_threads:
            files = sorted(glob.glob(glb))
            if len(files)>npackets:
                for f in files[npackets:]:
                    appid = int(f[f.rfind('_')+1:f.rfind('.bin')],16)
                    print (f"New CDI packet with AppID =  {appid:x}")
                    self.clog.logt(f"New packet received, appid={appid:x}")
                    blob = open(f,'rb').read()
                    self.inspect_packet(appid, blob)
                npackets = len(files)
            time.sleep(0.5)

        

    def stop(self):
        self.stop_threads = True
        self.process.terminate()
        self.sockout.close()
        self.thread.join()
        self.poll_thread.join()


    def run(self):
        self.clog.logt("Starting Coreloop backend\n")
        self.thread = threading.Thread (target = self.exec_thread, daemon = True)  
        self.poll_thread  = threading.Thread(target = self.exec_poll_thread, daemon = True)      
        self.thread.start()    
        self.poll_thread.start()