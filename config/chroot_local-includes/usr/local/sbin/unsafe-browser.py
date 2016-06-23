#! /usr/bin/python3
'''
    Run Unsafe browser

    Test with "python3 unsafe-browser.py doctest" as root.

    goodcrypto.com converted from bash to python and added basic tests.
'''
from gettext import gettext
from glob import glob
import io
import os
import re
import sys

import sh

from tailslib.chroot_browser import configure_chroot_browser, run_browser_in_chroot, setup_chroot_for_browser, try_cleanup_browser_chroot
from tailslib.common import is_readable
from tailslib.localization import localized_tails_doc_page
from tailslib.tor import tor_is_working
from tailslib.tor_browser import guess_best_tor_browser_locale, TBB_EXT


os.environ['PATH'] = '/usr/local/sbin:/usr/local/bin:/usr/bin:/bin'
os.environ['TEXTDOMAIN'] = 'tails'

CMD = os.path.basename(sys.argv[0])
SUDO_USER = os.environ['SUDO_USER']

CONF_DIR = "/var/lib/unsafe-browser"
COW = os.path.join(CONF_DIR, 'cow')
CHROOT = os.path.join(CONF_DIR, 'chroot')
BROWSER_USER = 'clearnet'

def main():
    """
        main()
    """

    LOCK = "/var/lock/{}".format(CMD)

    # Prevent multiple instances of the script.
    try:
        lockfile = io.FileIO(LOCK, 'x')

    except FileExistsError:
        error(gettext('Another Unsafe Browser is currently running, or being cleaned up. Please retry in a while.'))

    else:
        try:
            ip4_nameservers = get_nameservers()
            if ip4_nameservers is not None and verify_start():
                show_start_notification()
                try:
                    start_browser(ip4_nameservers)
                except KeyboardInterrupt:
                    pass
                else:
                    print("* Exiting Unsafe Browser")
                    show_shutdown_notification()
                    maybe_restart_tor()

        finally:
            try_cleanup_browser_chroot(CHROOT, COW, BROWSER_USER)
            # the race below doesn't matter because the file is considered locked
            # as long as it exists
            lockfile.close()
            os.remove(LOCK)

def get_nameservers():
    """
        Get IP4 name servers.

        >>> get_nameservers()
        '192.168.0.100 192.168.0.1'
    """
    NM_ENV_FILE = '/var/lib/NetworkManager/env'

    ip4_nameservers = None

    # Get the DNS servers that was obtained from NetworkManager, if any...
    if is_readable(NM_ENV_FILE):
        # We also check that the file we are gonna *source* doesn't
        # contain any unexpected data, like (potentially malicious) shell
        # script. Note that while the regex used for deciding IP addresses
        # is far from perfect, it serves our purpose here.
        IP4_REGEX = '[0-9]{1,3}(\.[0-9]{1,3}){3}'
        NAMESERVERS_REGEX = '^IP4_NAMESERVERS="({}( {})*)?"$'.format(IP4_REGEX, IP4_REGEX)
        with open(NM_ENV_FILE) as f:
            m = re.match(NAMESERVERS_REGEX, f.readline())
            if m:
                # Import the IP4_NAMESERVERS variable.
                ip4_nameservers = m.group(1)
            else:
                error(gettext(
                  'NetworkManager passed us garbage data when trying to deduce the clearnet DNS server.'))

    # ... otherwise fail.
    # FIXME: Or would it make sense to fallback to Google's DNS or OpenDNS?
    # Some stupid captive portals may allow DNS to any host, but chances are
    # that only the portal's DNS would forward to the login page.
    if ip4_nameservers is None:
        error(gettext('No DNS server was obtained through DHCP or manually configured in NetworkManager.'))

    return ip4_nameservers

def verify_start():
    """
        >>> verify_start()
        False
    """
    # Make sure the user really wants to start the browser
    launch = gettext('_Launch')
    exit = gettext('_Exit')
    want_to_launch = gettext('Do you really want to launch the Unsafe Browser?')
    not_anonymous = gettext(
      'Network activity within the Unsafe Browser is <b>not anonymous</b>.\nOnly use the Unsafe Browser if necessary, for example\nif you have to login or register to activate your Internet connection.')
    dialog_msg="<b><big>{}</big></b>\n\n{}".format(want_to_launch, not_anonymous)

    results = sh.sudo('-u', SUDO_USER, 'zenity',
        '--question', '--title', '',
        '--default-cancel', '--ok-label', '{}'.format(launch),
        '--cancel-label', '{}'.format(exit),
        '--text', '{}'.format(dialog_msg), _ok_code=[0,1,5])
    return results.exit_code == 0

def start_browser(ip4_nameservers):
    """
        >>> start_browser('127.0.0.1')
        * Setting up chroot
        * Configuring chroot
        * Starting Unsafe Browser
    """
    BROWSER_NAME = 'unsafe-browser'
    HUMAN_READABLE_NAME = gettext('Unsafe Browser')
    WARNING_PAGE = '/usr/share/doc/tails/website/misc/unsafe_browser_warning'
    HOME_PAGE = localized_tails_doc_page(WARNING_PAGE)

    print("* Setting up chroot")
    try:
        setup_chroot_for_browser(CHROOT, COW, BROWSER_USER)
    except:
        error(gettext('Failed to setup chroot.'))
        raise

    print("* Configuring chroot")
    try:
        configure_chroot_browser(CHROOT, BROWSER_USER, BROWSER_NAME,
                                 HUMAN_READABLE_NAME, HOME_PAGE, ip4_nameservers,
                                 glob(TBB_EXT+'/langpack-*.xpi'))
    except:
        error(gettext('Failed to configure browser.'))
        raise

    print("* Starting Unsafe Browser")
    try:
        run_browser_in_chroot(CHROOT, BROWSER_NAME, BROWSER_USER, SUDO_USER)
    except:
        error(gettext('Failed to run browser.'))
        raise

def error(message):
    """
        >>> error('testing')
    """
    ErrorTag = gettext('Error')

    cli_text = '{}: {} {}'.format(CMD, ErrorTag, message)
    dialog_text="<b><big>{}</big></b>\n\n{}".format(ErrorTag, message)

    print(cli_text, file=sys.stderr)
    sh.sudo('-u', SUDO_USER, 'zenity',
            '--error', '--title', '',
            '--text', '{}'.format(dialog_text), _ok_code=[0,1,5])

def show_start_notification():
    """
        >>> show_start_notification()
    """
    title = gettext('Starting the Unsafe Browser...')
    body = gettext('This may take a while, so please be patient.')
    sh.tails_notify_user(title, body, 10000)

def show_shutdown_notification():
    """
        >>> show_shutdown_notification()
    """
    title = gettext('Shutting down the Unsafe Browser...')
    body = gettext(
      'This may take a while, and you may not restart the Unsafe Browser until it is properly shut down.')
    sh.tails_notify_user(title, body, 10000)

def maybe_restart_tor():
    """
        >>> maybe_restart_tor()
    """
    # Restart Tor if it's not working (a captive portal may have prevented
    # Tor from bootstrapping, and a restart is the fastest way to get
    # wheels turning)
    if not tor_is_working():
        print("* Restarting Tor")
        sh.restart_tor()
        if sh.systemctl('--quiet', 'is-active', 'tor@default.service', _ok_code=[0,1,3]) != 0:
            error(gettext('Failed to restart Tor.'))
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

