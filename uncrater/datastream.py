from .spectrum import Spectrum
from .parse_metadata import parse_metadata
from .parse_spectrum import parse_spectrum

import sqlite3



def dict2sql_columns(di):
    dtypes = {int: 'INTEGER',float: 'REAL', str: 'TEXT'}
    toret = []
    for key,val in di.items():
        if type(val)==dict:
            for (skey, stype,sval) in dict2sql_columns(val):
                toret.append((f'{key}_{skey}',stype,sval))
        elif type(val)==list:
            td={}
            for i,sval in enumerate(val):
                td[f'{i+1}']=sval
            for (skey, stype,sval) in dict2sql_columns(td):
                toret.append((f'{key}_{skey}',stype,sval))
        elif type(val)==tuple:
            toret.append((key, 'TEXT',' '.join(map(str,val))))
        else:
            toret.append((key, dtypes[type(val)],val))
    return toret


class DataStream:
    def __init__ (self, database_name = 'database/uncrater.db'):
        self.data = []
        self.conn = sqlite3.connect(database_name)
        self.curs = self.conn.cursor()
        self.have_metadata_table = False
        self.have_data_table = False


    def process(self, appid, binary_blob):
        if appid == 0x020F:
            metadata = parse_metadata(binary_blob)
            spectrum = Spectrum(metadata)
            self.data.append(spectrum)
            self.current_unique_packet_id = metadata['unique_packet_id']
            self.current_format = metadata['seq']['format']
            sqldata = dict2sql_columns(metadata)
            if not self.have_metadata_table:
                columns = ', '.join([f'{key} {sqltype}' for key, sqltype,_ in sqldata])
                print (columns)
                
                query = f"CREATE TABLE IF NOT EXISTS metadata ({columns})"
                self.curs.execute(query)
                self.have_metadata_table = True
            columns = ', '.join([key for key, _,_ in sqldata])
            values = ', '.join([f"'{val}'" for _, _, val in sqldata])
            query = f"INSERT OR REPLACE INTO metadata (unique_packet_id, {columns}) VALUES ({metadata['unique_packet_id']}, {values})"
            self.curs.execute(query)

        elif appid >=0x0210 and appid <= 0x021F:
            spectrum = parse_spectrum(binary_blob, self.current_format, self.current_unique_packet_id)    
            ch = appid-0x0210
            self.data[-1].data[ch] = spectrum
            if not self.have_data_table:
                columns = ', '.join([f'SPECTRUM_{i+1}' for i in range(16)])
                query = f"CREATE TABLE IF NOT EXISTS data (unique_packet_id INTEGER, {columns})"
                self.curs.execute(query)
                self.have_data_table = True
            column = f'SPECTRUM_{ch+1}'
            values = '"'+' '.join([f"'{val}'" for val in spectrum])+'"'
            query = f"INSERT OR REPLACE INTO data (unique_packet_id, {column}) VALUES ({self.current_unique_packet_id}, {values})"
            self.curs.execute(query)
        else:
            raise ValueError("Unknown appid")
        
    def __del__(self):
        self.conn.commit()
        self.conn.close()
        


