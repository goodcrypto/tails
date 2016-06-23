#! /usr/bin/python3
'''

    IN PROGRESS

    goodcrypto.com started conversion from bash to python.
'''
import argparse
import os
import sys

import sh

# tailslib.cmdline_old and tailslib.misc_helpers have NOT be converted, yet
from tailslib.cmdline_old import Cmdline_old
from tailslib.misc_helpers import (activate_custom_mounts, get_custom_mounts, open_luks_device,
                                   probe_for_gpt_name, removable_dev, removable_usb_dev,
                                   storage_devices, where_is_mounted, custom_overlay_label)


os.environ['PATH'] = '/usr/local/bin:/usr/bin:/bin'
os.environ['TEXTDOMAIN'] = 'tails'

# Set variable names needed by get_custom_mounts(),
# and now initialized by live-boot in a file that we certainly
# don't want to source.
os.environ['persistence_list'] = "persistence.conf"
os.environ['old_persistence_list'] = "nonexistent"

def main(*args):
    # parse the kernel cmdline for live-boot's configuration as defaults
    Cmdline_old()

    os.environ['PERSISTENCE'] = "true"
    os.environ['NOPERSISTENCE'] = ""

    # Should be set empty since live-boot already changed root for us
    os.environ['Nrootmnt'] = ""

    parser = argparse.ArgumentParser(description='Live boot persistence.')

    # no profiling yet
    # parser.add_argument('--log-file', type=int, nargs='*',
    #                    help='log the execution trace to FILE')
    parser.add_argument('--encryption', nargs='*',
                       help="override 'persistent-encryption'")
    parser.add_argument('--media', nargs='*',
                       help="override 'persistent-media'")
    parser.add_argument('--read-only',
                       help="enable 'persistent-read-only'")
    parser.add_argument('--read-write',
                       help="disable 'persistent-read-only'")
    parser.add_argument('--union', nargs='*',
                       help="override 'union'")

    parser.add_argument('action',
                       help='action')
    parser.add_argument('action_args', nargs='*',
                       help='action args')

    args = parser.parse_args()

    # env vars
    if args.encryption:
        os.environ['PERSISTENCE_ENCRYPTION'] = ' '.join(args.encryption)
    if args.media:
        os.environ['PERSISTENCE_MEDIA'] = ' '.join(args.args.media)
    if args.read_only:
        os.environ['PERSISTENCE_READONLY'] = 'true'
    if args.read_write:
        os.environ['PERSISTENCE_READONLY'] = ''
    if args.union:
        os.environ['UNION_TYPE'] = ' '.join(args.union)

    # actions
    if args.action == 'list':
        if args.action_args:
            list_gpt_volumes(*args.action_args)
        else:
            # use default from live-helpers
            list_gpt_volumes(custom_overlay_label)
    elif args.action == 'activate':
        if not args.action_args:
            error('you must specify at least one volume')
        activate_volumes(args.action_args)
    elif args.action == 'close':
        if not args.action_args:
            error('you must specify at least one volume')
        close_volumes(args.action_args)
    elif not args.action:
        error('no action specified')
    else:
        error('unrecognized action: {action}'.format(action=args.action)

def error(args):
    print('error: {}'.format(' '.join(args)), file=sys.stderr)
    sys.exit(1)

def usage():
    cmd=${0##*/}
    echo "Usage: ${cmd} [OPTION]... list [LABEL]...
List (on stdout) all GPT partitions with names among LABEL(s) that are
compatible with live-boot's overlay persistence, and that are adhering to
live-boot's persistence filters (e.g. persistent-media). If no LABEL is given
the default in live-boot is used ('${custom_overlay_label}').
   or: ${cmd} [OPTION]... activate VOLUME...
Activates persistence on the given VOLUME(s). Successes and failures are
written to stdout. There are no checks for whether the given volumes adhere
to live-boot's options.

Kernel command-line options are parsed just like in live-boot and have the same
effect (see live-boot(7) for more information)

Arguments to options must be passed using an equality sign. LISTs are coma
separated. Most options correspond to the persistent-* options of live-boot,
and will override the corresponging options parsed from the kernel command-line.

General options:
  --help                display this help and exit
  --log-file=FILE       log the bash execution trace to FILE

Options affecting the 'list' action:
  --encryption=LIST     override 'persistent-encryption'
  --media=VALUE         override 'persistent-media'

Options affecting the 'activate' action:
  --read-only           enable 'persistent-read-only'
  --read-write          disable 'persistent-read-only'
  --union=VALUE         override 'union'
"

def escape_dots(arg):
    return '{}\n'.format(arg.replace('.', '\\.'))

def migrate_persistence_preset(old_preset, old_preset_source, new_preset, new_preset_source, config):
    if sh.grep('-E', '-qs', '--line-regex',
        '-e', "escape_dots(old_preset)\s+source=old_preset_source",
        "$config" \
        && ! grep -E -qs --line-regex \
        -e "$(escape_dots ${new_preset)\s+source=${new_preset_source}" \
        "$config":
        warning("Need to make {} persistent".format(new_preset))
        if os.environ.['PERSISTENCE_READONLY'] == 'true':
            warning("Persistence configuration needs to be migrated, but read only was selected; please retry in read-write mode")
        else:
            echo "$NEW_PRESET   source=$NEW_PRESET_SOURCE" \
                >> "$CONFIG" \
                || error "Failed to make $NEW_PRESET: $?"
            warning "Successfully made $NEW_PRESET persistent"

def warning(args):
    print("warning: {}".format(args), file=sys.stderr)

# We override live-boot's logging facilities to get more useful error messages
def log_warning_msg(args):
    warning(args)

# We override live-boot's panic() since it does a lot of crazy stuff
def panic(args):
    error(args)

def list_gpt_volumes(labels):

    whitelistdev = ""
    case "${PERSISTENCE_MEDIA}" in
        removable)
            whitelistdev="$(removable_dev)"
            [ -z "${whitelistdev}" ] && return
            ;;
        removable-usb)
            whitelistdev="$(removable_usb_dev)"
            [ -z "${whitelistdev}" ] && return
            ;;
        *)
            if grep -qs -w -E '(live-media|bootfrom)=removable-usb' /proc/cmdline ; then
                whitelistdev="$(removable_usb_dev)"
                [ -z "${whitelistdev}" ] && return
            elif grep -qs -w -E '(live-media|bootfrom)=removable' /proc/cmdline ; then
                whitelistdev="$(removable_dev)"
                [ -z "${whitelistdev}" ] && return
            else
                whitelistdev=""
            fi
            ;;
    esac

    for dev in $(storage_devices "" "${whitelistdev}")
    do
        if ( is_luks_partition ${dev} >/dev/null 2>&1 && \
             echo ${PERSISTENCE_ENCRYPTION} | grep -qve "\<luks\>" ) || \

           ( ! is_luks_partition ${dev} >/dev/null 2>&1 && \
             echo ${PERSISTENCE_ENCRYPTION} | grep -qve "\<none\>" )
        then
            continue
        fi
        local result="$(probe_for_gpt_name "${labels}" ${dev})"
        if [ -n "${result}" ]
        then
            echo ${result#*=}
        fi
    done

    exit 0
}

