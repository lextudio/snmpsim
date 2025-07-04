#
# This file is part of snmpsim software.
#
# Copyright (c) 2010-2019, Ilya Etingof <etingof@gmail.com>
# License: https://www.pysnmp.com/snmpsim/license.html
#
import asyncio
import importlib
import sys
import threading

import pysnmp
import pysmi
import pyasn1
import snmpsim

TITLE = """\
SNMP Simulator version {}, written by Ilya Etingof <etingof@gmail.com>
Using foundation libraries: pysmi {}, pysnmp {}, pyasn1 {}.
Python interpreter: {}
Documentation and support at https://www.pysnmp.com/snmpsim
""".format(
    snmpsim.__version__,
    pysmi.__version__,
    pysnmp.__version__,
    pyasn1.__version__,
    sys.version,
)


def try_load(module, package=None):
    """Try to load given module, return `None` on failure"""
    try:
        return importlib.import_module(module, package)

    except ImportError:
        return


def split(val, sep):
    """Split a string into a list based on a separator"""
    for x in (3, 2, 1):
        if val.find(sep * x) != -1:
            return val.split(sep * x)

    return [val]


def run_in_new_loop(coroutine):
    """Run a coroutine in a new event loop"""

    def run():
        new_loop = asyncio.new_event_loop()
        new_loop.run_until_complete(coroutine)

    thread = threading.Thread(target=run)
    thread.start()
    thread.join()


def run_in_loop_with_return(coroutine):
    """Run a coroutine in a new event loop"""
    def run():
        event_loop = asyncio.new_event_loop()
        return event_loop.run_until_complete(coroutine)

    thread = ThreadWithReturnValue(target=run)
    thread.start()
    return thread.join()


class ThreadWithReturnValue(threading.Thread):
    """Subclass thread to access return value from join."""
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        threading.Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args, **self._kwargs)

    def join(self, *args):
        threading.Thread.join(self, *args)
        return self._return
