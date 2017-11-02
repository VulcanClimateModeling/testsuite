#!/bin/bash

# COSMO TECHNICAL TESTSUITE
#
# This script checks whether the results of the output lay in a realistic range. 
# The SAMOA (SAnity check for MOdels of the Atmosphere) package is used for this purpose.
#

# Author       Burkhardt Rockel
# Maintainer   burkhardt.rockel@hzg.de

# check environment variables
RUNDIR=${TS_RUNDIR}
if [ -z "${RUNDIR}" ] ; then
  echo "Environment variable TS_RUNDIR is not set" 1>&1
  exit 20 # FAIL
fi
if [ ! -d "${RUNDIR}" ] ; then
  echo "Directory TS_RUNDIR=${RUNDIR} does not exist" 1>&1
  exit 20 # FAIL
fi

src/checkers/samoa.sh --skull_off -cdf --equl_val_test_of -m -l src/checkers/samoa.list ${RUNDIR}/output/*.nc >> ${RUNDIR}/samoa.log 2>&1
ERROR_STATUS=$?
if [ $ERROR_STATUS -ne 0 ]
  then
  echo ${RUNDIR}samoa.log
  exit 20 # FAIL
else
  exit 0 # MATCH
  fi

