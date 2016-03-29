#! /usr/bin/python
'''
    Install the AppArmor profile in the Tor browser.

    Conversion from bash to python by goodcrypto.com

    >>> # run script
    >>> import sh
    >>> import sys
    >>> this_command = sh.Command(sys.argv[0])
    >>> this_command()
    <BLANKLINE>
'''

from __future__ import print_function

import os
import sys
from gettext import gettext

import sh

os.environ['TEXTDOMAIN'] = 'tails'

CLAWSMAIL_DIR = '{}/.claws-mail'.format(os.environ['HOME'])
PROFILE = '{}/.icedove/profile.default'.format(os.environ['HOME'])

def claws_mail_config_is_persistent():
    """ Return True iff claws mail config is persistent. """

    sh_results = sh.findmnt('--noheadings',
                                '--output', 'SOURCE',
                                '--target', CLAWSMAIL_DIR,
                                _ok_code=[0,1])

    if sh_results.exit_code == 1:
        filesystem = str(sh_results.stdout).strip()

    return filesystem in sh.glob('/dev/mapper/TailsData_unlocked[/claws-mail]')

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
    dialog_msg = ('<b><big>{}</big></b>\n\n{}'.
                  format(is_activated_text, migrate_text))
    # Since zenity can't set the default button to cancel, we switch the
    # labels and interpret the return value as its negation.
    try:
        sh_results = sh.zenity('--question',
                                '--title', '',
                                '--ok-label', exit_text,
                                '--cancel-label', launch_text,
                                '--text', dialog_msg,
                              _ok_code=[0, 1])
        start = sh_results.exit_code == 1
    except sh.ErrorReturnCode:
        start = False
    else:
        start = True

    return start

def start_icedove(*args):
    """ Start icedove". """

    # Give Icedove its own temp directory, similar rationale to a1fd1f0f & #9558.
    tmpdir = '{}/tmp'.format(PROFILE)
    sh.mkdir('--mode=0700', '--parents', tmpdir)
    os.environ['TMPDIR'] = tmpdir

    del os.environ['SESSION_MANAGER']

    usr_bin_icedove = sh.Command('/usr/bin/icedove')
    usr_bin_icedove('--class', 'Icedove', '-profile', PROFILE, *args)

if (claws_mail_config_is_persistent() and
        os.path.isfile('{}/accountrc'.format(CLAWSMAIL_DIR))):
    if warn_about_claws_mail_persistence():
        sys.exit(0)

start_icedove(*sys.argv[1:])
