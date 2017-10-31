#!/bin/bash

# COSMO TECHNICAL TESTSUITE
#
# Software dependencies:
#
# - to be run from the bourne shell
# - CDO (Climate Data Operators, <http://code.zmaw.de/projects/cdo>) 
#   Version 1.5 needed for GRIB files!
#   CDO needs to be built with GRIB and/or netCDF support
# This script checks whether the content of NetCDF/GRIB files is identical
# David Leutwyler, October 2017

#Software
cdo=/apps/dom/UES/jenkins/6.0.UP04/gpu/easybuild/software/CDO/1.9.0-CrayGNU-17.08/bin/cdo

# check environment variables
RUNDIR=${TS_RUNDIR}
REFOUTDIR=${TS_REFOUTDIR}
VERBOSE=${TS_VERBOSE}

if [ -z "${VERBOSE}" ] ; then
  echo "Environment variable TS_VERBOSE is not set" 1>&1
  exit 20 # FAIL
fi

if [ -z "${RUNDIR}" ] ; then
  echo "Environment variable TS_RUNDIR is not set" 1>&1
  exit 20 # FAIL
fi
if [ ! -d "${RUNDIR}" ] ; then
  echo "Directory TS_RUNDIR=${RUNDIR} does not exist" 1>&1
  exit 20 # FAIL
fi

if [ -z "${REFOUTDIR}" ] ; then
  echo "Environment variable TS_REFOUTDIR is not set" 1>&1
  exit 20 # FAIL
fi
if [ ! -d "${REFOUTDIR}" ] ; then
  echo "Directory TS_REFOUTDIR=${REFOUTDIR} does not exist" 1>&1
  exit 20 # FAIL
fi

#Regular expression tagging NetCDF and GRIB output files based on their name, but not binary restart
REGEXP='^.*lff[fd][0-9]+[a-zA-Z]{0,1}(.nc){0,1}'

FILELIST=$(find ${RUNDIR}/output -regextype posix-extended -regex $REGEXP)
if [ -z "$FILELIST" ] ; then
  echo "No NetCDF/GRIB output file found in " ${RUNDIR}  1>&1
  exit 20 # FAIL
fi

FILELIST=$(find ${REFOUTDIR}/output -regextype posix-extended -regex $REGEXP)
if [ -z "$FILELIST" ] ; then
  echo "No NetCDF/GRIB output file found in " ${REFOUTDIR}  1>&1
  exit 20 # FAIL
fi

cd ${RUNDIR}
for f in $(find output -regextype posix-extended -regex $REGEXP) ; do
  DIFF=$($cdo -s diffv ${RUNDIR}/${f} ${REFOUTDIR}/${f}) 1>&1
  if [ ! -z $DIFF ] ; then
    echo $DIFF  1>&1
    exit 20 # FAIL
  fi
done

# goodbye
exit 0 # MATCH
