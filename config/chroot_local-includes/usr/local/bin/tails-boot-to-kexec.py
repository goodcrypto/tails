#! /usr/bin/python3
'''
    Boot to kexec.

    Test with "python3 tails-boot-to-kexec.py doctest".

    goodcrypto.com converted from bash to python and added basic tests.
'''
import os
import re
import sys

import sh

def main(args):
    """ Boot to kexec

        >>> main(['tails-boot-to-kexec', 'kernel', '/vmlinuz'])
        /vmlinuz
        >>> main(['tails-boot-to-kexec', 'initrd', '/vmlinuz'])
        /vmlinuz
        >>> try:
        ...     main(['tails-boot-to-kexec', 'test', '/vmlinuz'])
        ...     fail()
        ... except SystemExit:
        ...     pass
    """
    subsystem = args[1]
    if subsystem == 'kernel' or subsystem == 'initrd':
        path = args[2]

        if running_amd64_kernel():
            if subsystem == 'kernel':
                print(re.sub(r'/vmlinuz$', '/vmlinuz2', path))
            elif subsystem == 'initrd':
                print(re.sub(r'/initrd.img$', '/initrd2.img', path))
        else:
            print(path)
    else:
        script_name = os.path.basename(args[0])
        print('Usage: {} kernel|initrd PATH'.format(script_name), file=sys.stderr)
        sys.exit(3)

def running_amd64_kernel():
    """
        Return True if 64 bit, else False.

        >>> running_amd64_kernel()
        False
    """
    try:
        kernel_release_name = sh.uname('--kernel-release').stdout.decode()
        return 'amd64' in kernel_release_name
    except sh.ErrorReturnCode as error:
        if error.stderr:
            print(error.stderr, file=sys.stderr)
        sys.exit(-1)

if __name__ == '__main__':
    if sys.argv and len(sys.argv) > 1:
        if sys.argv[1] == 'doctest':
            from doctest import testmod
            testmod()
        else:
            main(sys.argv)
        sys.exit(0)
    else:
        print('Usage: tails-boot-to-kexec kernel|initrd PATH')
        sys.exit(-1)

