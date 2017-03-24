#!/usr/bin/env python2

"""
COSMO TECHNICAL TESTSUITE

Error classes used for exception handling
"""

# built-in modules
import re

# information
__author__     = "Nicolo Lardelli, Xavier Lapillonne"
__copyright__  = "Copyright 2012, COSMO Consortium"
__license__    = "GPL"
__version__    = "1.0"
__date__       = "Mon Oct  8 15:37:57 CEST 2012"
__email__      = "cosmo-wg6@cosmo.org"
__maintainer__ = "xavier.lapillonne@meteoswiss.ch"


class SkipError(RuntimeError):
    """Exception when a test has to be skipped (not applicable or unmatched requirement"""
    pass

class StopError(RuntimeError):
    """Exception when a test has encountered an error"""
    pass


