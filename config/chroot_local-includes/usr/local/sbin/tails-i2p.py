#! /usr/bin/python3
'''
    Start and stop I2P.

    Test with "python3 tails-tor-launcher.py doctest" as root.

    goodcrypto.com converted from bash to python and added basic tests.
'''
from gettext import gettext
import os
import sys
from time import sleep

import sh

from tailslib.common import set_default_locale, wait_until
from tailslib.i2p import (i2p_built_a_tunnel, i2p_reseed_failed, i2p_reseed_completed,
                          i2p_router_console_is_ready, set_best_i2p_router_console_lang)

os.environ['PATH'] = '/usr/sbin:/usr/local/bin:/usr/bin:/bin'
os.environ['TEXTDOMAIN'] = 'tails'

I2P_STARTUP_TIMEOUT=60

# When there are network problems (either local or remote), it can take up to 3
# minutes for all of the current reseed servers to be tried.
I2P_BOOTSTRAP_TIMEOUT=210

# After the router infos (RIs) are downloaded from the reseed servers
# it can take 3-5 minutes for a tunnel to be built, e.g.
# once we get to this point I2P should be ready to be used.
I2P_TUNNEL_BUILD_TIMEOUT=300

TAILS_NOTIFY_USER = '/usr/local/sbin/tails-notify-user'


def main(action):
    """
        >>> main('start')
    """

    # Get LANG, since we may run this from an environment that
    # doesn't have it set.
    set_default_locale()

    if action == 'start' or action == 'restart':
        # Stop I2P before setting the router console language in case
        # it pushes any updated options on quit.
        if sh.systemctl('--quiet', 'is-active', 'i2p', _ok_code=[0,1,3]):
            sh.systemctl('stop', 'i2p', _ok_code=[0,1,3])

        set_best_i2p_router_console_lang()
        sh.systemctl('start', 'i2p', _ok_code=[0,1,3])
        wait_until_i2p_router_console_is_ready() or startup_failure()
        notify_router_console_success()
        wait_until_i2p_has_bootstrapped() or bootstrap_failure()
        wait_until_i2p_builds_a_tunnel() or bootstrap_failure()
        notify_bootstrap_success()

    elif action == 'stop':
        sh.systemctl('stop', 'i2p', _ok_code=[0,1,3])

    else:
        print('invalid argument "{}"'.format(action), file=sys.stderr)
        sys.exit(1)

def startup_failure():
    """
        >>> startup_failure()
        >>> sh.systemctl('--quiet', 'is-active', 'i2p', _ok_code=[3])
        <BLANKLINE>
    """
    notify_user = sh.Command(TAILS_NOTIFY_USER)
    notify_user(gettext("I2P failed to start"),
      gettext("Something went wrong when I2P was starting. Check the logs in /var/log/i2p for more information."))

    sh.service('i2p', 'dump', _ok_code=[0,1]) # generate a thread dump
    sleep(5) # Give thread dump ample time to complete
    sh.systemctl('stop', 'i2p', _ok_code=[0,1,3]) # clean up, just in case

def wait_until_i2p_router_console_is_ready():
    """
        >>> wait_until_i2p_router_console_is_ready()
    """
    wait_until(I2P_STARTUP_TIMEOUT, [i2p_router_console_is_ready])

def wait_until_i2p_has_bootstrapped():
    """
        Show how to use this program.

        >>> wait_until_i2p_has_bootstrapped()
    """
    wait_until(I2P_BOOTSTRAP_TIMEOUT, [i2p_reseed_completed])

def notify_router_console_success():
    """
        >>> notify_router_console_success()
    """
    notify_user = sh.Command(TAILS_NOTIFY_USER)
    notify_user(gettext("I2P's router console is ready"),
                gettext("You can now access I2P's router console in the I2P Browser"))

def bootstrap_failure():
    """
        >>> try:
        ...    bootstrap_failure()
        ...    fail()
        ... except SystemExit:
        ...    pass
    """
    notify_user = sh.Command(TAILS_NOTIFY_USER)
    notify_user(gettext("I2P is not ready"),
      gettext("Eepsite tunnel not built within six minutes. Check the router console in the I2P Browser or the logs in /var/log/i2p for more information. Reconnect to the network to try again."))
    sys.exit(1)

def wait_until_i2p_builds_a_tunnel():
    """
        >>> wait_until_i2p_has_bootstrapped()
    """
    wait_until(I2P_TUNNEL_BUILD_TIMEOUT, [i2p_built_a_tunnel])
    # static sleep to work around upstream bug.
    sleep(240)

def notify_bootstrap_success():
    """
        Show how to use this program.

        >>> notify_bootstrap_success()
    """
    notify_user = sh.Command(TAILS_NOTIFY_USER)
    notify_user(gettext("I2P is ready"),
                gettext("You can now access services on I2P."))

def usage():
    """
        Show how to use this program.

        >>> try:
        ...    usage()
        ...    fail()
        ... except SystemExit:
        ...    pass
    """
    print('usage: tails-i2p.py start|stop|restart', file=sys.stderr)
    sys.exit(1)

'''
    >>> # run script
    >>> this_command = sh.Command(sys.argv[0])
    >>> this_command()
    <BLANKLINE>
'''
if __name__ == '__main__':
    if sys.argv and len(sys.argv) > 1:
        if sys.argv[1] == 'doctest':
            from doctest import testmod
            testmod()
        else:
            main(sys.argv[1])
    else:
        usage()

    sys.exit(0)

