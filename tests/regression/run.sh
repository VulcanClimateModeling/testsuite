#!/bin/bash

# be loud and exit upon error
set -x
set -e

exe='model.py'
args='--model=cosmo'
testsuite="../../testsuite.py"
config="--config-file=config.cfg"

\rm -f testsuite.out

${testsuite} ${config} -v 1 --color --args="${args}" --tolerance=TOLERANCE --testlist=testlist.xml --mpicmd='' $*

exit 0

