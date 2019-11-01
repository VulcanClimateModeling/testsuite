#!/usr/bin/env python

"""
COSMO TECHNICAL TESTSUITE

This script runs a set of tests defined in testlist.xml and checks the results
for correctness using a set of checkers which can be defined for each test.

For further help and command line arguments execute this script without arguments.
"""

# built-in modules
import os, sys, string, struct
import optparse as OP
import xml.etree.ElementTree as XML
import logging as LG
import ConfigParser
import ast
import yaml

# private modules
sys.path.append(os.path.join(os.path.dirname(__file__), "./tools")) # this is the generic folder for subroutines
from ts_error import StopError, SkipError
from ts_utilities import system_command, change_dir
import ts_logger as LG
from ts_test import Test

# information
__author__     = "Nicolo Lardelli, Xavier Lapillonne, Oliver Fuhrer, Santiago Moreno"
__copyright__  = "Copyright 2012-2018, COSMO Consortium"
__license__    = "MIT"
__version__    = "2.2.5"
__date__       = "13.11.2018"
__email__      = "cosmo-wg6@cosmo.org"
__maintainer__ = "xavier.lapillonne@meteoswiss.ch"


class objectview(object):
    def __init__(self, d):
        self.__dict__ = d

def parse_config_file(filename):

    # read YAML configuration file
    with open(filename) as f:
        data = yaml.load(f)

    # convert dictionary to object with attributes
    conf = objectview(data)

    # save base directory where testsuite is executed
    conf.basedir = os.getcwd()

    return conf 


