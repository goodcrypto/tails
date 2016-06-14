#! /usr/bin/python3
"""
    Helper functions for the Tor browser.

    goodcrypto.com converted from bash to python and added basic tests.
"""
import os
import re
import sh

# sanitize PATH before executing any other code
os.environ['PATH'] = '/usr/local/bin:/usr/bin:/bin'

TBB_INSTALL = '/usr/local/lib/tor-browser'
TBB_PROFILE = '/etc/tor-browser/profile'
TBB_EXT = '/usr/local/share/tor-browser-extensions'
TOR_LAUNCHER_INSTALL = '/usr/local/lib/tor-launcher-standalone'
TOR_LAUNCHER_LOCALES_DIR = os.path.join(TOR_LAUNCHER_INSTALL, 'chrome/locale')

def set_mozilla_pref(filename, name, value, prefix='pref'):
    """
        Set mozilla preference.

        For strings it's up to the caller to add
        double-quotes ("") around the value.

        Sometimes we might want prefix to be e.g. user_pref

        >>> POP = 0
        >>> IMAP = 1
        >>> HOME_DIR = os.environ['HOME']
        >>> ICEDOVE_CONFIG_DIR = os.path.join(HOME_DIR, '.icedove')
        >>> PROFILE = os.path.join(ICEDOVE_CONFIG_DIR, 'profile.default')
        >>> TAILS_JS = os.path.join(PROFILE, 'preferences', '0000tails.js')
        >>> lines = set_mozilla_pref(TAILS_JS, "extensions.torbirdy.defaultprotocol", POP)
        >>> len(lines) > 0
        True
        >>> lines = set_mozilla_pref(TAILS_JS, "extensions.torbirdy.defaultprotocol", IMAP)
        >>> len(lines) > 0
        True
    """

    new_lines = []
    named_prefix = '{prefix}("{name}"'.format(prefix=prefix, name=name)

    # delete old lines for this setting
    for line in open(filename):
        if not line.startswith(named_prefix):
            new_lines.append(line)

    # add the new setting
    new_lines.append('{prefix}("{name}", {value});\n'.format(prefix=prefix, name=name, value=value))
    with open(filename, 'w') as f:
        for line in new_lines:
            f.write(line)

    # returned for doctest
    return new_lines

def exec_firefox(*args):
    """
        Execute firefox.

        >>> PROFILE = '{}/.tor-browser/profile.default'.format(os.environ['HOME'])
        >>> exec_firefox(['-allow-remote', '--class', 'Tor Browser', '-profile', PROFILE])
    """
    exec_firefox_helper('firefox', *args)

def exec_unconfined_firefox(*args):
    """
        Execute firefox unconfined.

        >>> PROFILE = '{}/.tor-browser/profile.default'.format(os.environ['HOME'])
        >>> exec_unconfined_firefox(['-app', os.path.join(TOR_LAUNCHER_INSTALL,
        ...                         'application.ini'), '-profile', PROFILE])
    """
    exec_firefox_helper('firefox-unconfined', *args)

def exec_firefox_helper(binary, *args):
    """
        Execute the firefox helper.

        >>> PROFILE = '{}/.tor-browser/profile.default'.format(os.environ['HOME'])
        >>> exec_firefox_helper('firefox', ['-allow-remote', '--class', 'Tor Browser',
        ...                     '-profile', PROFILE])
    """
    if isinstance(args, tuple) and len(args) > 0:
        arg0 = args[0]
        if isinstance(arg0, list):
            args = arg0

    os.environ['LD_LIBRARY_PATH'] = TBB_INSTALL
    os.environ['FONTCONFIG_PATH'] = os.path.join(TBB_INSTALL, 'TorBrowser/Data/fontconfig')
    os.environ['FONTCONFIG_FILE'] = 'fonts.conf'

    os.unsetenv('SESSION_MANAGER')

    # The Tor Browser often assumes that the current directory is
    # where the browser lives, e.g. for the fixed set of fonts set by
    # fontconfig above.
    os.chdir(TBB_INSTALL)

    # From start-tor-browser:
    binary_path = os.path.join(TBB_INSTALL, binary)
    full_args = [binary_path]
    if len(args) > 0:
        full_args = full_args + list(args)

    process_id = os.spawnve(os.P_NOWAIT, binary_path, full_args, os.environ)
    if process_id == 127:
        raise 'Invalid keys or values in environment so unable to start: {}'.format(binary)
    elif process_id == 0:
        raise 'Unable to start: {}'.format(binary)

