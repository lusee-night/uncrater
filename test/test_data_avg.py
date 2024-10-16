import os
import shutil
import sys
import numpy as np
import scipy as sp
import typing
from icecream import ic

sys.path.append('.')
sys.path.append('./scripter/')
sys.path.append('./commander/')

if os.environ.get('CORELOOP_DIR') is not None:
    sys.path.append(os.environ.get('CORELOOP_DIR'))

from test_base import Test
from lusee_script import Scripter
from commander import Commander
import uncrater as uc
from collections import defaultdict

from pycoreloop import appId



def generate_script(avg_freq, navg_shift):
    time = 10
    scripter = Scripter()
    scripter.start()
    scripter.set_Navg(navg_shift, navg_shift)
    scripter.set_avg_freq(avg_freq)
    scripter.wait(time)
    scripter.stop()
    return scripter


def get_workdir(avg_freq):
    # recreate workdir and return its name
    result = os.path.join(".", f"session_avg_freq_{avg_freq}")
    shutil.rmtree(result, ignore_errors=True)
    os.makedirs(result)
    return result


def get_packets(avg_freq: int, navg_shift: int, backend: str="coreloop") -> typing.List[np.ndarray]:
    assert(avg_freq in [1,2,3,4])
    s = generate_script(avg_freq, navg_shift=navg_shift)
    workdir = get_workdir(avg_freq)
    comm = Commander(session = workdir, script=s.script, backend=backend)
    comm.run()
    coll = uc.Collection(os.path.join(workdir,'cdi_output'))
    result = []
    for ps in coll.spectra:
        for k in ps:
            if k != 'meta':
                result.append(ps[k].data.astype(np.int64))
    return result


def test_navg_freq():
    navg_shift = 2
    navg = 2 ** navg_shift
    err_base = navg
    avgs_1 = get_packets(1, navg_shift)
    avgs_2 = get_packets(2, navg_shift)
    avgs_3 = get_packets(3, navg_shift)
    avgs_4 = get_packets(4, navg_shift)
    assert(len(avgs_1) == len(avgs_2) == len(avgs_3) == len(avgs_4))
    for avg_1, avg_2, avg_3, avg_4 in zip(avgs_1, avgs_2, avgs_3, avgs_4):
        # Do not use np.average here: conversion to float leads to loss of precision
        # and error becomes too large. We want to work with integers to control the error exactly.
        corr_sum_2 = np.sum(np.stack((avg_1[::2], avg_1[1::2])), axis=0)
        corr_sum_3 = np.sum(np.stack((avg_1[::4], avg_1[1::4], avg_1[2::4])), axis=0)
        corr_sum_4 = np.sum(np.stack((avg_1[::4], avg_1[1::4], avg_1[2::4], avg_1[3::4])), axis=0)

        assert(np.max(np.abs(2 * avg_2 - corr_sum_2)) <= 2 * err_base)
        assert(np.max(np.abs(4 * avg_3 - corr_sum_3)) <= 4 * err_base)
        assert(np.max(np.abs(4 * avg_4 - corr_sum_4)) <= 4 * err_base)


if __name__ == "__main__":
    test_navg_freq()
