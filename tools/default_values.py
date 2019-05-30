class DefaultValues:
    """Datacontainer for the default values of the command line options"""
    
    nprocs   = 16
    nprocio  = None
    v_level  = 1
    mpicmd   = "aprun -n"
    exe      = None
    steps    = None
    stdout   = ""
    testlist = "testlist.xml"
    tolerance = "TOLERANCE"
    timeout  = None
    forcematch = False
    forcematch_base = False
    tune_thresholds = False
    reset_thresholds = False
    update_thresholds = False
    tuning_iterations = 10
    config_nl = "OUTPUT"
    namelist_ts_switch = "INPUT"
    icon = False
    config_file = "testsuite_config.cfg"
