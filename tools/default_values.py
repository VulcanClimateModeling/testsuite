class DefaultValues:
    """Datacontainer for the default values of the command line options"""
    
    nprocs             = 16
    nprocio            = None
    force              = False
    v_level            = 1
    mpicmd             = "aprun -n"
    exe                = None
    color              = False
    steps              = None
    use_wrappers       = False
    stdout             = ""
    outappend          = False
    only               = None
    upnamelist         = False
    forcematch         = False
    forcematch_base    = False
    tune_thresholds    = False
    update_thresholds  = False
    tuning_iterations  = 10
    reset_thresholds   = False
    upyufiles          = False
    testlist           = "testlist.xml"
    timeout            = None
    workdir            = "./work"
    tolerance          = "TOLERANCE"
    icon               = False
    config_file        = "testsuite_config.cfg"
