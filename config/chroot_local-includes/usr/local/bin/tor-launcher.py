#! /usr/bin/python3
"""
    Set up the environment and then launch Tor.

    Test with "python3 tor-launcher.py doctest".

    goodcrypto.com converted from bash to python and added basic tests.
"""
import os
import sys

# Import the TOR_LAUNCHER_INSTALL variable, and exec_unconfined_firefox()
# and configure_best_tor_launcher_locale()
from tailslib.tor_browser import (config_best_tor_launcher_locale,
                                  exec_unconfined_firefox, TOR_LAUNCHER_INSTALL)

# sanitize PATH before executing any other code
os.environ['PATH'] = '/usr/local/bin:/usr/bin:/bin'

def main(args):
    """
        >>> main([])
    """
    profile = '{}/.tor-launcher/profile.default'.format(os.environ['HOME'])

    os.unsetenv('TOR_CONTROL_PASSWD')
    os.unsetenv('TOR_FORCE_NET_CONFIG')
    os.environ['TOR_CONFIGURE_ONLY'] = '1'
    os.environ['TOR_CONTROL_PORT'] = '9051'
    os.environ['TOR_CONTROL_COOKIE_AUTH_FILE'] = '/var/run/tor/control.authcookie'
    os.environ['TOR_HIDE_BROWSER_LOGO'] = '1'
    if len(args) > 0:
        if '--force-net-config' in args:
            os.environ['TOR_FORCE_NET_CONFIG'] = '1'

    if not os.path.exists(profile):
        os.makedirs(profile)

    config_best_tor_launcher_locale(profile)

    full_args = ['-app', os.path.join(TOR_LAUNCHER_INSTALL, 'application.ini'), '-profile', profile]
    if len(args) > 0:
        full_args = full_args + list(args)

    exec_unconfined_firefox(full_args)

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
            main(sys.argv)
    else:
        main([])

    sys.exit(0)

