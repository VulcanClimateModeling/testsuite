#!/usr/bin/env python

"""
COSMO TECHNICAL TESTSUITE

This script checks cosmo diagnostic files within threshold
Since the test use a simple compare tools which do not depend
on the time step only the first ncomplines are considered.
"""

# built-in modules
import os, sys

# private modules
sys.path.append(os.path.join(os.path.dirname(__file__), "../tools"))
from ts_utilities import read_environ, dir_path, str_to_bool
from comp_table import cmp_table
import ts_thresholds

# information
__author__     = "Xavier Lapillonne"
__email__      = "cosmo-wg6@cosmo.org"
__maintainer__ = "xavier.lapillonne@meteoswiss.ch"

# some global definitions
yufiles    = ['YUPRHUMI','YUPRMASS']         # name of special output files to be compared
ncomplines = [21,22]                         # max line to consider
colpattern = ["xxcccccccccc","xxcccccccccc"] # coloumn pattern

def check():

    # init values
    err_count_identical=0
    err_count=0

    # get name of myself
    myname = os.path.basename(__file__)
    header = myname+': '

    # get environment variables
    verbose = int(os.environ['TS_VERBOSE'])
    namelistdir =  dir_path(os.environ['TS_NAMELISTDIR'])
    rundir = dir_path(os.environ['TS_RUNDIR'])
    refoutdir = dir_path(os.environ['TS_REFOUTDIR'])
    tolerance = os.environ['TS_TOLERANCE']


    #get tolerance and minval
    tolerance_file=namelistdir+tolerance
    if not os.path.exists(tolerance_file):
        print('Missing tolerance file %s' %(tolerance_file) )
        return 20 #FAIL

    thresholds = ts_thresholds.Thresholds(tolerance_file)
    tol = thresholds.get_threshold("CHKDAT", 0)   # tolerence for t
    minval = thresholds.minval

    
    for it in range(len(yufiles)):
        # defines the 2 file that belongs logically to the checker
        yufile1 = rundir + yufiles[it]
        yufile2 = refoutdir + yufiles[it]

        try:
            # check for bit identical results
            err = cmp_table(yufile1, yufile2, \
                            colpattern[it],minval,0,0,ncomplines[it])
            if err !=0 : err_count_identical=err
            # check for error within tolerance
            err = cmp_table(yufile1, yufile2, \
                            colpattern[it],minval,tol,1,ncomplines[it])
            if err !=0 : err_count=err
        except Exception as e:
            if verbose:
                print e
            return 20 # FAIL

    if err_count_identical == 0:
        return 0 # MATCH
    elif err_count == 0:
        return 10 # OK
    else:
        return 20 # FAIL

if __name__ == "__main__":
    sys.exit(check())



