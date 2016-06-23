#! /usr/bin/python3
'''
    Helper functions for Tor.

    Test with "python3 tor.py" as root.

    goodcrypto.com converted from bash to python and added basic tests.
'''
import os
import re
import socket

import sh


TOR_RC = '/etc/tor/torrc'
TOR_LOG = '/var/log/tor/log'
TOR_DIR = '/var/lib/tor'
TOR_DESCRIPTORS = os.path.join(TOR_DIR, 'cached-microdescs')
NEW_TOR_DESCRIPTORS = '{}.new'.format(TOR_DESCRIPTORS)

def get_tor_control_port():
    """
        >>> get_tor_control_port()
        9051
    """
    port = None
    with open(TOR_RC) as f:
        lines = f.readlines()

    for line in lines:
        m = re.match(r'^ControlPort\s+(\d+)', line)
        if m:
            port = int(m.group(1))
            break

    return port

def tor_control_send(param):
    """
        Send a command to Tor.

        >>> tor_control_send('GETINFO status/bootstrap-phase')
        '250 OK\\n250-status/bootstrap-phase=NOTICE BOOTSTRAP PROGRESS=100 TAG=done SUMMARY="Done"\\n250 OK\\n250 closing connection\\n'
    """
    COOKIE = '/var/run/tor/control.authcookie'
    HOST = '127.0.0.1'
    PORT = get_tor_control_port()

    xxd_result = sh.xxd('-c', 32, '-g', 0, COOKIE)
    cut_result = sh.cut('-d', ' ', '-f2', _in=xxd_result.stdout.decode())
    HEXCOOKIE = cut_result.stdout.decode().strip()
    command = 'AUTHENTICATE {hex_cookie}\r\n{param}\r\nQUIT\r\n'.format(
       hex_cookie=HEXCOOKIE, param=param)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    s.sendall(command.encode())
    data = s.recv(1024)
    s.close()

    if data:
        data = data.decode().replace('\r', '')

    return data

def tor_control_getinfo(param):
    """
        This function may be dangerous to use. See "Potential Tor bug" below.
        Only handles GETINFO keys with single-line answers

        >>> tor_control_getinfo('status/bootstrap-phase')
        'NOTICE BOOTSTRAP PROGRESS=100 TAG=done SUMMARY="Done"'
    """
    info = tor_control_send('GETINFO {}'.format(param))
    m = re.match(r'^250\s+OK\n250-' + param + r'=(.*?)\n', info)
    if m:
        info = m.group(1)
    else:
        m = re.match(r'^250 OK\n552 (.*?)\n', info)
        if m:
            info = m.group(1)

    return info

def tor_control_getconf(param):
    """
        Get conf from Tor.

        >>> tor_control_getconf('DisableNetwork')
        '0'
    """
    conf = tor_control_send('GETCONF {}'.format(param))
    m = re.match(r'^250 OK\n250 {}=(.*?)\n'.format(param), conf)
    if m:
        conf = m.group(1)

    return conf

def tor_control_setconf(param):
    """
        Get conf from Tor.

        >>> tor_control_setconf('Log="notice file {}'.format(TOR_LOG))
        True
    """
    conf = tor_control_send('SETCONF {}'.format(param))
    if conf.startswith('250 OK\n'):
        result = True
    else:
        result = False

    return result

def tor_bootstrap_progress():
    """
        Report the progress of booting Tor.

        >>> progress = tor_bootstrap_progress()
        >>> isinstance(progress, int)
        True
    """
    progress = 0

    if os.path.exists(TOR_LOG):
        with open(TOR_LOG) as f:
            for line in f.readlines():
                m = re.match(r'.*?\[notice\] Bootstrapped (\d+)%:.*', line.strip())
                if m:
                    progress = int(m.group(1))

    return progress

'''
def tor_bootstrap_progress():
    """
        Potential Tor bug: it seems like using this version makes Tor get
        stuck at "Bootstrapped 5%" quite often. Is Tor sensitive to opening
        control ports and/or issuing "getinfo status/bootstrap-phase" during
        early bootstrap? Because of this we fallback to greping the log.
    """
    info = tor_control_getinfo('status/bootstrap-phase')
    m = re.match(r'.*? BOOTSTRAP PROGRESS= (\d+) .*', info.strip())
    if m:
        progress = int(m.group(1))

    return progress
'''

def tor_is_working():
    """
        Determine if Tor is working.

        >>> tor_is_working()
        True
    """
    if os.path.exists(TOR_DESCRIPTORS) or os.path.exists(NEW_TOR_DESCRIPTORS):
        result = True
    else:
        result = tor_bootstrap_progress() == 100

    return result

def tor_append_to_torrc(param1, param2):
    """
        Add args to torrc.

        >>> tor_append_to_torrc('#Test', 'test')
        '#Test test\\n'
    """
    line = '{} {}\n'.format(param1, param2)
    with open(TOR_RC, 'a') as f:
        f.write(line)

    return line

def tor_set_in_torrc(param1, param2):
    """
        Set a (possibly existing) option $1 to $2 in torrc. Shouldn't be
        used for options that can be set multiple times (e.g. the listener
        options). Does not support configuration entries split into multiple
        lines (with the backslash character).

        >>> tor_set_in_torrc('#Test', 'new test')
        '#Test new test\\n'
    """
    with open(TOR_RC, 'r') as in_file:
        lines = in_file.readlines()
    with open(TOR_RC, 'w') as out_file:
        for line in lines:
            if not line.startswith(param1):
                out_file.write(line)
    return tor_append_to_torrc(param1, param2)

if __name__ == '__main__':
    # pylint wants this imported at the top, but
    # it's only used for testing so we want to minimize imports
    from doctest import testmod
    testmod()