def parse_cmdline():
    """parse command line options"""

    # read default values
    with open(os.path.join(os.path.dirname(__file__), 'conf', 'defaults.yaml')) as f:
        data = yaml.load(f)
    defaults = objectview(data)

    # the parser is initialized with its description and its epilog
    parser = OP.OptionParser(description=
                "Description: this script run a series of tests defined in testlist.xml. For "+
                "each test a set of checks are carried out, see checkers/README for more "+
                "information",
              epilog=
                "Example: ./testsuite.py -n 16 --color -f --exe=cosmo --mpicmd=\'aprun -n\' -v 1")
    
    # defines the number of processor, the number of processors is not a test specific option,
    # it overrides the values present in the namelist INPUT_ORG
    parser.set_defaults(nprocs=defaults.nprocs)
    parser.add_option("-n", type="int", dest="nprocs",
               help=("number of processors (nprocx*nprocy+nprocio) to use [default=%d]" % defaults.nprocs))
    
    # defines the number of I/O processors, not a test specific option
    parser.set_defaults(nprocio=defaults.nprocio)
    parser.add_option("--nprocio", type="int", dest="nprocio",
               help="set number of asynchronous IO processor, [default=<from namelist>]")
 
    # defines the behavior of testsuite after fail or crash
    parser.set_defaults(force=defaults.force)
    parser.add_option("-f","--force", dest="force", action="store_true", 
               help="do not stop upon error [default=%r]" % defaults.force)
    
    # set the level of verbosity of the standard output
    parser.set_defaults(v_level=defaults.v_level)
    parser.add_option("-v", type="int", dest="v_level", action="store",
               help=("verbosity level 0 to 3 [default=%d]" % defaults.v_level))

    # specifies the syntax of the mpi command
    parser.set_defaults(mpicmd=defaults.mpicmd)
    parser.add_option("--mpicmd", type="string", dest="mpicmd", action="store",
               help=("MPI run command (e.g. \"mpirun -n\") [default=\"%s\"]" % defaults.mpicmd))

    # defines the executable name, this overides the definition in testlist.xml if any
    parser.set_defaults(exe=defaults.exe)
    parser.add_option("--exe", type="string", dest="exe", action="store",
               help="Executable file, [default=<from testlist.xml>]")

    # defines if the output will be colored or not
    parser.set_defaults(color=defaults.color)
    parser.add_option("--color", dest="color", action="store_true",
               help="Select colored output [default=%r]" % defaults.color)

    # overrides the hstop/nstop options in the namelist and execute the cosmo runs with a given number of steps
    parser.set_defaults(steps=defaults.steps)
    parser.add_option("--steps", type="int", dest="steps", action="store",
               help="Run only specified number of timesteps [default=<from namelist>]")

    # defines if a wrapper for job submission has to be written or not
    parser.set_defaults(use_wrappers=defaults.use_wrappers)
    parser.add_option("-w","--wrapper", dest="use_wrappers", action="store_true", 
               help="Use wrapper instead of executable for mpicmd [default=%r]" % defaults.use_wrappers)

    # defines the filename for the redirected standard output
    parser.set_defaults(stdout=defaults.stdout)
    parser.add_option("-o", type="string", dest="stdout", action="store",
               help="Redirect standard output to selected file [default=<stdout>]")
    
    # defines the behaviour of the redirected standard output, if appended or overwritten
    parser.set_defaults(outappend=defaults.outappend)
    parser.add_option("-a","--append", dest="outappend", action="store_true",
               help="Appends standard output if redirection selected [default=%r]" % defaults.outappend)
    
    # only one test is executed
    parser.set_defaults(only=defaults.only)
    parser.add_option("--only", type="string", dest="only", action="store",
               help="Run only one test define as type,name (e.g. --only=cosmo7,test_1) [default=None]")

    # update namelist (no run). This is useful to quickly change all namelist at once 
    parser.set_defaults(upnamelist=defaults.upnamelist)
    parser.add_option("--update-namelist", dest="upnamelist", action="store_true",
               help="Use Testsuite to update namelists (no tests executed) [default=%r]" % defaults.upnamelist)

    # force bit-reproducible results
    parser.set_defaults(forcematch=defaults.forcematch)
    parser.add_option("--force-match", dest="forcematch", action="store_true",
               help="Force bit-reproducible results [default=%r]" % defaults.forcematch)

    # only force bit-reproducible results for base tests
    parser.set_defaults(forcematch_base=defaults.forcematch_base)
    parser.add_option("--force-match-base", dest="forcematch_base", action="store_true",
               help="Force bit-reproducible results only for base tests, " + 
                    "i.e. those with name matching test in data/ folder [default=%r]" % defaults.forcematch_base)

    # tune thresholds
    parser.set_defaults(tune_thresholds=defaults.tune_thresholds)
    parser.add_option("--tune-thresholds", dest="tune_thresholds", action="store_true",
               help="Change thresholds to always at least return OK [default=%r]" % defaults.tune_thresholds)

    # update thresholds
    parser.set_defaults(update_thresholds=defaults.update_thresholds)
    parser.add_option("--update-thresholds", dest="update_thresholds", action="store_true",
               help="Update the thresholds [default=%r]" % defaults.update_thresholds)

    # set number of iterations for tuning
    parser.set_defaults(tuning_iterations=defaults.tuning_iterations)
    parser.add_option("--tuning-iterations", dest="tuning_iterations", action="store",
               help="Defines how many times the tuning gets executed [default=%d]" % defaults.tuning_iterations)

    # set thresholds to zero before tuning
    parser.set_defaults(reset_thresholds=defaults.reset_thresholds)
    parser.add_option("--reset-thresholds", dest="reset_thresholds", action="store_true",
               help="Set all thresholds to 0.0 before tuning [default=%r]" % defaults.reset_thresholds)

    # update namelist (no run). This is useful to quickly change all namelist at once
    parser.set_defaults(upyufiles=defaults.upyufiles)
    parser.add_option("--update-yufiles", dest="upyufiles", action="store_true",
               help="Define new references (no tests executed) [default=%r]" % defaults.upyufiles)

    # specifies the namelist file
    parser.set_defaults(testlist=defaults.testlist)
    parser.add_option("-l","--testlist", type="string", dest="testlist", action="store",
               help=("Select the testlist file [default=%s]" % defaults.testlist))

    # timeout value for individual tests
    parser.set_defaults(timeout=defaults.timeout)
    parser.add_option("-t","--timeout", type="int", dest="timeout", action="store",
               help=("Timeout in s for each test [default=%s]" % defaults.timeout))

    # working directory
    parser.set_defaults(workdir=defaults.workdir)
    parser.add_option("--workdir", type="string", dest="workdir", action="store",
               help="Working directory [default=%s]" % defaults.workdir)

    # specifies the tolerance file name for the tolerance checker
    parser.set_defaults(tolerance=defaults.tolerance)
    parser.add_option("--tolerance", type="string", dest="tolerance", action="store",
               help=("Select the tolerance file name [default=%s]" % defaults.tolerance))

    # flag to run the testsuite for icon
    parser.set_defaults(icon=defaults.icon)
    parser.add_option("--icon", dest="icon", action="store_true",
               help=("Run the testsuite for ICON [default=%s]" % defaults.icon))

    # name of the config file
    parser.set_defaults(config_file=defaults.config_file)
    parser.add_option("--config-file", type="string", dest="config_file", action="store",
               help=("Name of the testsuite configuration file [default=%s]" % defaults.config_file))

    # parse
    try:
        (options,args) = parser.parse_args()
    except (OP.OptionError,TypeError):
        sys.exit("problem parsing command line arguments (check ./testsuite.py -h for valid arguments)")

    return options


