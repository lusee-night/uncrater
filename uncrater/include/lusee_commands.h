
#ifndef LUSEE_SETTINGS_H
#define LUSEE_SETTINGS_H

// Master mode command for which everything below applies.
#define RFS_Settings 0x10

// wait mode - disable data taking
#define RFS_SET_STOP  0x00 

// Start data acquisition. To start anything setup by 0x1x or 0x2x
#define RFS_SET_START  0x01 

// Soft reset, restores default configuration (as after boot)
#define RFS_SET_RESET  0x02 

// Stores current configuration
#define RFS_SET_STORE  0x03 

// Recalls configuration from previous store
#define RFS_SET_RECALL  0x04 

// Return housekeeping data, ARG = 0 -- full housekeeping; ARG = 1 ADC statistics;
#define RFS_SET_HK_REQ  0x05 

// Set ADC mode: 0 ADC disabled, 1 ADC enabled
#define RFS_SET_ADC  0x06 

// Autorange ADC and then set an ADC packet
#define RFS_SET_RANGE_ADC  0x07 

// prepare for power cut -- mode announcing power cut 5 seconds after issue
#define RFS_SET_TIME_TO_DIE  0x0F 

// Test modes stored internally, by number in argument
#define RFS_SET_TEST  0x10 

// Science modes stored internally, by number in argument
#define RFS_SET_SCIENCE  0x11 

// Load sequencer mode from flash
#define RFS_SET_LOAD_FL  0x12 

// Store sequencer mode into flash
#define RFS_SET_STORE_FL  0x13 

// set analog gains, DD is 4x2 bits for for channels, each 2 bits encodeds L, M, H, A
#define RFS_SET_GAIN_ANA_SET  0x30 

// automatic analog gains setting, min ADC. Low 2 bits are channels, remaming bits will be multiplied by 16 (1024 max val)
#define RFS_SET_GAIN_ANA_CFG_MIN  0x31 

// automatic analog gains setting, max ADC = min ADC  * mult. Low 2 bits are channels, remaming bits are multiplier.
#define RFS_SET_GAIN_ANA_CFG_MULT  0x32 

// Sets manual bitslicing for XCOR 1-8 (3 LSB bits) to values 1-32 (5 MSB bits)
#define RFS_SET_BITSLICE_LOW  0x33 

// Sets manual bitslicing for XCOR 9-16 (3 LSB bits) to values 1-32 (5 MSB bits)
#define RFS_SET_BITSLICE_HIGH  0x34 

// Uses automatic bitslicing, 0 disables, positive number sets number of SB for lowest product
#define RFS_SET_BITSLICE_AUTO  0x35 

// set routing for ADC channels 1 and 2, 4 DD bits each. First two bits are antenna1 number, second two bits are antenna2 number. If antenna1==antenna2, we are subtracting from the ground. I.e. 1101 meand A4-A2. 0101 menas A2-gronud.
#define RFS_SET_ROUTE_SET12  0x40 

// same as 0x40 but for ADC channels 3 and 4
#define RFS_SET_ROUTE_SET34  0x41 

// set averaging bit shifts. Lower 4 bits of DD is for Stage1 averager, higher 4 bits is for Stage2 averager. So B9 means 2^9 stage1 averaging and 2^11 stage2 averaging
#define RFS_SET_AVG_SET  0x50 

// set outlier rejectection. DD specifies the level of rejection with 00 disabled and 10 standard outlier rejection.
#define RFS_SET_AVG_OUTLIER  0x51 

// set frequency averaging. Valid values are 01, 02, 03, 04. If 03 it averages by 4 ignoring every 4th (presumably PF infected)
#define RFS_SET_AVG_FREQ  0x52 

// set notch averaging, 0 = disabled, 1=x4, 2=x16, 3=x64, 4=x256
#define RFS_SET_AVG_NOTCH  0x53 

// set high priority fraction as a fraction DD/FF, low priorty = 1-high-medium
#define RFS_SET_AVG_SET_HI  0x54 

// set medium priority fraction, low priority is 1-high-medium
#define RFS_SET_AVGI_SET_MID  0x55 

// set the output format: 0 - full 32 bits resolution; 1 4+16 bits with update packets
#define RFS_SET_OUTPUT_FORMAT  0x56 

// set averaging fractions for calibration signal acquisition. Same as 0x50, but note that not all values are valid
#define RFS_SET_CAL_FRAC_SET  0x60 

// set max drift guard in units of 0.1ppm
#define RFS_SET_CAL_MAX_SET  0x61 

// set lock drift guard in units of 0.01ppm
#define RFS_SET_CAL_LOCK_SET  0x62 

// set snr required for lock
#define RFS_SET_CAL_SNR_SET  0x63 

// set starting bin (/(2*4))
#define RFS_SET_CAL_BIN_ST  0x64 

// set end bin (/(2*4))
#define RFS_SET_CAL_BIN_EN  0x65 

// set antenna mask as the lower 4 bits. 0x00001111 = all antennas enabled
#define RFS_SET_CAL_ANT_MASK  0x66 

// enable zoom channel
#define RFS_SET_ZOOM_EN  0x70 

// set zoom 1 input channel
#define RFS_SET_ZOOM_SET1  0x71 

// set zoom 1 spectral channel low bits
#define RFS_SET_ZOOM_SET1_LO  0x72 

// set zoom 1 spectral channel high bits
#define RFS_SET_ZOOM_SET1_HI  0x73 

// set zoom 2 input channel
#define RFS_SET_ZOOM_SET2  0x74 

// set zoom 2 spectral channel# low bits
#define RFS_SET_ZOOM_SET2_LO  0x75 

// set zoom 2 spectral channel# high bits
#define RFS_SET_ZOOM_SET2_HI  0x76 

// enable (DD>0), disable sequencer  (DD=0)
#define RFS_SET_SEQ_EN  0xA0 

// set number of of cycle repetitions, 00 for infinite repetitions
#define RFS_SET_SEQ_REP  0xA1 

// set number of elements in a cycle, restart save counter
#define RFS_SET_SEQ_CYC  0xA2 

// store current configuration, as the next cycle. Store configuration includes settings under 0x30, 0x31, 0x32, 0x33, 0x40, 0x41, 0x50, 0x51, 0x52. DD means the number of integrations under this cycle
#define RFS_SET_SEQ_STO  0xA3 



#endif