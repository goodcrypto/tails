#! /usr/bin/python3
'''
    Handle running the browser in the chroot.

    Test with "python3 chroot_browser.py" as root.

    goodcrypto.com converted from bash to python and added basic tests.
'''
from glob import glob
import os
import re
import sys
from tempfile import TemporaryDirectory

import sh

# sanitize PATH before executing any other code
os.environ['PATH'] = '/usr/local/sbin:/usr/local/bin:/usr/bin:/bin'

PYTHON_LIB = '/usr/local/lib/python3.4/dist-packages'
TAILSLIB = os.path.join(PYTHON_LIB, 'tailslib')

who = sh.whoami().stdout.decode().strip()
if who != "root":
    print('This library is useless for non-root users. Exiting...', file=sys.stderr)
    sys.exit(1)

from tailslib.common import try_for
from tailslib.tor_browser import (configure_xulrunner_app_locale, guess_best_tor_browser_locale,
                                  TBB_EXT, TBB_INSTALL, TBB_PROFILE)

def try_cleanup_browser_chroot(chroot, cow, user):
    """
        Break down the chroot and kill all of its processes

        >>> TMP_DIR = '/tmp/nobody'
        >>> if not os.path.exists(TMP_DIR):
        ...     os.mkdir(TMP_DIR)
        >>> try_cleanup_browser_chroot('', TMP_DIR, 'nobody')
    """
    try_for(10, ['pkill', '-u', user], 0.1) or sh.pkill('-9', '-u', user, _ok_code=[0, 1])
    for mnt in ['{}/dev'.format(chroot), '{}/proc'.format(chroot), chroot, cow]:
        try_for(10, ['umount', mnt], 0.1)

    if os.path.exists(cow):
        try:
            os.rmdir(cow)
        except:
            pass
    # don't all the root directory to be removed
    # and don't get when our simple test doesn't pass a chroot dir
    if chroot != '/' and len(chroot) > 0:
        try:
            os.rmdir(chroot)
        except:
            pass

def setup_chroot_for_browser(chroot, cow, user):
    """
        Setup a chroot on a clean aufs "fork" of the root filesystem.

        FIXME: When LXC matures to the point where it becomes a viable option
        for creating isolated jails, the chroot can be used as its rootfs.

        >>> CONF_DIR = "/var/lib/unsafe-browser"
        >>> COW = os.path.join(CONF_DIR, 'cow')
        >>> CHROOT = os.path.join(CONF_DIR, 'chroot')
        >>> BROWSER_USER = 'clearnet'
        >>> try_cleanup_browser_chroot(CHROOT, COW, BROWSER_USER)
        >>> result = setup_chroot_for_browser(CHROOT, COW, BROWSER_USER)
        >>> result = sh.umount('aufs', _ok_code=[0,32])
        >>> result = sh.umount('tmpfs', _ok_code=[0,32])
    """

    rootfs_dirs_path = "/lib/live/mount/rootfs"
    tails_module_path = "/lib/live/mount/medium/live/Tails.module"
    aufs_dirs = ''

    # We have to pay attention to the order we stack the filesystems;
    # newest must be first, and remember that the .module file lists
    # oldest first, newest last.
    for line in open(tails_module_path):
        rootfs_dir = os.path.join(rootfs_dirs_path, line.strip())
        try:
            sh.mountpoint(rootfs_dir)
        except sh.ErrorReturnCode as erc:
            pass
        else:
            aufs_dirs = '{}=rr+wh:{}'.format(rootfs_dir, aufs_dirs)
    # But our copy-on-write dir must be at the very top.
    aufs_dirs = '{}=rw:{}'.format(cow, aufs_dirs)

    try:
        os.makedirs(chroot, exist_ok=True)
        os.makedirs(cow, exist_ok=True)

        sh.mount('-t', 'tmpfs', 'tmpfs', cow)
        sh.mount('-t', 'aufs',
                 '-o', 'noatime,noxino,dirs={}'.format(aufs_dirs),
                 'aufs', chroot)

        proc_dir = os.path.join(chroot, 'proc')
        if not os.path.exists(proc_dir):
            os.mkdir(proc_dir)
        sh.mount('-t', 'proc', 'proc', '{}'.format(proc_dir))

        dev_dir = os.path.join(chroot, 'dev')
        if not os.path.exists(dev_dir):
            os.mkdir(dev_dir)
        sh.mount('--bind', '/dev' '{}'.format(dev_dir))

    except sh.ErrorReturnCode as erc:
        # we may want less info, but probably not until this code is well tested
        # print(erc.stderr.strip(), file=sys.stderr)
        # sys.exit(3)
        return 1

    else:

        # Workaround for #6110
        # what does a "-t" do? man page doesn't document it as an option
        sh.chmod('-t', cow)

