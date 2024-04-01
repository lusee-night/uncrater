from .spectrum import Spectrum
from .parse_metadata import parse_metadata
from .parse_spectrum import parse_spectrum

class DataStream:
    def __init__ (self):
        self.data = []

    def process(self, appid, binary_blob):
        if appid == 0x020F:
            metadata = parse_metadata(binary_blob)
            spectrum = Spectrum(metadata)
            self.data.append(spectrum)
            self.current_unique_packet_id = metadata['unique_packet_id']
            self.current_format = metadata['seq']['format']

        elif appid >=0x0210 and appid <= 0x021F:
            spectrum = parse_spectrum(binary_blob, self.current_format, self.current_unique_packet_id)    
            self.data[-1].data[appid-0x0210] = spectrum
        else:
            raise ValueError("Unknown appid")
        



