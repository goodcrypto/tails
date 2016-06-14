#! /usr/bin/python3
"""
    Set up the environment and then start the tor browser.

    Test with "python3 tor-browser.py doctest".

    goodcrypto.com converted from bash to python and added basic tests.
"""
import os
import sys
from gettext import gettext

import sh
from tailslib.tor_browser import config_best_tor_browser_locale, exec_firefox, TBB_INSTALL


# AppArmor Ux rules don't sanitize PATH, which can lead to an
# exploited application (that's allowed to run this script unconfined)
# having this script run arbitrary code, violating that application's
# confinement. Let's prevent that by setting PATH to a list of
# directories where only root can write.
os.environ['PATH'] = '/usr/local/bin:/usr/bin:/bin'

PROFILE = '{}/.tor-browser/profile.default'.format(os.environ['HOME'])

def main(args):
    """
        >>> main([])
    """

    try:
        os.environ['TEXTDOMAIN'] = 'tails'

        # Allow Torbutton access to the control port filter (for new identity).
        # Setting a password is required, otherwise Torbutton attempts to
        # read the authentication cookie file instead, which fails.
        os.environ['TOR_CONTROL_HOST'] = '127.0.0.1'
        os.environ['TOR_CONTROL_PORT'] = '9052'
        os.environ['TOR_CONTROL_PASSWD'] = 'passwd'
        # Hide Torbutton's "Tor Network Settings..." context menu entry since
        # it doesn't work in Tails, and we deal with those configurations
        # strictly through Tor Launcher.
        os.environ['TOR_NO_DISPLAY_NETWORK_SETTINGS'] = 'yes'

        if os.path.exists('/usr/local/sbin/tor-has-bootstrapped') or ask_for_confirmation():
            # Torbutton 1.5.1+ uses those environment variables
            os.environ['TOR_SOCKS_HOST'] = '127.0.0.1'
            os.environ['TOR_SOCKS_PORT'] = '9150'

            start_browser(args)

    except sh.ErrorReturnCode as error:
        print(error.stderr, file=sys.stderr)
        sys.exit(-1)

def ask_for_confirmation():
    """
        Warn that Tor isn't ready and see if user wants to proceed anyways.

        >>> ask_for_confirmation()
        False
    """

    # Skip dialog if user is already running Tor Browser:
    try:
        sh.pgrep('-u', 'amnesia', '-f', os.path.join(TBB_INSTALL, 'firefox'))
        result = False
    except sh.ErrorReturnCode_1:
        dialog_title = gettext('Tor is not ready')
        dialog_text = gettext('Tor is not ready. Start Tor Browser anyway?')
        dialog_start = gettext('Start Tor Browser')
        dialog_cancel = gettext('Cancel')

        # results 0 == True; 1 == False; 5 == Timeout
        results = sh.zenity('--question', '--title', "{}".format(dialog_title),
            '--default-cancel', '--ok-label', '{}'.format(dialog_start),
            '--cancel-label', '{}'.format(dialog_cancel),
            '--text', '{}'.format(dialog_text), _ok_code=[0,1,5])
        result = results.exit_code == 0

    return result

def start_browser(args):
    """
        Start the browser.

        >>> start_browser([])
    """
    if not os.path.exists(PROFILE) or not os.path.isdir(PROFILE):
        run = sh.Command('/usr/local/lib/generate-tor-browser-profile')
        run()

    tmp_dir = os.path.join(PROFILE, 'tmp')
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir, 0o700)
    os.environ['TMPDIR'] = tmp_dir

    # We need to set general.useragent.locale properly to get
    # localized search plugins (and perhaps other things too). It is
    # not enough to simply set intl.locale.matchOS to true.
    config_best_tor_browser_locale(PROFILE)

    full_args = ['-allow-remote', '--class', 'Tor Browser', '-profile', PROFILE]
    if len(args) > 0:
        full_args = full_args + list(args)

    exec_firefox(full_args)

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

