#! /usr/bin/python3
'''
    Handle localization.

    Test with "python3 localization.py".

    goodcrypto.com converted from bash to python and added basic tests.
'''
import os
import re

def language_code_from_locale(lang='en'):
    """
        Extracts the language part of a given locale, e.g. "en_US.UTF-8"
        yields "en". Often $LANG will be passed as the argument.

        >>> language_code_from_locale('de_CH.UTF-8')
        'de'
        >>> language_code_from_locale('DE_CH.UTF-8')
        'de'
        >>> language_code_from_locale('de.UTF-8')
        'de'
        >>> language_code_from_locale('de')
        'de'
    """
    m = re.match(r'([a-zA-z]{2}).*', lang)
    if m:
        locale = m.group(1)
    else:
        locale = lang

    return locale.lower()

def localized_tails_doc_page(page):
    """
        Prints the path to the localized (according to the environment's
        LANG) version of `page` in the local copy of Tails' website. `page`
        should specify only the name of the page, not the language code (of
        course!) or the ".html" extension. If a localized page doesn't exist
        the default is the English version.

        >>> page = localized_tails_doc_page('tailsdoc')
        >>> page is None
        True
    """
    page = None

    if 'LANG' in os.environ:
        lang_code = language_code_from_locale(lang=os.environ['LANG'])
    else:
        lang_code = language_code_from_locale()

    for locale in [lang_code, 'en']:
        try_page = '{page}.{locale}.html'.format(page=page, locale=locale)
        if os.path.isfile(try_page):
            page = try_page

    return page

if __name__ == '__main__':
    # pylint wants this imported at the top, but
    # it's only used for testing so we want to minimize imports
    from doctest import testmod
    testmod()

