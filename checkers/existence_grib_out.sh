#!/bin/bash

# COSMO TECHNICAL TESTSUITE
#
# This script checks whether the run produced correctly a grib
# file at hour zero

# Author       Oliver Fuhrer
# Email        cosmo-wg6@cosmo.org
# Maintainer   xavier.lapillonne@meteoswiss.ch

# check environment variables
RUNDIR=${TS_RUNDIR}
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

# function to cat together files (from parallel grib output)
function grc {
  files=`find * -maxdepth 0 -print | grep '.*_[0-9]$' | sed 's/_[0-9]$//g' | sort | uniq`
  if [ ! -z "$files" ] ; then
    # cat the files together
    for thef in $files ; do
      # concat the files
      /bin/cat ${thef}_[0-9] > ${thef}
      # check the file size
      totsiz=`stat -c '%s' ${thef}_[0-9] | awk '{sum=sum+$1;print sum}' | tail -1`
      catsiz=`stat -c '%s' ${thef}`
      if [ $totsiz -eq $catsiz ] ; then
        /bin/rm -f ${thef}_[0-9]
      else
        echo "Size check mismatch for ${thef}!!!"
      fi
    done
  fi
}

# determine file
FILE="${RUNDIR}/output/lfff00000000"

# determine number of IO processors
nprocio=0
if [ -s "${RUNDIR}/YUSPECIF" ] ; then
  nprocio=`grep nprocio ${RUNDIR}/YUSPECIF | awk '{print \$2}'`
fi

# cat together files if parallel grib I/O was used
cwd=`/bin/pwd`
if [ "${nprocio}" -gt 1 ] ; then
  if [ -s "${FILE}_0" ]; then
    cd ${RUNDIR}/output
    grc
    cd ${cwd}
  fi
fi

# check presence of output file
if [ ! -s "$FILE" ]; then
  if [ "$VERBOSE" -gt 0 ]; then
    echo "File $FILE does not exists or is zero size"
  fi
  exit 20 # FAIL
fi

## fuo: this check does not seem to be robust across platforms and grib libraries
##
## # check if output file is grib
## which od 1>/dev/null 2>/dev/null
## if [ $? -eq 0 ] ; then
##   hdd=`od -N 4 -c "${FILE}" 2>/dev/null | head -1 2>/dev/null | tr -d '[0-9 ]' 2>/dev/null`
##   if [ $? -eq 0 ] ; then
##     if [ "$hdd" != "GRIB" ] ; then
##       if [ "$VERBOSE" -gt 0 ]; then
##         echo "File $FILE is not GRIB format"
##       fi
##       exit 20 # FAIL
##     fi
##   fi
## fi

# goodbye
exit 0 # MATCH