def mountpoint_has_correct_access_rights(mountpoint):

    result = 0
    expected_user = 'root'
    expected_group = 'root'
    expected_perms = 775
    expected_acl = "user::rwx
user:tails-persistence-setup:rwx
group::rwx
mask::rwx
other::r-x"

    if sh.stat('-c', '%U', mountpoint) != expected_user:
        warning('{} is not owned by the "{}" user'.format(mountpoint, expected_user))
        result = 1
    elif sh.stat('-c', '%G', mountpoint) != expected_group:
        warning('{} is not owned by the "{}" group'.format(mountpoint, expected_group))
        result = 2
    elif sh.stat('-c', '%a', mountpoint) != expected_perms:
        warning('{} permissions are not {}'.format(mountpoint, expected_perms))
        result = 4
    elif sh.getfacl('--omit-header', '--skip-base', mountpoint) | grep -v '^\s*$') != expected_acl:
        warning('{} permissions has incorrect ACL'.format(mountpoint))
        result = 8

    return result

def persistence_conf_file_has_correct_access_rights(conf):
    result = 0
    expected_user = 'tails-persistence-setup'
    expected_group = 'tails-persistence-setup'
    expected_perms = 600
    expected_acl = ''

    if sh.stat('-c', '%U', conf) != expected_user:
        warning('{} is not owned by the "{}" user'.format(conf, expected_user))
        result = 1
    elif sh.stat('-c', '%G', conf) != expected_group:
        warning('{} is not owned by the "{}" group'.format(conf, expected_group))
        result = 2
    if  sh.stat('-c', '%a', conf) != expected_perms:
        warning('{} permissions are not {}'.format(conf, expected_perms))
        result = 4
    if sh.getfacl('--omit-header', '--skip-base', conf) | grep -v '^\s*$')" != "$expected_acl:
        warning('{} permissions has incorrect ACL'.format(conf))
        result = 8

    return result

