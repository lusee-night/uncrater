
#ifndef LUSEE_APPIDS_H
#define LUSEE_APPIDS_H

// RFS register read back; Priority:  High     
#define AppID Read Response 0x0200

// RFS watchdog is requesting a reset + metadata; Priority:  High     
#define AppID_Reset_Request 0x0201

// Dumps all register values from the RFS into packet; Priority:  High     
#define AppID_Registers_RB 0x0205

// uC generater housekeeping; Priority:  High     
#define AppID_uC_Housekeeping 0x0206

// Calibrator detected with meta data; Priority:  High     
#define AppID_Calibrator_Detect 0x0207

// Data from the bootloader; Priority:  High     
#define AppID_uC_Bootloader 0x0208

// Flight SW has booted; Priority:  High     
#define AppID_uC_Start 0x0209

// HeartBeat; Priority:  None     
#define AppID_uC_HeartBeat 0x020A

// For sequencer with a limited number of steps; Priority:  High     
#define AppID_uC_Sequencer_complete 0x020B

// x = 0..F for 16 correlations; Priority:  High     
#define AppID_MetaData 0x020F

// Main correlation products, high priorty; Priority:  High     
#define AppID_SpectraHigh 0x0210

// Main correlation products, medium priority; Priority:  Med      
#define AppID_SpectraMed 0x0220

// Main correlation products, low priority; Priority:  Low      
#define AppID_SpectraLow 0x0230

// Rejected spectra, high priority; Priority:  High     
#define AppID_SpectraRejectHigh 0x0240

// Rejected spectra, medium priority; Priority:  Med      
#define AppID_SpectraRejectMed 0x0250

// Rejected Spectra, low priority; Priority:  Low      
#define AppID_SpectraRejectLow 0x0260

// Spectral zoom-in spectra; Priority:  High     
#define AppID_ZoomSpectra 0x0270

// Time zoom-in spectra; Priority:  High     
#define AppID_TimeZoomSpectra 0x0280

// Calibrator data; Priority:  High     
#define AppID_Calibrator_Data 0x0290

// Very low priority, not expected to be normally downloaded; Priority:  VeryLow  
#define AppID_SpectraVeryLow 0x02D0

// x= 0...4 for 4 autocorrelatins; Priority:  High     
#define AppID_FW_DirectSpectrum 0x02E0

// x= 0..4 for 4 raw ADC data streams; Priority:  High     
#define AppID_RawADC 0x02F0



#endif