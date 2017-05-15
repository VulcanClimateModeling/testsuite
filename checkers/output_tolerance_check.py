#!/usr/bin/env python2

"""
COSMO TECHNICAL TESTSUITE

This script checks whether the output of two runs is identical by comparing the
YUCHKDAT files.
"""

# built-in modules
import os, sys

# private modules
sys.path.append(os.path.join(os.path.dirname(__file__), "../tools"))
from ts_utilities import read_environ, dir_path
from ts_fortran_nl import get_param
from sys import maxsize
import comp_yuchkdat
import ts_thresholds

# information
__author__     = "Xavier Lapillonne, David Leutwyler, Santiago Moreno"
__email__      = "cosmo-wg6@cosmo.org"
__maintainer__ = "xavier.lapillonne@meteoswiss.ch"

# some global definitions
yufile   = 'YUCHKDAT'    # name of special testsuite output
yuswitch = 'lcheck'      # namelist switch controlling YUPRDBG output
lnout    = 'ngribout'    # namelist entry which specifies the nr ouf output lists
nlfile  = 'INPUT_IO'    # namelist file containing yuswitch
nlfile2 = 'INPUT_ORG'    # namelist file containing dt



def check():

    # get name of myself
    myname = os.path.basename(__file__)
    header = myname+': '

    # get environment variables
    env = read_environ()
    verbose = int(env['VERBOSE'])
    rundir = dir_path(env['RUNDIR'])
    refoutdir = dir_path(env['REFOUTDIR'])
    namelistdir = dir_path(env['NAMELISTDIR'])
    tolerance = env['TOLERANCE']
    forcematch = int(env['FORCEMATCH']) == 1

    # defines the 2 file that belongs logically to the checker
    yufile1 = rundir + yufile
    yufile2 = refoutdir + yufile

    # extract timestep
    try:
        dt = float(get_param(rundir+nlfile2, 'dt'))
    except:
        if verbose:
            print header+'failed to extract dt from '+rundir+nlfile
        return 20 # FAIL

    # check for output lists
    try:
        nout_list = get_param(rundir+nlfile, lnout)
    except:
        if verbose:
            print header+'no output lists in '+rundir+nlfile
        return 20 # FAIL

    # check if special testsuite output was activated in every output list
    if get_param(rundir+nlfile, yuswitch, occurrence=nout_list) in ['.FALSE.', '.false.']:
        if verbose:
            print yuswitch+' is set to .false. in '+rundir+nlfile+' for this simulation'
        return 20 # FAIL

    #check if tolerance file exists in namelistdir
    tolerance_path=namelistdir + tolerance
    if os.path.exists(tolerance_path):
        tolerance_file=tolerance_path   #in namelist dir
        ltol_file=True
    else:
        tolerance_file=''
        ltol_file=False

    # define tolerances for comparing YUCHKDAT files
    # Use tolerance file if exists
    if ltol_file:
        if verbose==2:
            print header + 'Using tolerance values from file'
        elif verbose>2:
            print header + 'Using tolerance values from file '+tolerance_file
        try:
            threshold = ts_thresholds.Thresholds(tolerance_file)
            threshold_dict = threshold.to_dict()
            if "CHKDAT" in threshold_dict.keys():
                tol_out  = threshold_dict["CHKDAT"]
            else:
                tol_out = threshold_dict["*"]
            tol_times  = threshold_dict["steps"]
            minval = threshold_dict["minval"]
        except:
            if verbose:
                print header+'Error while reading '+tolerance_file
                print header+'Cannot read one of the follwoing parameter: tol_times,tol_out,minval'
            return 20 # FAIL
    else:
        if verbose>1:
            print header + 'Using default tolerance values'

        tol_times = [1200,2400,4000]      # time limit for tolerance setting in seconds
        tol_out  = [1.0e-7,1.0e-4,1.0e-0] # tolerance threshold for all other prognostic fields
        minval   = 1.0e-9                 # values below min val are not considered

    # Override the tolerances in case FORCEMATCH is enabled
    if forcematch:
        tol_times = [maxsize]
        tol_out   = [0.0]
        minval    = 0.0

    #set tolerance time step index

    try:
        # check for bit identical results
        if verbose>1:
            print header + 'Checking first if results are bit identical'
        if verbose>2:
            print header + 'comp_yuprtest()'
            print header + '  file1 = '+yufile1
            print header + '  file2 = '+yufile2
            print header + '  minval = '+str(-1)
            print header + '  nts = [%s]' % ','.join(map(str, [maxsize]))
            print header + '  tol_temp = [%s]' % ','.join(map(str, [0.0]))
            print header + '  tol_out = [%s]' % ','.join(map(str, [0.0]))
        err_count_identical = comp_yuchkdat.cmp_(yufile1, yufile2, -1, -1, [0.0], [0.0])
        if verbose>1:
            if err_count_identical==0:
                print header + 'Results are bit identical'
            else:
                print header + 'Results are not bit identical'
        # check if results are within tolerance values
        if verbose>1:
            print header + 'Checking if results are within tolerance'
            print header + '  minimal value : %s' %(minval)
            print header + '  tolerance time : %s' % ','.join(map(str, tol_times))
            print header + '  thresholds for all output fields: %s' % ','.join(map(str, tol_out))
        if verbose>2:
            print header + 'comp_yuprtest()'
            print header + '  file1 = '+yufile1
            print header + '  file2 = '+yufile2
            print header + '  minval = '+str(minval)
            print header + '  nts = [%s]' % ','.join(map(str, tol_times))
            print header + '  tol_out = [%s]' % ','.join(map(str, tol_out))
        error_count = comp_yuchkdat.cmp_(yufile1, yufile2, 0, minval, tol_times, tol_out)
        if verbose>1:
            if error_count==0:
                print header + 'Results are within thresholds'
            else:
                print header + 'Results are not within thresholds'

    except Exception as e:
        if verbose:
            print e
        return 20 # FAIL

    if err_count_identical == 0:
        return 0 # MATCH
    elif error_count == 0:
        return 10 # OK
    else:
        return 20 # FAIL

if __name__ == "__main__":
    sys.exit(check())



