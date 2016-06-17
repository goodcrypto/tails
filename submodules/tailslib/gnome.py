#! /usr/bin/python3
'''
    Export gnome environment.

    Test with "python3 gnome.py".

    goodcrypto.com converted from bash to python and added basic tests.
'''
import os
import sh

def export_gnome_env():
    '''
        Export gnome environment.

        >>> export_gnome_env()
        >>> variable = os.environ['DBUS_SESSION_BUS_ADDRESS']
        >>> variable is not None
        True
        >>> variable = os.environ['DISPLAY']
        >>> variable is not None
        True
        >>> variable = os.environ['XAUTHORITY']
        >>> variable is not None
        True
    '''
    LIVE_USERNAME_FILE = '/etc/live/config.d/username.conf'

    # Get LIVE_USERNAME
    with open(LIVE_USERNAME_FILE) as f:
        __, __, live_username = f.read().partition('=')

    pgrep_result = sh.pgrep('--newest', '--euid', live_username.strip(), 'gnome-shell')
    gnome_shell_pid = pgrep_result.stdout.decode().strip()

    # extract the environment varialbes from the gnome shell
    with open('/proc/{gnome_shell_pid}/environ'.format(gnome_shell_pid=gnome_shell_pid)) as f:
        env_lines = f.read().split('\0')

    # export the gnome environment variables
    variables = "(DBUS_SESSION_BUS_ADDRESS|DISPLAY|XAUTHORITY)"
    grep_result = sh.grep('-E', r'^{vars}='.format(vars=variables),
       _in='\n'.join(env_lines), _ok_code=[0, 1, 2])
    for line in grep_result.stdout.decode().split('\n'):
        attr, __, value = line.partition('=')
        os.environ[attr.strip()] = value.strip()

if __name__ == '__main__':
    # pylint wants this imported at the top, but
    # it's only used for testing so we want to minimize imports
    from doctest import testmod
    testmod()