def parse_xmlfile(filename, logger):

    try: 
        xmltree = XML.parse(filename)
    except Exception as e:
        logger.error('Error while reading xml file '+filename+':')
        logger.error(e)
        sys.exit(1) # this exits without traceback
        #raise # this exits with full traceback

    return xmltree.getroot()


def setup_logger(options):

    # instantiate logger class
    logger = LG.Logger(options.stdout, options.outappend, options.color)

    # set verbosity level
    if options.v_level <= 0:
      logger.setLevel(LG.ERROR)
    elif options.v_level == 1:
      logger.setLevel(LG.WARNING)
    elif options.v_level == 2:
      logger.setLevel(LG.INFO)
    elif options.v_level >= 3:
      logger.setLevel(LG.DEBUG)

    return logger
    

def main():
    """read configuration and then execute tests"""

    # definition of structure carrying global configuration
    # search for config file in current path, otherwise takes
    # default configuration file in testsuite source directory
    # parse command line arguments
    options = parse_cmdline()

    if os.path.isfile(options.config_file): 
        conf = parse_config_file(options.config_file)
    elif os.path.isfile(os.path.join(os.path.dirname(__file__), options.config_file)):
        conf = parse_config_file(os.path.join(os.path.dirname(__file__), options.config_file))     
    else:
        #logger not initialize at this stage, use print and exit
        print('Error: Missing configuration file ' + options.config_file)
        sys.exit(1)
        
    # redirect standard output (if required)
    logger = setup_logger(options)

    # hello world!
    logger.important('TESTSUITE ' + __version__)

    # parse the .xml file which contains the test definitions
    logger.info('Parsing XML (' + options.testlist + ')')
    root = parse_xmlfile(options.testlist, logger)

    # generate work directory
    status = system_command('/bin/mkdir -p ' + options.workdir + '/', logger, throw_exception=False)
    if status:
        exit(status)

    # loops over all the tests
    stop = False
    for child in root.findall("test"):

        # create test object
        mytest = Test(child, options, conf, logger)
        
        if mytest.run_test():
            # run test
            try:

                # if upyufiles=True, no model run.
                if options.upyufiles:
                    logger.important('Update YU* files mode, no run')
                    mytest.update_yufiles()
                #
                elif options.update_thresholds:
                    logger.important('Updating the thresholds on the current runs')
                    mytest.options.tune_thresholds = True
                    mytest.log_file = 'exe.log'
                    mytest.check()
                # if upnamelist=True, no model run.
                elif options.upnamelist:
                    logger.important('Update namelist mode, no run')
                    mytest.prepare() # prepare test directory and update namelists
                    mytest.update_namelist() #copy back namelist in typedir
                # Spcial setup for ICON where only check is run
                elif options.icon:
                    mytest.options.pert = 0
                    logger.important('Running checks for ICON')
                    mytest.log_file = 'final_status.txt'
                    mytest.check()
                else:
                    if(mytest.options.tune_thresholds):
                        mytest.options.pert = 0
                        for i in range(int(mytest.options.tuning_iterations)):
                            mytest.prepare() # prepare test directory and update namelists
                            logger.important("Iteration number {0}".format(i+1))
                            mytest.prerun() # last preparations (dependencies must have finished)
                            mytest.start()  # start test
                            mytest.wait()   # wait for completion of test
                            mytest.check()  # call checkers for this test
                            mytest.options.reset_thresholds = False
                            # 1: Perturb only in the first timestep
                            # 2: Perturb in every iteration
                            mytest.options.pert = 2
                    else:
                        mytest.options.pert = 0
                        mytest.prepare() # prepare test directory and update namelists
                        mytest.prerun() # last preparations (dependencies must have finished)
                        mytest.start()  # start test
                        mytest.wait()   # wait for completion of test
                        mytest.check()  # call checkers for this test

            except SkipError as smessage:
                mytest.result = 15 # SKIP
                logger.warning(smessage)

            except StopError as emessage:
                if str(emessage).strip():
                    logger.error(emessage)
                    if not options.force:
                        stop = True

            # write result
            mytest.write_result()

            # return into the base directory after each test
            status = change_dir(conf.basedir, logger)

            # exit if required
            if stop:
                break

    # end of testsuite std output
    logger.important('FINISHED')


if __name__ == "__main__":
    main()

