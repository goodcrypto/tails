#! /usr/bin/python3
'''
    Run I2P browser

    Test with "python3 unsafe-browser.py doctest" as root.

    goodcrypto.com converted from bash to python and added basic tests.
'''
from gettext import gettext
from glob import glob
import os
import re
import sys

import sh

from tailslib.chroot_browser import configure_chroot_browser, run_browser_in_chroot, setup_chroot_for_browser, try_cleanup_browser_chroot
from tailslib.i2p import i2p_is_enabled, i2p_router_console_is_ready
from tailslib.tor_browser import guess_best_tor_browser_locale, TBB_EXT


os.environ['PATH'] = '/usr/local/sbin:/usr/local/bin:/usr/bin:/bin'
os.environ['TEXTDOMAIN'] = 'tails'

CMD = os.path.basename(sys.argv[0])
SUDO_USER = os.environ['SUDO_USER']
CONF_DIR = "/var/lib/i2p-browser"
COW = os.path.join(CONF_DIR, 'cow')
CHROOT = os.path.join(CONF_DIR, 'chroot')
BROWSER_USER = 'i2pbrowser'

def main():
    """
        Main script
    """

    # This isn't very useful without I2P...
    if not i2p_is_enabled():
        sys.exit(0)

    LOCK = "/var/lock/{}".format(CMD)

    # Prevent multiple instances of the script.
    try:
        lockfile = io.FileIO(LOCK, 'x')

    except FileExistsError:
        error(gettext('Another Unsafe Browser is currently running, or being cleaned up. Please retry in a while.'))

    else:
        try:
            if i2p_router_console_is_ready():
                ready_to_start = True
            else:
                ready_to_start = verify_start()

            if ready_to_start:
                show_start_notification()

                try:
                    start_browser()
                except KeyboardInterrupt:
                    pass
                else:
                    print("* Exiting I2P Browser")
                    show_shutdown_notification()
        finally:
            try_cleanup_browser_chroot(CHROOT, COW, BROWSER_USER)
            # the race below doesn't matter because the file is considered locked
            # as long as it exists
            lockfile.close()
            os.remove(LOCK)

def verify_start():
    """
        >>> verify_start()
        False
    """
    # Make sure the user really wants to start the browser in case the router console isn't available
    launch = gettext('_Launch')
    exit = gettext('_Exit')
    want_to_launch = gettext('Do you really want to launch the I2P Browser?')
    router_not_ready = gettext('The I2P router console is not ready.')
    dialog_msg="<b><big>{}</big></b>\n\n{}".format(want_to_launch, router_not_ready)

    results = sh.sudo('-u', SUDO_USER, 'zenity',
        '--question', '--title', '',
        '--default-cancel', '--ok-label', '{}'.format(launch),
        '--cancel-label', '{}'.format(exit),
        '--text', '{}'.format(dialog_msg), _ok_code=[0,1,5])

    return results.exit_code == 0

def start_browser():
    """
        >>> start_browser()
        * Setting up chroot
        * Configuring chroot
        * Starting I2P Browser
    """
    BROWSER_NAME = 'i2p-browser'
    HOME_PAGE = "http://127.0.0.1:7657"
    NOSCRIPT_EXT_XPI = os.path.join(TBB_EXT, '73a6fe31-595d-460b-a920-fcc0f8843232.xpi')
    TORBUTTON_EXT_DIR = os.path.join(TBB_EXT, 'torbutton@torproject.org')
    HUMAN_READABLE_NAME = gettext('UI2P Browser')
    IP4_NAMESERVERS = "0.0.0.0"

    print("* Setting up chroot")
    try:
        setup_chroot_for_browser(CHROOT, COW, BROWSER_USER)
    except:
        error(gettext('Failed to setup chroot.'))
        raise

    print("* Configuring chroot")
    try:
        extensions = glob(TBB_EXT+'langpack-*.xpi') + [NOSCRIPT_EXT_XPI, TORBUTTON_EXT_DIR]
        configure_chroot_browser(CHROOT, BROWSER_USER, BROWSER_NAME,
                                 HUMAN_READABLE_NAME, HOME_PAGE, IP4_NAMESERVERS,
                                 extensions)
    except:
        error(gettext('Failed to configure browser.'))
        raise
    else:
        copy_extra_tbb_prefs(CHROOT, BROWSER_NAME, BROWSER_USER)

    print("* Starting I2P Browser")
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
    title = gettext('Starting the I2P Browser...')
    body = gettext('This may take a while, so please be patient.')
    sh.tails_notify_user(title, body, 10000)

def copy_extra_tbb_prefs(chroot, browser_name, browser_user):
    """
        >>> CONF_DIR = "/var/lib/i2p-browser"
        >>> CHROOT = os.path.join(CONF_DIR, 'chroot')
        >>> BROWSER_NAME = 'i2p-browser'
        >>> BROWSER_USER = 'i2pbrowser'
        >>> copy_extra_tbb_prefs(CHROOT, BROWSER_NAME, BROWSER_USER)
    """
    tbb_prefs = "/etc/tor-browser/profile/preferences"
    browser_prefs_dir = os.path.join(
      chroot, 'home', browser_user, '.{}'.format(browser_name), 'profile.default/preferences')
    os.makedirs(browser_prefs_dir, exist_ok=True)

    # Selectively copy the TBB prefs we want
    browser_prefs_path = os.path.join(browser_prefs_dir, '0000tails.js')
    with open(browser_prefs_path, 'w') as browser_prefs:
        for line in open(os.path.join(tbb_prefs, '0000tails.js')):
            if re.match(r'.*?(security|update|download|spell|noscript|torbrowser)', line):
                browser_prefs.write(line)
    extension_overrides_path = os.path.join(browser_prefs_dir, 'extension-overrides.js')
    with open(extension_overrides_path, 'w') as extension_overrides:
        for line in open(os.path.join(tbb_prefs, 'extension-overrides.js')):
            if re.match(r'.*?(capability|noscript)', line):
                extension_overrides.write(line)
    sh.chown('-R', '{}:{}'.format(browser_user, browser_user), browser_prefs_dir)

def show_shutdown_notification():
    """
        >>> show_shutdown_notification()
    """
    title = gettext('Shutting down the I2P Browser...')
    body = gettext(
      'This may take a while, and you may not restart the I2P Browser until it is properly shut down.')
    sh.tails_notify_user(title, body, 10000)

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

