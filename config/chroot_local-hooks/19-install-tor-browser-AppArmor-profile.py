#! /usr/bin/python3
"""
    Install the AppArmor profile in the Tor browser.

    Conversion from bash to python by goodcrypto.com

    >>> # run script
    >>> import sh
    >>> import sys
    >>> this_command = sh.Command(sys.argv[0])
    >>> this_command()
    ...
"""

from __future__ import print_function

import os
import re
import sys
from shutil import rmtree
from tempfile import mkdtemp

import sh

PROFILE = '/etc/apparmor.d/torbrowser'
PATCH = '/usr/share/tails/torbrowser-AppArmor-profile.patch'
TEMP_APT_SOURCES = '/etc/apt/sources.list.d/tmp-deb-src.list'

def main():
    """
        Install and patch AppArmor profile for Tor Browser

        >>> main()
        ...
    """

    try:
        toggle_src_apt_sources('on')
        install_apparmor_profile()
        toggle_src_apt_sources('off')

        with open(PATCH) as patchfile:
            sh.patch('--forward', '--batch', PROFILE, _in=patchfile)
        os.remove(PATCH)

    except sh.ErrorReturnCode as error:
        if error.stderr:
            print(error.stderr, file=sys.stderr)
        sys.exit(-1)

def toggle_src_apt_sources(mode):
    """
        Toggle source APT sources.

        >>> toggle_src_apt_sources('on')
        >>> os.path.exists(TEMP_APT_SOURCES)
        True
        >>> toggle_src_apt_sources('off')
        >>> os.path.exists(TEMP_APT_SOURCES)
        False
    """

    def write_deb_src_lines(sources_file):
        """ Write deb-src lines from deb lines in sources_file. """

        with open(TEMP_APT_SOURCES, 'w') as temp_apt_file:
            for line in sources_file:
                if not re.match(r'deb\s+file:/root/local-packages\s+\./', line):
                    line = re.sub(r'^deb(\s+)', r'deb-src\1', line)
                    temp_apt_file.write(line + '\n')

    if mode == 'on':
        # add file in /etc/apt/sources.list.d that contains deb-src sources
        paths = ['/etc/apt/sources.list'] + sh.glob('/etc/apt/sources.list.d/*.list')
        for path in paths:
            with open(path) as sources_file:
                write_deb_src_lines(sources_file)

    elif mode == 'off':
        if os.path.exists(TEMP_APT_SOURCES):
            os.remove(TEMP_APT_SOURCES)

    sh.apt_get('--yes', 'update')

def install_apparmor_profile():
    """
        Install Tor browser AppArmor profile.

        >>> install_apparmor_profile()
        >>> assert len(os.listdir(PROFILE)) > 0
    """
    tmpdir = mkdtemp()
    with os.chdir(tmpdir):
        sh.apt_get('source', 'torbrowser-launcher/testing')
        sh.install('-m', 0o644,
                   sh.glob('torbrowser-launcher-*/apparmor/torbrowser.Browser.firefox'),
                   PROFILE)
    rmtree(tmpdir)

if __name__ == '__main__':
    if sys.argv and len(sys.argv) > 1 and sys.argv[1] == 'test':
        from doctest import testmod
        testmod()
    else:
        main()