def browser_conf_dir(browser_name, browser_user):
    """
        Get the full path for the browser config dir.

        >>> browser_conf_dir('tor-browser', 'amnesia')
        '/home/amnesia/.tor-browser'
    """
    return '/home/{}/.{}'.format(browser_user, browser_name)


def browser_profile_dir(browser_name, browser_user):
    """
        Get the full path for the browser profile dir.

        >>> browser_profile_dir('tor-browser', 'amnesia')
        '/home/amnesia/.tor-browser/profile.default'
    """
    conf_dir = browser_conf_dir(browser_name, browser_user)
    return os.path.join(conf_dir, 'profile.default')

def chroot_browser_conf_dir(chroot, browser_name, browser_user):
    """
        Get the full path for the browser config dir in the chroot.

        >>> chroot_browser_conf_dir('/chroot', 'tor-browser', 'amnesia')
        '/chroot/home/amnesia/.tor-browser'
    """
    conf_dir = browser_conf_dir(browser_name, browser_user)
    return '{}{}'.format(chroot, conf_dir)

def chroot_browser_profile_dir(chroot, browser_name, browser_user):
    """
        Get the full path for the browser profile dir in the chroot.

        >>> chroot_browser_profile_dir('/chroot', 'tor-browser', 'amnesia')
        '/chroot/home/amnesia/.tor-browser/profile.default'
    """
    conf_dir = chroot_browser_conf_dir(chroot, browser_name, browser_user)
    return os.path.join(conf_dir, 'profile.default')

def configure_chroot_dns_servers(chroot, ip4_nameservers):
    """
        Set the chroot's DNS servers (IPv4 only)

        >>> configure_chroot_dns_servers('/', '123.45.67.890 987.65.43.21')
    """
    RESOLV_CONF = os.path.join(chroot, 'etc/resolv.conf')
    if os.path.exists(RESOLV_CONF):
        os.remove(RESOLV_CONF)

    with open(RESOLV_CONF, 'w') as f:
        for ns in ip4_nameservers.split(' '):
            f.write('nameserver {}\n'.format(ns))
    sh.chmod('a+r', RESOLV_CONF)

def set_chroot_browser_permissions(chroot, browser_name, browser_user):
    """
        Set the chroot's browser permissions.

        >>> set_chroot_browser_permissions('/', 'tor-browser', 'amnesia')
    """
    browser_conf = chroot_browser_conf_dir(chroot, browser_name, browser_user)
    sh.chown('-R', '{}:{}'.format(browser_user, browser_user), browser_conf)

