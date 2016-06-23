#! /usr/bin/python3
'''
    A few common functions.

    Test with "python3 common.py".

    goodcrypto.com converted from bash to python and added basic tests.
'''
import os
import stat
from time import sleep

import sh

# sanitize PATH before executing any other code
os.environ['PATH'] = '/usr/local/bin:/usr/bin:/bin'


def clock_gettime_monotonic():
    """
        Get monotonic time in seconds. See clock_gettime(2) for details.
        Note: we limit ourselves to seconds simply because floating point
        arithmetic is a PITA in the shell.

        >>> value = clock_gettime_monotonic()
        >>> value is not None
        True
        >>> isinstance(value, int)
        True
    """
    results = sh.perl('-w', '-MTime::HiRes=clock_gettime,CLOCK_MONOTONIC',
                      '-E', 'say int(clock_gettime(CLOCK_MONOTONIC))')

    return int(results.stdout.decode().strip())

def wait_until(timeout, args, delay=1):
    """
        Run the first element of args until `timeout` seconds has passed, and sleep
        `delay` (optional, defaults to 1) seconds in between the calls.

        Note that execution isn't aborted exactly after `timeout`
        seconds. In the worst case (the timeout happens right after we check
        if the timeout has happened) we'll wait in total: `timeout` seconds +
        `delay` seconds + the time needed for `check_expr`.

        >>> mnt = 'tmpfs'
        >>> mnt_dir = '/tmp/amnesia'
        >>> if not os.path.exists(mnt_dir):
        ...     os.mkdir(mnt_dir)
        >>> result = sh.mount('-t', mnt, mnt, mnt_dir)
        >>> wait_until(10, args=['umount', mnt])
        False
    """
    result = False
    timeout_at = clock_gettime_monotonic() + timeout

    command = args[0]
    if callable(command):
        if len(args[1:]) > 0:
            run_command = command(args[1:])
        else:
            run_command = command()

        while run_command:
            if clock_gettime_monotonic() >= timeout_at:
                result = True
                break
            sleep(delay)
    else:
        full_path = sh.which(command)
        try:
            run = sh.Command(full_path)
            while run(sh.glob(args[1:])):
                if clock_gettime_monotonic() >= timeout_at:
                    result = True
                    break
                sleep(delay)
        except:
            pass

    return result

def try_for(timeout, args, delay=1):
    """
        Just an alias. The second argument (wait_until()'s first element of args) is
        the "try code block". Just like in `wait_until()`, the timeout isn't
        very accurate.

        >>> mnt = 'tmpfs'
        >>> mnt_dir = '/tmp/amnesia'
        >>> if not os.path.exists(mnt_dir):
        ...     os.mkdir(mnt_dir)
        >>> result = sh.mount('-t', mnt, mnt, mnt_dir)
        >>> try_for(10, args=['umount', mnt])
        False
    """
    return wait_until(timeout, args, delay=delay)

def set_simple_config_key(filename, key, value, op='='):
    """
        Sets the `value` of a `key` in a simple configuration `file`. With
        "simple" you should think something like a the shell environment as
        output by the `env` command. Hence this is only useful for
        configuration files that have no structure (e.g. sections with
        semantic meaning, like the namespace secions in .gitconfig), allow
        only one assignment per line, and a fixed/static assignment operator
        (`op`, which defaults to '=', but other examples would be " = " or
        torrc's " "). If the key already exists its value is updated in
        place, otherwise it's added at the end.

        >>> filename = '/tmp/test.conf'
        >>> set_simple_config_key(filename, 'key', 'value')
        >>> with open(filename) as f:
        ...     lines = f.readlines()
        ...     'key=value' in ''.join(lines)
        True
        >>> set_simple_config_key(filename, 'key', 'new value')
        >>> with open(filename) as f:
        ...     lines = f.readlines()
        ...     'key=new value' in ''.join(lines)
        True
        >>> 'key=value' in ''.join(lines)
        False
        >>> os.remove(filename)
    """
    if os.path.exists(filename):
        with open(filename) as f:
            lines = f.readlines()
    else:
        lines = []

    updated_key = False
    with open(filename, 'wt') as f:
        for line in lines:
            if line.startswith(key):
                f.write('{key}{op}{value}\n'.format(key=key, op=op, value=value))
                updated_key = True
            else:
               f.write(line)

        if not updated_key:
            f.write('{key}{op}{value}\n'.format(key=key, op=op, value=value))

def set_default_locale():
    """
        Set the default locale in the environment.

        >>> set_default_locale()
        >>> lang = os.environ['LANG']
        >>> lang is not None
        True
    """
    DEFAULT_LOCALE_FILE = '/etc/default/locale'

    # Get default locale
    with open(DEFAULT_LOCALE_FILE) as f:
        lines = f.readlines()
    for line in lines:
        if line.startswith('LANG='):
            __, __, lang = line.partition('=')
            break
    os.environ['LANG'] = lang.strip()

def is_readable(path):
    """
        Return True if path exists and file is readable.

        >>> is_readable('/etc/hosts')
        True
    """
    return os.path.exists(path) and os.access(path, os.R_OK)

def no_abort():
    """
        Not converting as it's not needed in python.
    """

if __name__ == '__main__':
    # pylint wants this imported at the top, but
    # it's only used for testing so we want to minimize imports
    from doctest import testmod
    testmod()

