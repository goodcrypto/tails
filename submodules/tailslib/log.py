#! /usr/bin/python3
'''
    Log messages.

    goodcrypto.com converted from bash to python and added basic tests.
'''
import sys
import sh

_LOG_TAG = None

def warn(*args):
    '''
        Print warnings.

        >>> warn('warning')
        ('warning',)
    '''
    print(args, file=sys.stderr)

def die(*args):
    '''
        Print warnings and exit program.

        >>> try:
        ...     die('dying')
        ... except SystemExit:
        ...     pass
        (('dying',),)
    '''
    warn(args)
    sys.exit(1)

def set_log_tag(tag):
    '''
        Shouldn't be used in shell libraries; a script including such a
        library would overwrite the library's log tag.

        >>> set_log_tag('TEST')
        'TEST'
    '''
    global _LOG_TAG

    _LOG_TAG = tag

    # just for testing
    return _LOG_TAG

def log(*args):
    '''
        Log a message.

        log('hello')
    '''
    global _LOG_TAG

    if _LOG_TAG is None:
        sh.logger(*args)
    else:
        sh.logger('-t', _LOG_TAG, args)

if __name__ == '__main__':
    # pylint wants this imported at the top, but
    # it's only used for testing so we want to minimize imports
    from doctest import testmod
    testmod()