def configure_chroot_browser_profile(chroot, browser_name, browser_user, home_page, extensions):
    """
        Configure the browser profile in the chroot.

        >>> from glob import glob
        >>> configure_chroot_browser_profile('/', 'unsafe-browser', 'amnesia',
        ...   'https://tails.boum.org', glob(TBB_EXT+'/langpack-*.xpi'))
    """
    def cat_files(file1, file2, output, mode):
        with open(file1) as f:
            lines1 = f.readlines()
        with open(file2) as f:
            lines2 = f.readlines()
        with open(output, mode) as f:
            for line in lines1:
                f.write(line)
            for line in lines2:
                f.write(line)

    # Prevent sudo from complaining about failing to resolve the 'amnesia' host
    with open(os.path.join(chroot, 'etc/hosts'), 'a') as output:
        output.write("127.0.0.1 localhost amnesia\n")

    # Create a fresh browser profile for the clearnet user
    browser_profile = chroot_browser_profile_dir(chroot, browser_name, browser_user)
    browser_ext = os.path.join(browser_profile, 'extensions')
    os.makedirs(browser_profile, exist_ok=True)
    os.makedirs(browser_ext, exist_ok=True)

    # Select extensions to enable
    for extension in extensions:
        sh.ln('--symbolic', '--force', extension, browser_ext)

    # Set preferences
    browser_prefs = os.path.join(browser_profile, 'preferences', 'prefs.js')
    browser_prefs_dir = os.path.dirname(browser_prefs)
    chroot_browser_config = '/usr/share/tails/chroot-browsers'
    os.makedirs(browser_prefs_dir, exist_ok=True)
    cat_files(os.path.join(chroot_browser_config, 'common', 'prefs.js'),
              os.path.join(chroot_browser_config, browser_name, 'prefs.js'),
              browser_prefs, 'wt')

    # Set browser home page to something that explains what's going on
    if len(home_page) > 0:
        with open(browser_prefs, 'at') as f:
            f.write('user_pref("browser.startup.homepage", "{}");\n'.format(home_page))

    # Remove all bookmarks
    bookmark_file = os.path.join(chroot, TBB_PROFILE, 'bookmarks.html')
    if os.path.exists(bookmark_file):
        os.remove(bookmark_file)

    # Set an appropriate theme
    browser_theme_file = os.path.join(chroot_browser_config, browser_name, 'theme.js')
    if os.path.exists(browser_theme_file):
        with open(browser_theme_file) as f:
            content = f.read()
        with open(browser_prefs, 'at') as f:
            f.write(content)

    # Customize the GUI.
    browser_chrome = os.path.join(browser_profile, 'chrome', 'userChrome.css')
    browser_chrome_dir = os.path.dirname(browser_chrome)
    os.makedirs(browser_chrome_dir, exist_ok=True)
    cat_files(os.path.join(chroot_browser_config, 'common', 'userChrome.css'),
              os.path.join(chroot_browser_config, browser_name, 'userChrome.css'),
              browser_chrome, 'at')

    set_chroot_browser_permissions(chroot, browser_name, browser_user)

def set_chroot_browser_locale(chroot, browser_name, browser_user, locale):
    """
        Set the locale for the chroot's browser.

        >>> set_chroot_browser_locale('/', 'tor-browser', 'amnesia', 'de')
    """
    browser_profile = chroot_browser_profile_dir(chroot, browser_name, browser_user)
    configure_xulrunner_app_locale(browser_profile, locale)

def set_chroot_browser_name(chroot, human_readable_name, browser_name, browser_user, locale):
    """
        Must be called after configure_chroot_browser_profile(), since it
        depends on which extensions are installed in the profile.

        >>> set_chroot_browser_name('/', 'Tor Browser', 'tor-browser', 'amnesia', 'de')
    """
    ext_dir = os.path.join(chroot, TBB_EXT)
    browser_profile_ext_dir = chroot_browser_profile_dir(
       chroot, browser_name, '{}/extensions'.format(browser_user))

    # If Torbutton is installed in the browser profile, it will decide
    # the browser name.
    if os.path.exists('{}/torbutton@torproject.org'.format(browser_profile_ext_dir)):
        torbutton_locale_dir = '{}/torbutton/chrome/locale/{}'.format(ext_dir, locale)
        if not os.path.exists(torbutton_locale_dir):
            # Surprisingly, the default locale is en, not en-US
            torbutton_locale_dir = '{}/usr/share/xul-ext/torbutton/chrome/locale/en'.format(chroot)
        filename = os.path.join(torbutton_locale_dir, 'brand.dtd')
        update_brand_name(human_readable_name, filename)

        # Since Torbutton decides the name, we don't have to mess with
        # with the browser's own branding, which will save time and
        # memory.
    else:
        if locale != 'en-US':
            pack = '{}/langpack-{}@firefox.mozilla.org.xpi'.format(ext_dir, locale)
            top = 'browser/chrome'
            rest = '{}/locale'.format(locale)
        else:
            pack = '{}/{}/browser/omni.ja'.format(chroot, TBB_INSTALL)
            top = 'chrome'
            rest = 'en-US/locale'

        with TemporaryDirectory() as tmp:
            branding = '{top}/{rest}/branding/brand.dtd'.format(top=top, rest=rest)
            seven_zip = sh.Command('/usr/bin/7z')
            seven_zip('x', '-o{}'.format(tmp), pack, branding)
            branding_file = os.path.join(tmp, branding)
            update_brand_name(human_readable_name, branding_file)
            os.chdir(tmp)
            seven_zip('u', '-tzip', pack, '.')
            sh.chmod('a+r', pack)

