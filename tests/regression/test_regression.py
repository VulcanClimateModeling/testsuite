#!/usr/bin/env python3

import pytest

# We should test the following patterns in the XML file
# - description
# - prerun
# - namelistdir
# - refoutdir
# - depend
# - executable
# - nprocs
# - autoparallel
# - checker, ...
# - changepar, ...

# We should test the following command line arguments
# -n NPROCS
# --nprocio=NPROCIO
# -f, --force
# --mpicmd=MPICMD
# --exe=EXE
# --args=ARGS
# --steps=STEPS
# -w, --wrapper
# -o STDOUT
# -a, --append
# --only=cosmo7,test_1
# --update-namelist
# --force-match
# --force-match-base
# --tune-thresholds
# --tuning-iterations=#
# --update-thresholds
# --reset-thresholds
# --update-yufiles
# -l TESTLIST, --testlist=TESTLIST
# -t TIMEOUT, --timeout=TIMEOUT
# --workdir=WORKDIR
# --tolerance=TOLERANCE
# --icon
# --config-file=CONFIG_FILE

def test_true():
    pass
