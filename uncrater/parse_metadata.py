import struct



def parse_metadata(binary_blob):
    """Parse the metadata from the binary blob.

    Args:
        binary_blob (bytes): The binary blob containing the metadata.

    Returns:
        dict: The metadata.
    """
    metadata = {}
    ## Sequencer state, defined in core_loop.h
    """"
    struct sequencer_state {
    uint8_t gain [NINPUT]; // this defines the commanded gain state (can be auto)
    uint16_t gain_auto_min[NINPUT];   
    uint16_t gain_auto_mult[NINPUT];
    struct route_state route[NINPUT];
    uint8_t Navg1_shift, Navg2_shift;   // Stage1 (FW) and Stage2 (uC) averaging
    uint8_t Navgf; // frequency averaging
    uint8_t format;
    };
    """
    
    seq_state = '4B 4H 4H 2B 2B 2B 2B B B B B'
    
    ## ADC state, defined in spectrometer_interface.h
    """
    struct ADC_stat {
    uint32_t invalid_count;
    int32_t min;
    int32_t max;
    uint32_t mean;
    uint64_t var;
    };    
    """
    adc_state = 'I i i I Q'
    
    """"
    struct core_state_base {
    uint8_t actual_gain[NINPUT]; // this defines the actual gain state (can only be low, med, high);
    uint32_t errors;
    uint32_t time_seconds;
    uint16_t time_subseconds;
    struct ADC_stat ADC_stat[4];    
    bool spectrometer_enable;
    uint8_t sequencer_counter; // number of total cycles in the sequencer.
    uint8_t sequencer_step; // 0xFF is sequencer is disabled
    uint8_t sequencer_substep; // counting seq_times;
    uint16_t sequencer_repeat; // number of sequencer repeats remaining, 00 for infinite (RFS_SET_SEQ_REP)
    };
    """
    core_state_base = '4B I I H '+4*adc_state+ 'B B B B H'

    """
    
    // metadata payload, compatible with core_state
    struct meta_data {
    uint16_t metadata_version; 
    uint32_t unique_packet_id;
    struct sequencer_state seq;
    struct core_state_base base;
    };
    """
    meta_data = '<H I '+seq_state+' '+core_state_base
    
    print (len(binary_blob), struct.calcsize(seq_state), struct.calcsize(core_state_base), struct.calcsize(meta_data))
    values = struct.unpack(meta_data, binary_blob)
    print (binary_blob[:10])
    print (values[:10])
    metadata['metadata_version'] = values[0]
    metadata['unique_packet_id'] = values[1]
    metadata['seq'] = {}
    metadata['seq']['gain'] = values[2:6]
    metadata['seq']['gain_auto_min'] = values[6:10]
    metadata['seq']['gain_auto_mult'] = values[10:14]
    metadata['seq']['route'] = [(values[14],values[15]),(values[16],values[17]),(values[18],values[19]),(values[20],values[21])]
    metadata['seq']['Navg1_shift'] = values[22]
    metadata['seq']['Navg2_shift'] = values[23]
    metadata['seq']['Navgf'] = values[24]
    metadata['seq']['format'] = values[25]
    metadata['base'] = {}
    metadata['base']['actual_gain'] = values[26:30]
    metadata['base']['errors'] = values[30]
    metadata['base']['time_seconds'] = values[31]
    metadata['base']['time_subseconds'] = values[32]
    metadata['base']['ADC_stat'] = []
    for i in range(33,53,5):
        metadata['base']['ADC_stat'].append(dict(zip(['invalid_count', 'min', 'max', 'mean', 'var'], values[i:i+5])))
    metadata['base']['spectrometer_enable'] = values[53]
    metadata['base']['sequencer_counter'] = values[54]
    metadata['base']['sequencer_step'] = values[55]
    metadata['base']['sequencer_substep'] = values[56]
    metadata['base']['sequencer_repeat'] = values[57]

    assert (metadata['metadata_version'] == 1)
    return metadata
