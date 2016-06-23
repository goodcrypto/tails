#! /usr/bin/python3
'''
    Launch Tor browser in Tails.

    Test with "python3 tails-tor-launcher.py doctest" as root.

    goodcrypto.com converted from bash to python and added basic tests.
'''
import os
import sys
from time import sleep

import sh

from tailslib.common import set_default_locale
from tailslib.gnome import export_gnome_env

os.environ['PATH'] = '/usr/local/bin:/usr/bin:/bin'

def main(*args):
    """
        >>> try:
        ...     main()
        ...     fail()
        ... except SystemExit:
        ...     pass
    """

    LIVE_USERNAME_FILE = '/etc/live/config.d/username.conf'
    TOR_BROWSER_LIB_DIR = '/usr/local/lib/TorBrowser'
    TOR_BROWSER_CACHES_DIR = os.path.join(TOR_BROWSER_LIB_DIR, 'Data/Browser', 'Caches')

    set_default_locale()

    # Get LIVE_USERNAME
    with open(LIVE_USERNAME_FILE) as f:
        __, __, live_username = f.read().partition('=')
    live_username = live_username.strip()

    # The Tor Browser hardcodes the default profile dir to inside
    # ../TorBrowser/Data/Browser/ from the folder storing the
    # application.ini file supplied via -app. We can use -profile to load
    # it from a different place, but then the Caches directory
    # must still exist and be accessible in the above folder.
    os.makedirs(TOR_BROWSER_CACHES_DIR, exist_ok=True)
    sh.chmod('-R', 'a+rX', TOR_BROWSER_LIB_DIR)

    while sh.pgrep('-u', live_username, '^ibus-daemon', _ok_code=[0, 1]) == 1:
        sleep(5)

    export_gnome_env()

    sh.sudo('-u', live_username, 'xhost', '+SI:localuser:tor-launcher')
    if len(args) > 0:
        exit_code = sh.gksudo('-u', 'tor-launcher', '/usr/local/bin/tor-launcher', '--', sh.glob(args)).exit_code
    else:
        exit_code = sh.gksudo('-u', 'tor-launcher', '/usr/local/bin/tor-launcher', '--').exit_code
    sh.sudo('-u', live_username, 'xhost', '-SI:localuser:tor-launcher')

    sys.exit(exit_code)

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
            main(sys.argv[1:])
    else:
        main()

    sys.exit(0)

