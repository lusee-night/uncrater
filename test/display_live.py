import sys
sys.path.append(".")

import numpy as np
import argparse
import time
import uncrater as uc
import yaml



def main():
    parser = argparse.ArgumentParser(description="Display live data.")
    parser.add_argument(
        "-t", "--terminal-only",
        action="store_true",
        default=False,
        help="Run in terminal-only mode (no GUI display)."
    )
    parser.add_argument(
        "-N", "--npoints",
        type=int,
        default=20,
        help="Number of points to display (default: 20)."
    )
    args = parser.parse_args()

    run(args)


def get_adc_data(C):
    """ Get ADC data from the collection C """
    adc_min, adc_max, adc_mean, adc_rms = [], [], [], []
    for packet in C.cont:
        if hasattr(packet, "base") and hasattr(packet.base, "housekeeping_type") and (packet.base.housekeeping_type == 1):
            adc_min.append(packet.min)
            adc_max.append(packet.max)
            adc_mean.append(packet.mean)
            adc_rms.append(packet.rms)

    return np.array(adc_min), np.array(adc_max), np.array(adc_mean), np.array(adc_rms)


def endline(data, npoints):
    """ Ensure the data is of length npoints, filling with zeros if necessary """
    if len(data) < npoints:
        return np.concatenate((data, np.zeros(npoints - len(data))))
    else:
        return data[-npoints:]  # Return the last npoints if data is longer

def run(args):
    terminal_only = args.terminal_only
    npoints = args.npoints


    options_path = "session_live/options.yaml"
    with open(options_path, "r") as f:
        options = yaml.safe_load(f)
    mode = options.get("mode")
    print(f"Mode from options.yaml: {mode}")
    adc = (mode== "adc")
    C = uc.Collection("session_live/cdi_output")


    if not terminal_only:
        import matplotlib.pyplot as plt
        if 'fivethirtyeight' in plt.style.available:
            plt.style.use('fivethirtyeight')

        plt.rcParams.update({'font.size': 10, 'figure.figsize': (10, 8)})

        fig, axs = plt.subplots(2, 2, figsize=(10, 8))

        lines = []

        if (adc):
            for i, ax in enumerate(axs.flat):
                x=np.arange(npoints)
                vals = np.zeros(npoints)

                line_max, = ax.plot(x, vals, 'k-', lw=1, label='max')
                line_min, = ax.plot(x, vals, 'k--', lw=1,  label='-min')
                line_rms, = ax.plot(x, vals, 'r-', lw=2, label=' 3 x rms')
                ax.set_ylim(0, 200)
                lines.append((line_max, line_min, line_rms))
                ax.set_title(f"CH {i}")
            axs[0][0].legend()
        else:
            for i, ax in enumerate(axs.flat):
                x = np.arange(2048)*0.025
                vals = np.zeros(2048)
                imin = 10
                linepp, = ax.plot(x[imin:], vals[imin:], color='gray', lw=1, label='last-2 ')
                linep, = ax.plot(x[imin:], vals[imin:], 'k-', lw=1,  label='last-1')
                line, = ax.plot(x[imin:], vals[imin:], 'r-', lw=2, label=' last')
                ax.set_ylim(10, 1e6)
                ax.set_yscale('log')
                lines.append((linepp, linep, line))
                ax.set_title(f"CH {i}")
                if (i>1):
                    ax.set_xlabel("frequency (MHz)")

            axs[0][0].legend()


        plt.tight_layout()
        plt.ion()
        plt.show()



    while True:
        try:
        #print ('refreshing')
            C.refresh(quiet=False)
        except: 
            pass
        if (adc):
            adc_min, adc_max, adc_mean, adc_rms = get_adc_data (C)
            if len(adc_min) == 0:                
                time.sleep(1)
                continue
            if not terminal_only:
                for i, (line,ax) in enumerate(zip(lines,axs.flat)):
                    xmin = len(adc_max)-npoints
                    if xmin < 0:
                        xmin = 0
                    xar = np.arange(xmin, xmin+npoints)

                    line[0].set_xdata(xar)
                    line[1].set_xdata(xar)
                    line[2].set_xdata(xar)

                    line[0].set_ydata(endline(adc_max[:,i],npoints))
                    line[1].set_ydata(endline(-adc_min[:,i],npoints))
                    line[2].set_ydata(endline(adc_rms[:,i],npoints)*3)
                    ylim = ax.get_ylim()
                    wmax= np.max(np.hstack((adc_max[:,i], -adc_min[:,i]))) * 1.1
                    if ylim[1] < wmax:
                        ax.set_ylim(0, wmax)
                    ax.set_xlim(xmin, xmin+npoints-1)
                    ax.set_xticks(xar[::4])

                fig.canvas.draw()
                fig.canvas.flush_events()
            else:                                
                print(f"RMS: {adc_rms[-1]}")
        else:
            spectra = C.spectra
            if len(spectra) == 0:
                time.sleep(1)
                continue
            if 3 not in spectra[-1]:
                # just refresh asap to get the last spectra
                continue

            if not terminal_only:
                for i, (line,ax) in enumerate(zip(lines,axs.flat)):
                   if len(spectra)>2:                        
                        line[0].set_ydata(spectra[-3][i].data[imin:])                                            
                   if len(spectra)>1:                        
                        line[1].set_ydata(spectra[-2][i].data[imin:])                                           
                   ldata = spectra[-1][i].data[imin:]
                   line[2].set_ydata(ldata)                    
                   wmax= np.max(ldata) * 1.5
                   ylim = ax.get_ylim()
                   if ylim[1] < wmax:
                       ax.set_ylim(10, wmax)
                fig.canvas.draw()
                fig.canvas.flush_events()
            else:
                last = spectra[-1]
                pwr = [last[i].data[160:240].mean() for i in range(4)]
                print(f"Last spectra, PWR 4-6 MHz: {pwr[0]:.2f} {pwr[1]:.2f} {pwr[2]:.2f} {pwr[3]:.2f}")
            
        time.sleep(1)


if __name__ == "__main__":
    main()