def guess_best_tor_browser_locale():
    """
        Get the best Tor browser locale.

        >>> guess_best_tor_browser_locale()
        'en-US'
    """
    long_locale = get_long_locale()
    short_locale = get_short_locale(long_locale)

    lang_pack_path = os.path.join(TBB_EXT, 'langpack-{}@firefox.mozilla.org.xpi')
    if os.path.exists(lang_pack_path.format(long_locale)):
        locale = long_locale
    elif os.path.exists(lang_pack_path.format(short_locale)):
        locale = short_locale
    else:
        # If we use locale xx-YY and there is no langpack for xx-YY nor xx
        # there may be a similar locale xx-ZZ that we should use instead.
        reg_ex = r'^langpack-({}-[A-Z]+)@firefox.mozilla.org.xpi$'.format(short_locale)

        # start with the default in case any unexpected errors
        similar_locale = 'en-US'

        files = '\n'.join(os.listdir(TBB_EXT))
        match = re.match(reg_ex, files)
        if match:
            similar_locale = match.group(1)

        while similar_locale.startswith('-'):
            similar_locale = similar_locale[1:]

        locale = similar_locale

    return locale

def guess_best_tor_launcher_locale():
    """
        Get the best Tor launcher locale.

        >>> guess_best_tor_launcher_locale()
        'en-US'
    """
    long_locale = get_long_locale()
    short_locale = get_short_locale(long_locale)

    if os.path.exists(os.path.join(TOR_LAUNCHER_LOCALES_DIR, long_locale)):
        locale = long_locale

    else:
        regex = r'^{}(-[A-Z]+)?$'.format(short_locale)

        files = '\n'.join(os.listdir(TOR_LAUNCHER_LOCALES_DIR))
        match = re.match(reg_ex, files)
        if match:
            locale = match.group(1)
        else:
            locale = 'en-US'

    return locale

def config_best_tor_browser_locale(profile):
    """
        Configure the best Tor browser locale.

        >>> PROFILE = '{}/.tor-browser/profile.default'.format(os.environ['HOME'])
        >>> config_best_tor_browser_locale(PROFILE)
    """
    configure_xulrunner_app_locale(profile, guess_best_tor_browser_locale())

def config_best_tor_launcher_locale(profile):
    """
        Configure the best Tor launcher locale.

        >>> PROFILE = '{}/.tor-browser/profile.default'.format(os.environ['HOME'])
        >>> config_best_tor_launcher_locale(PROFILE)
    """
    configure_xulrunner_app_locale(profile, guess_best_tor_launcher_locale())

def configure_xulrunner_app_locale(profile, locale):
    """
        Configure XUL runner app's locale.

        >>> PROFILE = '{}/.tor-browser/profile.default'.format(os.environ['HOME'])
        >>> js_path = os.path.join(PROFILE, 'preferences/0000locale.js')
        >>> if os.path.exists(js_path):
        ...     os.remove(js_path)
        >>> configure_xulrunner_app_locale(PROFILE, 'de-CH')
        >>> os.path.exists(js_path)
        True
        >>> with open(js_path) as f:
        ...     print(f.read())
        pref("general.useragent.locale", "de-CH")
    """
    prefs_dir = os.path.join(profile, 'preferences')
    if not os.path.exists(prefs_dir):
        os.makedirs(prefs_dir)

    js_path = os.path.join(profile, 'preferences/0000locale.js')
    with open(js_path, 'w') as js_file:
        js_file.write('pref("general.useragent.locale", "{}")'.format(locale))

def supported_tor_browser_locales():
    """
        Determine which locales are supported by the Tor Browser.

        >>> locales = supported_tor_browser_locales()
        >>> len(locales) > 1
        True
    """
    # The default is always supported
    locales = ['en-US']
    for langpack in sh.glob(os.path.join(TBB_EXT, 'langpack-*@firefox.mozilla.org.xpi')):
        basename = os.path.basename(langpack)
        # !! did these '@' chars have special meaning in bash or sed?
        reg_ex = r'^langpack-([^@]+)@.*$'
        match = re.match(reg_ex, basename)
        if match:
            locale = match.group(1)
            locales.append(locale)

    return locales

def get_long_locale():
    """
        Get the long locale from the OS.

        >>> locale = get_long_locale()
        >>> len(locale) > 0
        True
        >>> '_' in locale
        False
    """
    lang = os.environ['LANG']
    parts = lang.split('.')
    return parts[0].replace('_', '-')

def get_short_locale(long_locale):
    """
        Get the short locale from the OS.

        >>> get_short_locale('de-CH')
        'de'
    """
    parts = long_locale.split('-')
    return parts[0]

if __name__ == '__main__':
    # pylint wants this imported at the top, but
    # it's only used for testing so we want to minimize imports
    from doctest import testmod
    testmod()

