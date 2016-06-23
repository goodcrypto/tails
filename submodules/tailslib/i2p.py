#! /usr/bin/python3
'''
    Test with "python3 i2p.py".

    goodcrypto.com converted from bash to python and added basic tests.
'''
import os
import sh

from tailslib.common import set_simple_config_key
from tailslib.localization import language_code_from_locale

I2P_DEFAULT_CONFIG = '/usr/share/i2p'
I2P_CONFIG = '/var/lib/i2p/i2p-config'
I2P_TUNNEL_CONFIG = os.path.join(I2P_CONFIG, 'i2ptunnel.config')
I2P_WRAPPER_LOG = '/var/log/i2p/wrapper.log'

def i2p_is_enabled():
    """
        Determine if i2p is enabled

        >>> i2p_is_enabled()
        False
    """
    result = sh.grep('-qw', 'i2p', _in='/proc/cmdline', _ok_code=[0,1,2])

    return result.exit_code == 0

def i2p_router_console_address():
    """
        Get the i2p router console address.

        >>> i2p_router_console_address()
        '127.0.0.1:7657'
    """
    return '127.0.0.1:7657'

def i2p_router_console_is_ready():
    """
        Determine if the i2p router console is ready

        >>> i2p_router_console_is_ready()
        False
    """
    netstat_result = sh.netstat('-nlp').stdout.decode()
    grep_result = sh.grep('-qwF', i2p_router_console_address(), _in=netstat_result, _ok_code=[0, 1, 2])

    return grep_result.exit_code == 0

def i2p_eep_proxy_address():
    """
        We retrieve the host and port number from the I2P profile. This
        shouldn't be anywhere other than 127.0.0.1:4444 but in case
        someone modifies the hook scripts or the default changes in I2P,
        this check should still work.

        >>> i2p_eep_proxy_address()
        '127.0.0.1:4444'
    """

    for line in open(I2P_TUNNEL_CONFIG):
        if line.startswith('tunnel.0.interface'):
            fields = line.split()
            listen_host = fields[1]
        elif line.startswith('tunnel.0.listenPort'):
            fields = line.split()
            listen_port = fields[1]

    return '{}:{}'.format(listen_host, listen_port)

def i2p_reseed_started():
    """
        Determine if the i2p reseed started

        >>> i2p_reseed_started()
        False
    """
    result = sh.grep('-q', '"Reseed start"', _in=I2P_WRAPPER_LOG, _ok_code=[0, 1, 2])
    return result.exit_code == 0

def i2p_reseed_failed():
    """
        Determine if the i2p reseed failed

        >>> i2p_reseed_failed()
        False
    """
    result = sh.grep('-q', '"Reseed failed, check network connection"',
       _in=I2P_WRAPPER_LOG, _ok_code=[0, 1, 2])

    return result.exit_code == 0

def i2p_reseed_completed():
    """
        Determine if the i2p reseed completed

        >>> i2p_reseed_completed()
        False
    """
    result = sh.grep('-q', '"Reseed complete"', _in=I2P_WRAPPER_LOG, _ok_code=[0, 1, 2])
    return result.exit_code == 0

def i2p_reseed_status():
    """
        Get the i2p reseed status

        >>> status = i2p_reseed_status()
        >>> status is None
        True
    """
    if i2p_reseed_completed():
        result = 'success'
    elif i2p_reseed_failed():
        result = 'failure'
    elif i2p_reseed_started():
        result = 'running'
    else:
        result = None

    return result

def i2p_built_a_tunnel():
    """
        Determine if i2p built a tunnel

        >>> i2p_built_a_tunnel()
        False
    """
    netstat_result = sh.netstat('-nlp').stdout.decode()
    grep_result = sh.grep('-qwF', i2p_eep_proxy_address(), _in=netstat_result, _ok_code=[0, 1, 2])

    return grep_result.exit_code == 0

def set_best_i2p_router_console_lang():
    """
        Set the best i2p router console language

        >>> set_best_i2p_router_console_lang()
        1
    """
    # We will use the detected language even if I2P doesn't support it; it
    # will default to English in that case.
    if 'LANG' in os.environ:
        lang = language_code_from_locale(lang=os.environ['LANG'])
    else:
        lang = language_code_from_locale()

    # We first try to set it in an existing "live" config, even though
    # the effect will only appear after a restart.
    config_file = os.path.join(I2P_CONFIG, 'router.config')
    default_config_file = os.path.join(I2P_DEFAULT_CONFIG, 'router.config')
    for config in [config_file, default_config_file]:
        if os.path.exists(config):
            set_simple_config_key(config, 'routerconsole.lang', lang)
            return 0

    return 1

if __name__ == '__main__':
    # pylint wants this imported at the top, but
    # it's only used for testing so we want to minimize imports
    from doctest import testmod
    testmod()

