#ifndef SPECTROMETER_INTERFACE_H
#define SPECTROMETER_INTERFACE_H

#include <stdbool.h>
#include <stdint.h>




#define NCHANNELS 2048
#define NSPECTRA 16
#define NINPUT 4


struct ADC_stat {
    int16_t min, max;
    uint32_t valid_count, invalid_count_max, invalid_count_min;
    int32_t mean;
    uint64_t var;
}__attribute__((packed));




void spectrometer_init();

void spec_set_Navg1(uint32_t Navg1);
void spec_set_spectrometer_enable(bool on);


// RFS_SET_RESET  Reset default configuration (system configuration as after boot)
void spec_set_reset();

// RFS_SET_STORE Stores current configuration
void spec_store();

// RFS_SET_RECALL  Recalls configuration from previous store 
void spec_recall();

// set gain of channel ch to gain
void spec_set_gain(uint8_t ch, uint8_t gain);

// get Temmperature and Voltage Telemetry
void spec_get_TVS(uint16_t *TVS);

// set auto and cross-correlation bit-slices for 16 products
void spec_set_bitslice (uint8_t* slice);

// enable or disable notch filter
// 0 = disable, 1 = x4, 2 = x16, 3=x64, 4=x256
void spec_notch_enable (uint8_t arg);

// get overflow bitmasks for wf, 16 correlation channels and their notch counter-parts (MSB)
void spec_get_digital_overflow (uint16_t* corr_owf, uint16_t *notch_owf);


// set routing of channel ch to plus - minus.  plus = 0..3, minus = 0..3 or FF for ground
void spec_set_route(uint8_t ch, uint8_t plus, uint8_t minus);

// set the number of shift bits for Stage 1 averageing (ie. Navg1_shift =10 ->  Navg1 = 1024)
void spec_set_avg1 (uint8_t Navg1_shift);

// fires up the ADC statistic engine
void spec_trigger_ADC_stat(uint16_t Nsamples); 
// If we have ADC results, return true and get ADC level statistics into 4 element array in order to enable automatic gain, etc
bool spec_get_ADC_stat(struct ADC_stat *stat);

// get spacecraft time as per commands RFS_SCM_F1-F3
void spec_get_time(uint32_t *time_sec, uint16_t *time_subsec);


//returns true if a new spectrum is ready (DF flag is set)
bool spec_new_spectrum_ready();

// clears the DF flag
void spec_clear_df_flag();




#endif
