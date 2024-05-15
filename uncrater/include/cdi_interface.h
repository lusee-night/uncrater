#ifndef CDI_INTERFACE_H
#define CDI_INTERFACE_H

#include <stdbool.h>
#include <stdint.h>
#include "LuSEE_IO.h"

#define CMD_uC_RD_ADDR       0x202     //  0x202  R/W  bit 0
#define CMD_uC_OUT_ADDR      0x203     //  0x203  R    bits 23..0
#define CMD_uC_RDY_ADDR      0x203     //  0x203  R    bit 31

#define PKT_GEN_BUSY         0x21A
#define START_TLM_DATA       0x218
#define CDI_REG              0x219
#define CDI_SRC_SEL          0x21F


void cdi_init();
// returns true if a new command is available, and sets the command and arguments
bool cdi_new_command(uint8_t *cmd, uint8_t *arg_high, uint8_t *arg_low );

// returns true if the CDI is ready to accept new data  (i.e. write to staging area and dispatching it)
bool cdi_ready();

// waits until CDI buffers is ready to be written.
void wait_for_cdi_ready();
// dispatches the CDI data packet of a given size with the right appID
// AS : add message type (0x20 - 0x27)
void cdi_dispatch (uint16_t appID, uint32_t length);



#endif
