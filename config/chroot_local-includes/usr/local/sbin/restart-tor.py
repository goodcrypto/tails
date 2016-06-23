#! /usr/bin/python3
'''
    Restart Tor.

    Test with "python3 tor_browser.py doctest".

    goodcrypto.com converted from bash to python and added basic tests.
'''
import os
import sys

import sh

from tailslib.common import clock_gettime_monotonic, try_for
from tailslib.log import log
from tailslib.tor import tor_bootstrap_progress, TOR_LOG

os.environ['PATH'] = '/usr/sbin:/usr/local/bin:/usr/bin:/bin'

_LOG_TAG = os.path.basename(sys.argv[0])

bootstrap_progress = 0
last_bootstrap_change = clock_gettime_monotonic()

def main():
    """
        The main point of this script is to restart Tor
        if bootstrapping stalls for more than 20 seconds

        >>> main()
        >>> tor_bootstrap_progress() == 100
        True
    """
    clear_tor_log()
    restart_tor_service()

    try_for(270, [maybe_restart_tor])

def clear_tor_log():
    """
        The Tor log is removed to ensure
        tor_bootstrap_progress's output will be accurate.

        >>> clear_tor_log()
        >>> os.path.exists(TOR_LOG)
        False
    """

    if os.path.exists(TOR_LOG):
       os.remove(TOR_LOG)

def restart_tor_service():
    """
        Restart Tor service.

        >>> restart_tor_service()
    """

    sh.systemctl('restart', 'tor@default.service')
    log("Started Tor.")

def maybe_restart_tor():
    """
        Restart Tor service if bootstrapping stalls for more than 20 seconds.

        >>> maybe_restart_tor()
        0
    """
    global bootstrap_progress, last_bootstrap_change
    result = 1

    new_bootstrap_progress = tor_bootstrap_progress()
    if new_bootstrap_progress == 100:
        log("Tor has successfully bootstrapped.")
        result = 0

    elif new_bootstrap_progress > bootstrap_progress:
        bootstrap_progress = new_bootstrap_progress
        last_bootstrap_change = clock_gettime_monotonic()
        result = 1

    elif (clock_gettime_monotonic() - last_bootstrap_change) > 20:
        log("Tor seems to have stalled while bootstrapping. Restarting Tor.")
        clear_tor_log()
        restart_tor_service()
        bootstrap_progress = 0
        last_bootstrap_change = clock_gettime_monotonic()
        result = 1

    else:
        result = 1

    return result


'''
    >>> # run script
    >>> this_command = sh.Command(sys.argv[0])
    >>> this_command()
    <BLANKLINE>
'''
if __name__ == "__main__":
    if sys.argv and len(sys.argv) > 1:
        if sys.argv[1] == 'doctest':
            from doctest import testmod
            testmod()
        else:
            main(sys.argv)
    else:
        main()