def update_brand_name(human_readable_name, filename):
    """
        Update the name of the brand.

        >>> human_readable_name = 'Tor Browser'
        >>> filename = '/tmp/branding'
        >>> with open(filename, 'w') as output:
        ...    bytes = output.write('<!ENTITY brandFullName "tor browser">\\n')
        ...    bytes = output.write('<!ENTITY brandShortName "tor">\\n')
        >>> update_brand_name(human_readable_name, filename)
        True
        >>> with open(filename, 'r') as input:
        ...    lines = input.readlines()
        >>> FULL_BRAND_LINE = '<!ENTITY brandFullName "Tor Browser">\\n'
        >>> SHORT_BRAND_LINE = '<!ENTITY brandShortName "Tor Browser">\\n'
        >>> for line in lines:
        ...    line == FULL_BRAND_LINE or line == SHORT_BRAND_LINE
        True
        True
        >>> os.remove(filename)
    """
    if os.path.exists(filename):
        with open(filename) as infile:
            lines = infile.readlines()

        with open(filename, 'w') as outfile:
            for line in lines:
                m = re.match(r'.*?ENTITY\s+brand(Full|Short)Name (".*?")', line)
                if m:
                    outfile.write(line.replace(m.group(2), '"{}"'.format(human_readable_name)))
                else:
                    outfile.write(line)

        result = True
    else:
        result = False

    return result

def configure_chroot_browser(
      chroot, browser_user, browser_name, human_readable_name, home_page, dns_servers, paths):
    """
        Configure the browser in the chroot.

        >>> from glob import glob
        >>> chroot = '/'
        >>> chroot_user = 'root'
        >>> browser_user = 'amnesia'
        >>> browser_name = 'unsafe-browser'
        >>> human_readable_name = 'Unsafe Browser'
        >>> home_page = 'https://tails.boum.org'
        >>> dns_servers = '127.0.0.1'
        >>> paths = glob(TBB_EXT+'/langpack-*.xpi')
        >>> configure_chroot_browser(chroot, browser_user, browser_name,
        ...    human_readable_name, home_page, dns_servers, paths)
    """

    best_locale = guess_best_tor_browser_locale()
    configure_chroot_dns_servers(chroot, dns_servers)
    configure_chroot_browser_profile(chroot, browser_name, browser_user, home_page, paths)
    set_chroot_browser_locale(chroot, browser_name, browser_user, best_locale)
    set_chroot_browser_name(chroot, human_readable_name, browser_name, browser_user, best_locale)
    set_chroot_browser_permissions(chroot, browser_name, browser_user)

def run_browser_in_chroot(chroot, browser_name, chroot_user, local_user):
    """
        Start the browser in the chroot

        >>> chroot = '/var/lib/unsafe-browser/chroot'
        >>> browser_name = 'unsafe-browser'
        >>> chroot_user = 'clearnet'
        >>> local_user = 'amnesia'
        >>> run_browser_in_chroot(chroot, browser_name, chroot_user, local_user)
    """
    TOR_BROWSER = os.path.join(TAILSLIB, 'tor_browser.py')

    profile = browser_profile_dir(browser_name, chroot_user)
    display = os.environ['DISPLAY']

    sh.sudo('-u', local_user, 'xhost', '+SI:localuser:{}'.format(chroot_user))
    chroot_command = sh.Command('/usr/sbin/chroot')
    try:
        tor_browser_args = ['-DISPLAY={}'.format(display), '-profile', profile]
        chroot_command(chroot, 'sudo', '-u', chroot_user,
            '/usr/bin/python3', TOR_BROWSER, tor_browser_args)
    except:
        from traceback import format_exc
        print(format_exc())
        raise
    sh.sudo('-u', local_user, 'xhost', '-SI:localuser:{}'.format(chroot_user))

if __name__ == '__main__':
    # pylint wants this imported at the top, but
    # it's only used for testing so we want to minimize imports
    from doctest import testmod
    testmod()