def disable_and_create_empty_persistence_conf_file(conf):

    mv "$conf" "${conf}.insecure_disabled" \
        || error "Failed to disable '$conf': $?"
    install --owner tails-persistence-setup \
        --group tails-persistence-setup --mode 0600 \
        /dev/null "$conf" \
        || error "Failed to create empty '$conf': $?"
}

def activate_volumes(volumes):
    ret=0
    open_volumes=""
    successes=""
    failures=""

    # required by open_luks_device()
    exec 6>&1

    for vol in ${volumes}
    do
        if [ ! -b "${vol}" ]
        then
            warning "${vol} is not a block device"
            failures="${failures} ${vol}"
            ret=1
            continue
        fi
        if [ -n "$(what_is_mounted_on ${dev})" ]
        then
            warning "${vol} is already mounted"
            failures="${failures} ${vol}"
            ret=1
            continue
        fi
        local luks_vol=""
        if /sbin/cryptsetup isLuks ${vol} >/dev/null 2>&1
        then
            if luks_vol=$(open_luks_device "${vol}")
            then
                open_volumes="${open_volumes} ${luks_vol}"
            else
                failures="${failures} ${vol}"
            fi
        else
            open_volumes="${open_volumes} ${vol}"
        fi
    done

    custom_mounts="$(mktemp /tmp/custom_mounts-XXXXXX.list)"
    get_custom_mounts ${custom_mounts} ${open_volumes}
    # ... and now the persistent volumes should be mounted.

    # Enable the acl mount option on all persistent filesystems.
    for mountpoint in $(ls -d /live/persistence/*_unlocked || true)
    do
        mount -o remount,acl "$mountpoint"
    done

    # Detect if we have incorrect ownership, permissions and ACL.
    ACCESS_RIGHTS_ARE_CORRECT=true
    for mountpoint in $(ls -d /live/persistence/*_unlocked || true)
    do
        if ! mountpoint_has_correct_access_rights "$mountpoint"
        then
            ACCESS_RIGHTS_ARE_CORRECT=false
            break
        fi
    done

    # Disable all persistence configuration files if the mountpoint
    # has wrong access rights.
    if [ "$ACCESS_RIGHTS_ARE_CORRECT" != true ]
    then
        for f in $(ls /live/persistence/*_unlocked/persistence.conf \
                      /live/persistence/*_unlocked/live-additional-software.conf || true)
        do
            warning "Disabling '$f': persistent volume has unsafe access rights"
            disable_and_create_empty_persistence_conf_file "$f"
        done
    fi

    # Regardless of the mountpoint access rights, disable persistence
    # configuration files with wrong access rights.
    for f in $(ls /live/persistence/*_unlocked/persistence.conf \
                  /live/persistence/*_unlocked/live-additional-software.conf || true)
    do
        if ! persistence_conf_file_has_correct_access_rights "$f"
        then
            warning "Disabling '$f', that has unsafe access rights"
            disable_and_create_empty_persistence_conf_file "$f"
        fi
    done

    for conf in $(ls /live/persistence/*_unlocked/persistence.conf || true)
    do
        # Migrate Squeeze-era NetworkManager persistence setting to Wheezy.
        migrate_persistence_preset '/home/amnesia/.gconf/system/networking/connections' 'nm-connections' \
            '/etc/NetworkManager/system-connections' 'nm-system-connections' "$conf"
        # disable pre-Wheezy NM persistence setting
        sed -r -i \
            -e 's,^(/home/amnesia/\.gconf/system/networking/connections\s+source=nm-connections)$,#\1,' \
            "$conf"

        # Migrate Claws-mail persistence setting to Icedove
        migrate_persistence_preset '/home/amnesia/.claws-mail' 'claws-mail' \
            '/home/amnesia/.icedove' 'icedove' "$conf"
    done

    # Fix permissions on persistent directories that were created
    # with unsafe permissions.
    for persistent_fs in $(ls -d /live/persistence/*_unlocked || true)
    do
        [ -d "$persistent_fs" ] || continue
        for child in $(ls "$persistent_fs" || true)
        do
            subdir="$persistent_fs/$child"
            [ -d "$subdir" ] || continue
            # Note: we chmod even custom persistent directories.
            # This may break things by changing otherwise correct
            # permissions copied from the directory that was made
            # persistent, so we only do that if the persistent directory
            # is owned by amnesia:amnesia, and thus unlikely to be
            # a system directory. This e.g. avoids setting wrong
            # permissions on the APT, CUPS and NetworkManager
            # persistent directories.
            [ $(stat -c '%U' "$subdir") = 'amnesia' ] || continue
            [ $(stat -c '%G' "$subdir") = 'amnesia' ] || continue
            if [ "$PERSISTENCE_READONLY" = true ]
            then
                warning "Permissions of '$subdir' may need to be fixed, but read only was selected; please retry in read-write mode"
            else
                chmod go= "$subdir"
            fi
        done
    done

    # Load the new persistence.conf.
    custom_mounts="$(mktemp /tmp/custom_mounts-XXXXXX.list)"
    get_custom_mounts ${custom_mounts} ${open_volumes}

    if [ -s "${custom_mounts}" ]
    then
        OLD_UMASK="$(umask)"
        # Have activate_custom_mounts create new directories
        # with safe permissions (#7443)
        umask 0077
        activate_custom_mounts ${custom_mounts} &> /dev/null
        umask "$OLD_UMASK"
    fi
    rm -f ${custom_mounts} 2> /dev/null

    for vol in ${open_volumes}
    do
        if grep -qe "^${vol}\>" /proc/mounts
        then
            successes="${successes} ${vol}"
        else
            failures="${failures} ${vol}"
            ret=1
        fi
    done

    if [ -n "${successes}" ]
    then
        echo "Successes:"
        for vol in ${successes}
        do
            echo "  - ${vol}"
        done
    fi

    if [ -n "${failures}" ]
    then
        echo "Failures:"
        for vol in ${failures}
        do
            echo "  - ${vol}"
        done
    fi
    exit ${ret}

def close_volumes(volumes):
    custom_mounts="$(mktemp /tmp/custom_mounts-XXXXXX.list)"
    get_custom_mounts ${custom_mounts} ${volumes}
    while read device source dest options # < ${custom_mounts}
    do
        if [ "${options}" != linkfiles ]
        then
            umount ${dest} 2> /dev/null
        fi
    done < ${custom_mounts}
    rm -f ${custom_mounts} 2> /dev/null
    for vol in ${volumes}
    do
        local backing=$(where_is_mounted ${vol})
        umount ${backing}
    done

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
        usage()

