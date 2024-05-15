#ifndef CORELOOP_ERRORS_H
#define CORELOOP_ERRORS_H


// unknown CDI command received
#define CDI_COMMAND_UNKNOWN 1
// CDI command called at wrong time ((i.e. program sequencer while it is running)
#define CDI_COMMAND_BAD 2
// CDI command called with wrong arguments
#define CDI_COMMAND_BAD_ARGS 4
// Cannot autogain
#define ANALOG_AGC_TOO_HIGH 8
#define ANALOG_AGC_TOO_LOW 16

#define ANALOG_AGC_ACTION_CH1 32
#define ANALOG_AGC_ACTION_CH2 64
#define ANALOG_AGC_ACTION_CH3 128
#define ANALOG_AGC_ACTION_CH4 256




#endif