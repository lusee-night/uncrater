#include <stddef.h>
#include <stdio.h>

#include "core_loop.h"

#define PRINT_TYPE(name)                                                       \
    printf("S\t" #name "\t%zu\t%zu\n", sizeof(struct name),                \
           _Alignof(struct name))
#define PRINT_FIELD(name, field)                                               \
    printf("F\t" #name "\t" #field "\t%zu\t%zu\n",                       \
           offsetof(struct name, field),                                      \
           sizeof(((struct name *)0)->field))

int main(void) {
    PRINT_TYPE(ADC_stat);
    PRINT_FIELD(ADC_stat, sumv);
    PRINT_FIELD(ADC_stat, sumv2);

    PRINT_TYPE(time_counters);
    PRINT_FIELD(time_counters, heartbeat_counter);
    PRINT_FIELD(time_counters, resettle_counter);
    PRINT_FIELD(time_counters, cdi_wait_counter);
    PRINT_FIELD(time_counters, cdi_dispatch_counter);

    PRINT_TYPE(core_state_base);
    PRINT_FIELD(core_state_base, uC_time);

    PRINT_TYPE(cdi_stats);
    PRINT_FIELD(cdi_stats, cdi_bytes_sent);

    PRINT_TYPE(startup_hello);
    PRINT_FIELD(startup_hello, SW_version);
    PRINT_FIELD(startup_hello, unique_packet_id);
    PRINT_FIELD(startup_hello, time_16);

    PRINT_TYPE(heartbeat);
    PRINT_FIELD(heartbeat, cdi_stats);
    PRINT_FIELD(heartbeat, magic);

    PRINT_TYPE(meta_data);
    PRINT_FIELD(meta_data, version);
    PRINT_FIELD(meta_data, unique_packet_id);
    PRINT_FIELD(meta_data, base);

    PRINT_TYPE(housekeeping_data_base);
    PRINT_FIELD(housekeeping_data_base, version);
    PRINT_FIELD(housekeeping_data_base, housekeeping_type);

    PRINT_TYPE(housekeeping_data_0);
    PRINT_FIELD(housekeeping_data_0, base);
    PRINT_FIELD(housekeeping_data_0, core_state);

    PRINT_TYPE(calibrator_metadata);
    PRINT_FIELD(calibrator_metadata, version);
    PRINT_FIELD(calibrator_metadata, unique_packet_id);
    PRINT_FIELD(calibrator_metadata, drift);

#if VERSION_ID >= 0x305
    PRINT_TYPE(waveform_metadata);
    PRINT_FIELD(waveform_metadata, timestamp);

    PRINT_TYPE(watchdog_packet);
    PRINT_FIELD(watchdog_packet, uC_time);

    PRINT_TYPE(housekeeping_data_2);
    PRINT_FIELD(housekeeping_data_2, heartbeat);

    PRINT_TYPE(housekeeping_data_3);
    PRINT_FIELD(housekeeping_data_3, weight_ndx);
#endif

    /* Early and final 0x306 share VERSION_ID, so the test selects by commit. */
#ifdef UNCRATER_FINAL_306_LAYOUT
    PRINT_TYPE(housekeeping_data_100);
    PRINT_FIELD(housekeeping_data_100, meta_valid);
    PRINT_TYPE(housekeeping_data_101);
    PRINT_FIELD(housekeeping_data_101, report);
#endif

    return 0;
}
