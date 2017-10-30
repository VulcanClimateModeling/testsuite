#!/bin/bash

# COSMO TECHNICAL TESTSUITE
#
# This script checks whether the content of NetCDF/GRIB files is identical
# David Leutwyler, October 2017


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

FILELIST=$(ls -1 ${RUNDIR}/output/l[bf]f*00.nc 2>/dev/null)
if [ $? -ne 0 ] ; then
  echo "No netCDF output file found in " ${RUNDIR}  1>&1
  exit 20 # FAIL
fi

FILELIST=$(ls -1 ${REFOUTDIR}/output/l[bf]f*00.nc 2>/dev/null)
if [ $? -ne 0 ] ; then
  echo "No netCDF output file found in " ${REFOUTDIR}  1>&1
  exit 20 # FAIL
fi

REGEX='^.*lff[fd][0-9]+[a-zA-Z]{0,1}(.nc){0,1}' #Find NetCDF and GRIB files, based on name
for f in `find ${RUNDIR}/output -regextype posix-extended -regex $REGEX` ; do
  DIFF=$(cdo -s diffv ${RUNDIR}/output/${f} ${REFOUTDIR}/output/${f})
  if [ ! -z $DIFF ] ; then
    echo $DIFF  1>&1
    exit 20 # FAIL
  fi
done

# goodbye
exit 0 # MATCH
