#! /usr/bin/python
'''
    Boot to kexec.

    Conversion from bash to python by goodcrypto.com
'''

from __future__ import print_function

import os
import re
import sys

import sh

def main(*args):
    """ Boot to kexec

        >>> main('kernel')
    """

    print('Boot to kexec')

    try:
        subsystem = sys.argv[1]

        # possibly refactor. kernel and initrd are handled identically except for regex
        if subsystem == 'kernel':
            boot_kernel = sys.argv[2]
            if running_amd64_kernel():
                print(re.sub(r'/vmlinuz$', '/vmlinuz2', boot_kernel))
            else:
                print(boot_kernel)

        elif subsystem == 'initrd':
            boot_initrd = sys.argv[2]
            if running_amd64_kernel():
                print(re.sub(r'/initrd.img$', '/initrd2.img', boot_initrd))
            else:
                print(boot_initrd)

        else:
            script_name = os.path.basename(sys.argv[0])
            print('Usage: {} kernel|initrd PATH'.format(script_name), file=sys.stderr)
            sys.exit(3)

    except sh.ErrorReturnCode as error:
        if error.stderr:
            print(error.stderr, file=sys.stderr)
        sys.exit(-1)

def running_amd64_kernel():
    """
        Return True if 64 bit, else False.

        >>> running_amd64_kernel()
        True
    """

    kernel_release_name = str(sh.uname('--kernel-release').stdout)
    return 'amd64' in kernel_release_name

if __name__ == '__main__':
    if sys.argv and len(sys.argv) > 1:
        if sys.argv[1] == 'doctest':
            from doctest import testmod
            testmod()
        else:
            main(sys.argv[1:])
    else:
        main([])

    sys.exit(0)

