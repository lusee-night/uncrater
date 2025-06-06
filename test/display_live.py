import numpy as np
import argparse
import time
import matplotlib.pyplot as plt




def main():
    parser = argparse.ArgumentParser(description="Display live data.")
    parser.add_argument(
        "-t", "--terminal-only",
        action="store_true",
        default=False,
        help="Run in terminal-only mode (no GUI display)."
    )
    args = parser.parse_args()
    terminal_only = args.terminal_only

    run(terminal_only)


def run(terminal_only):


    if not terminal_only:
        if 'fivethirtyeight' in plt.style.available:
            plt.style.use('fivethirtyeight')

        plt.rcParams.update({'font.size': 10, 'figure.figsize': (10, 8)})

        fig, axs = plt.subplots(2, 2, figsize=(10, 8))
        x = np.linspace(0, 2 * np.pi, 100)
        lines = []

        for i, ax in enumerate(axs.flat):
            line, = ax.plot(x, np.sin(x))
            ax.set_ylim(-1.5, 1.5)
            lines.append(line)
            ax.set_title(f"CH {i}")

        plt.tight_layout()
        plt.ion()
        plt.show()

        phase = 0
        while True:
            for line in lines:
                line.set_ydata(np.sin(x + phase))
            phase += 0.2
            fig.canvas.draw()
            fig.canvas.flush_events()
            time.sleep(1)
    else:
        print("Terminal-only mode: live plot not displayed.")




if __name__ == "__main__":
    main()