#
# Generic interface for the AWG backends
#

class AWGBackendBase:
    def __init__ (self):
        pass

    
    def tone (self, ch, freq, amplitude):
        # ch is 0-4
        # freq is in MHz
        # amplitude is in mVPP
        pass
    
    def process_command(self, command):
        command = command.split()
        if command[0]=='TONE':
            ch = int(command[1])
            freq = float(command[2])
            amplitude = float(command[3])
            self.tone(ch, freq, amplitude)
        elif command[0] == 'CAL':
            if command[1] == 'ON':
                alpha = float(command[2])
                self.cal_on(alpha)
            elif command[1] == 'OFF':
                self.cal_off()
            else:
                print ("AWG Unknown CAL command:", command)                
        elif command[0]=='STOP':
            self.stop()
        elif command[0]=='INIT':
            pass
        else:
            print ("AWG Unknown command:", command)
        
    def stop(self):
        pass



    

