#! /usr/bin/python3
'''
    Set up the environment and then start IceDove.

    Test with "python3 icedove.py doctest".
    The tests will start the tor-browser so you probably
    want to use a tester that handles user interaction or
    run the tests from the command line and answer prompts as needed.

    goodcrypto.com converted from bash to python and added basic tests.
'''
import os
import sys
from gettext import gettext

import sh

from tailslib.tor_browser import set_mozilla_pref

# sanitize PATH before executing any other code
os.environ['PATH'] = '/usr/local/bin:/usr/bin:/bin'

os.environ['TEXTDOMAIN'] = 'tails'

HOME_DIR = os.environ['HOME']
CLAWSMAIL_CONFIG_DIR = os.path.join(HOME_DIR, '.claws-mail')
ICEDOVE_CONFIG_DIR = os.path.join(HOME_DIR, '.icedove')
PROFILE = os.path.join(ICEDOVE_CONFIG_DIR, 'profile.default')

def main(*args):
    """
        >>> main()
    """

    configure_default_incoming_protocol()

    ACCOUNT_RC = os.path.join(CLAWSMAIL_CONFIG_DIR, 'accountrc')
    if claws_mail_config_is_persistent() and os.path.isfile(ACCOUNT_RC):
        if warn_about_claws_mail_persistence():
            sys.exit(0)

    start_icedove(*args)

def claws_mail_config_is_persistent():
    """
        Return True iff claws mail config is persistent.

        >>> claws_mail_config_is_persistent()
        True
    """

    sh_results = sh.findmnt('--noheadings',
                            '--output', 'SOURCE',
                            '--target', CLAWSMAIL_CONFIG_DIR,
                            _ok_code=[0,1])

    if sh_results.exit_code == 1:
        filesystem = sh_results.stdout.decode().strip()
        result = filesystem in sh.glob('/dev/mapper/TailsData_unlocked[/claws-mail]')
    else:
        result = False

    return result

def icedove_config_is_persistent():
    """
        Return True iff icedove config is persistent.

        >>> icedove_config_is_persistent()
        False
    """

    sh_results = sh.findmnt('--noheadings',
                            '--output', 'SOURCE',
                            '--target', ICEDOVE_CONFIG_DIR,
                            _ok_code=[0,1])

    if sh_results.exit_code == 1:
        filesystem = sh_results.stdout.decode().strip()
        result = filesystem in sh.glob('/dev/mapper/TailsData_unlocked[/icedove]')
    else:
        result = False

    return result

def warn_about_claws_mail_persistence():
    """
        Warn about Claws Mail persistence.

        >>> warn_about_claws_mail_persistence()
        False
    """

    is_activated_text = gettext('The <b>Claws Mail</b> persistence feature is activated.')
    migrate_text = gettext("If you have emails saved in <b>Claws Mail</b>, you should <a href='https://tails.boum.org/doc/anonymous_internet/claws_mail_to_icedove'>migrate your data</a> before starting <b>Icedove</b>.")
    launch_text = gettext('_Launch')
    exit_text = gettext('_Exit')
    dialog_msg = gettext('<b><big>{}</big></b>\n\n{}'.
                  format(is_activated_text, migrate_text))

    JS_PREFS = os.path.join(PROFILE, 'prefs.js')
    if os.path.isfile(JS_PREFS):
        url = '<a href="https://tails.boum.org/doc/anonymous_internet/claws_mail_to_icedove#delete">'
        if_msg = gettext(
          'If you already migrated your emails to <b>Icedove</b>, {url} you should delete all your <b>Claws Mail</b> data</a> to remove this warning.'.format(url=url))
        dialog_msg = dialog_msg + if_msg

    # results 0 == True; 1 == False; 5 == Timeout
    results = sh.zenity('--question', '--title', "", '--default-cancel',
        '--ok-label', '{}'.format(launch_text), '--cancel-label', '{}'.format(exit_text),
        '--text', '{}'.format(dialog_msg), _ok_code=[0,1,5])
    start = results.exit_code == 0

    return start

def configure_default_incoming_protocol():
    """
        Configure incoming protocol (POP vs IMAP).

        >>> configure_default_incoming_protocol()
    """

    # For extensions.torbirdy.defaultprotocol,
    POP = 0
    IMAP = 1

    if icedove_config_is_persistent():
        default_protocol = POP
    else:
        default_protocol = IMAP

    TAILS_JS = os.path.join(PROFILE, 'preferences', '0000tails.js')
    set_mozilla_pref(TAILS_JS,
                     "extensions.torbirdy.defaultprotocol",
                     default_protocol)

def start_icedove(*args):
    """
        Start icedove.

        >>> start_icedove()
    """

    # Give Icedove its own temp directory, similar rationale to a1fd1f0f & #9558.
    tmpdir = os.path.join(PROFILE, 'tmp')
    os.makedirs(tmpdir, mode=0700)
    os.environ['TMPDIR'] = tmpdir

    try:
        del os.environ['SESSION_MANAGER']
    except KeyError:
        # if it doesn't exist, then don't worry about it
        pass

    if args is None:
        sh.icedove('--class', 'Icedove', '-profile', PROFILE)
    else:
        sh.icedove('--class', 'Icedove', '-profile', PROFILE, *args)


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

    sys.exit(0)

