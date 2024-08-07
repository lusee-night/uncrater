import os

class BackendBase:

    def __init__(self, clog, uart_log, session):
        self.clog = clog
        self.uart_log = uart_log
        self.session = session
        self.out_dir = os.path.join(session,'cdi_output')
        self.packet_count = 0




    def save_data(self, appid, data):
        fname = os.path.join(self.out_dir,f"{self.packet_count:05d}_{appid:04x}.bin")        
        f=open(fname,'wb')
        f.write(data) 
        f.close()
        self.clog.logt(f"Stored AppID {hex(appid)} len={len(data)}\n")    
        self.packet_count += 1
        
    