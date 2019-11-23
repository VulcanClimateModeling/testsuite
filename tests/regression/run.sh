#!/bin/bash

# be loud and exit upon error
set -x
set -e

exe='model.py'
args='--model=cosmo'
testsuite="../../testsuite.py"
config="--config-file=config.cfg"

\rm -f testsuite.out

${testsuite} ${config} -n 6 --nprocio 0 -v 1 --color -f --exe="${exe}" --args="${args}" --tolerance=TOLERANCE --testlist=testlist.xml --mpicmd='' $*

exit 0

