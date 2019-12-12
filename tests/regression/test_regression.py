#!/usr/bin/env python

import os
import shutil
import subprocess
import tempfile

import f90nml
import pytest

# these regression tests only work in the directory where they reside
ROOTDIR = os.path.dirname(os.path.realpath(__file__))
os.chdir(ROOTDIR)

# location where the reference data directory is located
DATAREFDIR = os.path.join(ROOTDIR, 'data_ref')
DATADIR = os.path.join(ROOTDIR, 'data')

# temporary working directories
TMPDIR = tempfile.TemporaryDirectory()
WORKDIR = os.path.join(TMPDIR.name, 'work')
WORKDIR2 = os.path.join(TMPDIR.name, 'work2')

# temporary stdout redirection file
OUTFILE = os.path.join(TMPDIR.name, 'testsuite.out')

# invocation of testsuite
TESTSUITE_CMD = '../../testsuite.py'

# check if we want to do code coverage analysis
# note: this is required, since the regression tests use subprocess to call the testsuite
COVERAGE = False
if COVERAGE:
    try:
        os.remove(".coverage")
    except OSError:
        pass
    TESTSUITE_CMD = 'coverage run -a ' + TESTSUITE_CMD

# default arguments when invoking testsuite (can be overriden)
DEFAULT_ARGUMENTS = [
    '--config-file=config.cfg',
    '--args="--model=cosmo"',
    '--tolerance=TOLERANCE',
    '--testlist=testlist.xml',
    '--mpicmd=',
    '--workdir=' + WORKDIR]


def run_cmd(cmd):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    return process.returncode, stdout, stderr


def number_of_lines_in_string(input_string):
    if not input_string:
        return 0
    else:
        return len(input_string.split('\n'))


def extract_lines_with_pattern(pattern, input_string, ignore_case=False):
    result = ''
    for line in input_string.split('\n'):
        if ignore_case:
            pattern = pattern.lower()
            line = line.lower()
        if pattern in line:
            if result:
                result += '\n' + line
            else:
                result = line
    return result


def remove_lines_with_pattern(pattern, input_string, ignore_case=False):
    result = ''
    for line in input_string.split('\n'):
        if ignore_case:
            pattern = pattern.lower()
            line = line.lower()
        if pattern not in line:
            if result:
                result += '\n' + line
            else:
                result = line
    return result


def number_of_lines_with_pattern(pattern, input_string, ignore_case=False):
    matching_lines = extract_lines_with_pattern(pattern, input_string,
        ignore_case)
    return number_of_lines_in_string(matching_lines)


def clean_working_directory(dirname=WORKDIR):
    assert dirname != ''
    assert dirname != '/'
    if os.path.isdir(dirname):
        shutil.rmtree(dirname)


def clean_data_directory(data_directory_source=DATAREFDIR,
        data_directory_destination=DATADIR):
    assert DATAREFDIR != ''
    assert DATAREFDIR != '/'
    assert DATADIR != ''
    assert DATADIR != '/'
    assert os.path.isdir(DATAREFDIR)
    cmd = 'rsync -a --delete ' + DATAREFDIR + '/ ' + DATADIR + '/'
    os.system(cmd)


def run_testsuite(args=[], with_default_arguments=True, clean_before=True):
    if clean_before:
        clean_working_directory()
        clean_data_directory()
    cmd = TESTSUITE_CMD
    if with_default_arguments:
        cmd += ' ' + ' '.join(DEFAULT_ARGUMENTS)
    cmd += ' ' + ' '.join(args)
    exit_status, stdout, stderr = run_cmd(cmd)
    return exit_status, stdout.decode('utf-8'), stderr.decode('utf-8')


def check_test_results(exit_status, stdout, stderr):
    if stderr:
        print('\n\n>>> stderr\n' + stderr)
    assert exit_status == 0
    assert stderr == ''
    number_of_errors = number_of_lines_with_pattern('error', stdout,
        ignore_case=True)
    number_of_warnings = number_of_lines_with_pattern('warning', stdout,
        ignore_case=True)
    results = extract_lines_with_pattern(' RESULT ', stdout)
    number_of_matches = number_of_lines_with_pattern(' MATCH ', results)
    number_of_oks = number_of_lines_with_pattern(' OK ', results)
    number_of_fails = number_of_lines_with_pattern(' FAIL ', results)
    number_of_skips = number_of_lines_with_pattern(' SKIP ', results)
    number_of_crashes = number_of_lines_with_pattern(' CRASH ', results)
    number_of_unknowns = number_of_lines_with_pattern(' UNKNOWN ', results)
    return {'error': number_of_errors,
            'warning': number_of_warnings,
            'match': number_of_matches,
            'ok': number_of_oks,
            'fail': number_of_fails,
            'skip': number_of_skips,
            'crash': number_of_crashes,
            'unknown': number_of_unknowns}


def check_successful_run(exit_status, stdout, stderr, force_match=False):
    results = check_test_results(exit_status, stdout, stderr)
    problem = results['error'] + results['warning'] + results['fail'] + \
               results['skip'] + results['crash'] + results['unknown']
    if problem:
        print('\n\n>>> stdout\n' + stdout)
    assert results['error'] == 0
    assert results['warning'] == 0
    assert results['fail'] == 0
    assert results['skip'] == 0
    assert results['crash'] == 0
    assert results['unknown'] == 0
    if force_match:
        assert results['ok'] == 0
    return results


def read_exe_logfile(dirname, working_directory=WORKDIR, logfile='exe.log'):
    assert os.path.isdir(working_directory)
    filepath = os.path.join(working_directory, dirname, logfile)
    with open(filepath, 'r') as logfile:
        return logfile.read()


def count_timesteps_in_stats_file(filename):
    timesteps = []
    with open(filename, 'r') as statistics_file:
        for line in statistics_file:
            if '#' not in line:
                step = int(line.split()[1])
                if step not in timesteps:
                    timesteps += [step]
    return timesteps


def test_help_argument():
    exit_status, stdout, stderr = run_testsuite(['--help'],
        with_default_arguments=False)
    assert exit_status == 0
    assert stderr == ''


def test_plain_testcase():
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_plain'])
    log = read_exe_logfile('basic/test_plain')
    check_successful_run(exit_status, stdout, stderr, force_match=True)
    assert number_of_lines_with_pattern('RESULT', stdout) == 1
    assert 'basic/test_plain' in extract_lines_with_pattern('RESULT', stdout)
    _ = read_exe_logfile('basic/test_plain')


def test_args_argument():
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_plain',
        '--args=""'])
    check_successful_run(exit_status, stdout, stderr, force_match=True)
    assert number_of_lines_with_pattern('RESULT', stdout) == 1
    assert 'basic/test_plain' in extract_lines_with_pattern('RESULT', stdout)
    log = read_exe_logfile('basic/test_plain')
    assert 'Model: plain model' in log


def test_basic_tolerance_testcase():
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic'])
    check_successful_run(exit_status, stdout, stderr)
    assert number_of_lines_with_pattern('RESULT', stdout) == 1
    assert 'basic/test_basic' in extract_lines_with_pattern('RESULT', stdout)
    _ = read_exe_logfile('basic/test_basic')


def test_verbose_argument():
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '-v 10'])
    check_successful_run(exit_status, stdout, stderr)


def test_derived_testcase():
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_derived'])
    check_successful_run(exit_status, stdout, stderr)
    assert number_of_lines_with_pattern('RESULT', stdout) == 1
    assert 'basic/test_derived' in extract_lines_with_pattern('RESULT', stdout)
    _ = read_exe_logfile('basic/test_derived')


@pytest.mark.parametrize("number_of_iterations", [2, 4, 7])
def test_threshold_tuning_arguments(number_of_iterations):
    exit_status, stdout, stderr = run_testsuite(
        ['--only=basic,test_basic', '--tune-thresholds',
         '--tuning-iterations=' + str(number_of_iterations)])
    results = check_successful_run(exit_status, stdout, stderr)
    actual_number = number_of_lines_with_pattern('Iteration number', stdout)
    assert actual_number == number_of_iterations
    assert results['ok'] == 1
    assert results['match'] == 0
    clean_data_directory()


def test_updating_of_reference_argument():
    # first make a perturbed run (we need to retain updated thresholds)
    test_threshold_tuning_arguments(number_of_iterations=2)
    # update references (with results from perturbed run)
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '--update-yufiles'], clean_before=False)
    check_successful_run(exit_status, stdout, stderr)
    # check that this only gives an OK for an unperturbed run
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic'])
    results = check_successful_run(exit_status, stdout, stderr)
    assert results['ok'] == 1
    assert results['match'] == 0
    # update references (with results from clean run)
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '--update-yufiles'], clean_before=False)
    check_successful_run(exit_status, stdout, stderr)
    # check that this gives a MATCH
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic'],
        clean_before=False)
    results = check_successful_run(exit_status, stdout, stderr)
    assert results['ok'] == 0
    assert results['match'] == 1
    clean_data_directory()


def test_nproc_argument():
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '-n 144'])
    check_successful_run(exit_status, stdout, stderr)
    nml = f90nml.read(WORKDIR + '/basic/test_basic/INPUT_ORG')
    assert nml['runctl']['nprocx'] == 12
    assert nml['runctl']['nprocy'] == 12


def test_nprocio_argument():
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '--nprocio=2'])
    check_successful_run(exit_status, stdout, stderr)
    nml = f90nml.read(WORKDIR + '/basic/test_basic/INPUT_ORG')
    assert nml['runctl']['nprocx'] == 7
    assert nml['runctl']['nprocy'] == 2
    assert nml['runctl']['nprocio'] == 2


def test_exe_argument():
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_plain',
        '--exe=echo.sh', '--args="Hello world"'])
    check_successful_run(exit_status, stdout, stderr)
    # check that 'echo.sh --model=cosmo' was executed
    log = read_exe_logfile('basic/test_plain')
    assert 'Hello world' in log


@pytest.mark.parametrize("number_of_steps", [1, 3, 7])
def test_number_of_timesteps_argument(number_of_steps):
    assert number_of_steps <= 10
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '--steps=' + str(number_of_steps)])
    check_successful_run(exit_status, stdout, stderr)
    timesteps = count_timesteps_in_stats_file(WORKDIR + '/basic/test_basic/YUPRTEST')
    assert timesteps == list(range(number_of_steps + 1))


@pytest.mark.parametrize("argument_name", ['--wrapper', '-w'])
def test_wrapper_argument(argument_name):
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        argument_name])
    check_successful_run(exit_status, stdout, stderr)


def test_stdout_redirect_to_file_argument():
    # generate reference stdout (no redirect)
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic'])
    check_successful_run(exit_status, stdout, stderr)
    stdout_reference = stdout
    # run testsuite with redirect and compare to reference
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '-o ' + OUTFILE])
    check_successful_run(exit_status, stdout, stderr)
    assert stdout == ''
    with open(OUTFILE, 'r') as stdout_file:
        stdout = stdout_file.read()
    assert stdout == stdout_reference
    os.remove(OUTFILE)


@pytest.mark.parametrize("argument_name", ['--append', '-a'])
def test_stdout_redirect_and_append_to_file_argument(argument_name):
    # generate reference stdout (no redirect)
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic'])
    check_successful_run(exit_status, stdout, stderr)
    stdout_reference = stdout
    # create a file with random content
    random_string = 'The quick brown fox jumps over the lazy dog.\n'
    with open(OUTFILE, 'w') as stdout_file:
        stdout_file.write(random_string)
    # run testsuite with redirect and append (and check results)
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '-o ' + OUTFILE, argument_name])
    check_successful_run(exit_status, stdout, stderr)
    assert stdout == ''
    with open(OUTFILE, 'r') as stdout_file:
        stdout = stdout_file.read()
    assert stdout == random_string + stdout_reference
    os.remove(OUTFILE)


def test_force_argument():
    # all but first test should crash with echo.sh executable
    exit_status, stdout, stderr = run_testsuite(['--exe=echo.sh'])
    results = check_test_results(exit_status, stdout, stderr)
    assert number_of_lines_with_pattern('RESULT', stdout) == 2
    assert results['crash'] == 1
    # run again, but forcing execution of all tests (irrespective of success)
    exit_status, stdout, stderr = run_testsuite(['--exe=echo.sh', '--force'])
    results = check_test_results(exit_status, stdout, stderr)
    assert number_of_lines_with_pattern('RESULT', stdout) > 2
    assert results['crash'] >= 1


def test_force_match_argument():
    # first make a perturbed run
    test_threshold_tuning_arguments(number_of_iterations=2)
    # update references (with results from perturbed run)
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '--update-yufiles'], clean_before=False)
    check_successful_run(exit_status, stdout, stderr)
    # check that force-match fails
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '--force-match'])
    results = check_test_results(exit_status, stdout, stderr)
    assert results['ok'] == 0
    assert results['match'] == 0
    assert results['fail'] == 1
    # update references (with results from clean run)
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '--update-yufiles'], clean_before=False)
    check_successful_run(exit_status, stdout, stderr)
    # check that this only gives a MATCH
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '--force-match'], clean_before=False)
    results = check_successful_run(exit_status, stdout, stderr)
    assert results['ok'] == 0
    assert results['match'] == 1
    clean_data_directory()


def test_force_match_base_argument():
    # first make a perturbed run
    test_threshold_tuning_arguments(number_of_iterations=2)
    # update references (with results from perturbed run)
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '--update-yufiles'], clean_before=False)
    check_successful_run(exit_status, stdout, stderr)
    # check that force-match fails
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '--force-match-base'])
    results = check_test_results(exit_status, stdout, stderr)
    assert results['ok'] == 0
    assert results['match'] == 0
    assert results['fail'] == 1
    # check that derived testcaes does not fail
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_derived',
        '--force-match-base'])
    results = check_successful_run(exit_status, stdout, stderr)
    assert results['ok'] == 1
    assert results['match'] == 0
    clean_data_directory()


def test_reset_thresholds_argument():
    # first make a perturbed run
    test_threshold_tuning_arguments(number_of_iterations=2)
    # update references (with results from perturbed run)
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '--update-yufiles'], clean_before=False)
    check_successful_run(exit_status, stdout, stderr)
    # run standard test (and reset thresholds)
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '--reset-thresholds'])
    results = check_test_results(exit_status, stdout, stderr)
    assert results['ok'] == 0
    assert results['match'] == 0
    assert results['fail'] == 1
    clean_data_directory()


def test_update_thresholds_argument():
    test_reset_thresholds_argument()
    # run standard test (and reset thresholds)
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '--update-thresholds'], clean_before=False)
    results = check_test_results(exit_status, stdout, stderr)
    assert 'Updating the thresholds' in stdout
    assert results['ok'] == 1
    assert results['match'] == 0
    assert results['fail'] == 0
    clean_data_directory()


@pytest.mark.parametrize("argument_name", ['--testlist=', '-l '])
def test_testlist_argument(argument_name):
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        argument_name + 'testlist2.xml'])
    check_successful_run(exit_status, stdout, stderr)
    assert 'testlist2.xml' in stdout


def test_tolerance_argument():
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '--tolerance=TOLERANCE2', '-v 10'])
    check_successful_run(exit_status, stdout, stderr)
    assert 'TOLERANCE2' in stdout


# TODO: timeout flag is currently not working in testsuite.py
# @pytest.mark.parametrize("argument_name", ['--timeout=','-t '])
# def test_timeout_argument(argument_name):
# 	exit_status, stdout, stderr = run_testsuite(['--only=basic,test_plain', '--exe=sleep.sh',
# 		                                         '--args=1', argument_name+'2'])
# 	check_successful_run(exit_status, stdout, stderr)
# 	log = read_exe_logfile('basic/test_plain')
# 	exit_status, stdout, stderr = run_testsuite(['--only=basic,test_plain', '--exe=sleep.sh',
# 		                                         '--args=60', argument_name+'2'])
# 	check_successful_run(exit_status, stdout, stderr)
# 	log = read_exe_logfile('basic/test_plain')


def test_workdir_argument():
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '--workdir=' + WORKDIR2])
    check_successful_run(exit_status, stdout, stderr)
    assert os.path.isdir(WORKDIR2)
    _ = read_exe_logfile('basic/test_basic', working_directory=WORKDIR2)


def test_config_file_argument():
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '--config-file=config2.cfg'])
    check_successful_run(exit_status, stdout, stderr)
    assert 'config2.cfg' in stdout


def test_update_namelist_argument():
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic'])
    check_successful_run(exit_status, stdout, stderr)
    log = read_exe_logfile('basic/test_basic')
    assert 'Extra namelist option' not in log
    # change namelist and update data directory (explicitly remove working directory)
    nml_file = WORKDIR + '/basic/test_basic/INPUT_ORG'
    nml = f90nml.read(nml_file)
    nml['runctl']['hstart'] = 1.0
    nml['runctl']['extra_option'] = True
    f90nml.write(nml, nml_file, force=True)
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic',
        '--update-namelist', '-v 10'], clean_before=False)
    check_successful_run(exit_status, stdout, stderr)
    clean_working_directory()
    # run with modified namelist parameters
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic'],
        clean_before=False)
    results = check_successful_run(exit_status, stdout, stderr)
    log = read_exe_logfile('basic/test_basic')
    assert 'Extra namelist option activated' in log
    timesteps = count_timesteps_in_stats_file(WORKDIR + '/basic/test_basic/YUPRTEST')
    assert timesteps == list(range(60, 121, 10))
    clean_data_directory()


def test_mpicmd_argument():
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_plain',
        '--mpicmd=' + os.path.join(os.getcwd(), 'mpicmd.sh')])
    check_successful_run(exit_status, stdout, stderr)
    log = read_exe_logfile('basic/test_plain')
    assert 'Running on 16 MPI ranks' in log


def test_identical_testcase():
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic'])
    check_successful_run(exit_status, stdout, stderr)
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_identical'],
        clean_before=False)
    check_successful_run(exit_status, stdout, stderr)


def test_changepar_testcase():
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic'])
    check_successful_run(exit_status, stdout, stderr)
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_changepar'],
        clean_before=False)
    check_successful_run(exit_status, stdout, stderr)
    number_of_steps = 7
    timesteps = count_timesteps_in_stats_file(WORKDIR + '/basic/test_changepar/YUPRTEST')
    assert timesteps == list(range(number_of_steps + 1))


def test_full_checker_list_testcase():
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_full'])
    check_successful_run(exit_status, stdout, stderr)


def test_parallel_testcase():
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_full'])
    check_successful_run(exit_status, stdout, stderr)
    nml = f90nml.read(WORKDIR + '/basic/test_full/INPUT_ORG')
    assert nml['runctl']['nprocx'] == 4
    assert nml['runctl']['nprocy'] == 4
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_parallel'],
        clean_before=False)
    check_successful_run(exit_status, stdout, stderr)
    nml = f90nml.read(WORKDIR + '/basic/test_parallel/INPUT_ORG')
    assert nml['runctl']['nprocx'] == 8
    assert nml['runctl']['nprocy'] == 2


def test_restart_testcase():
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_full'])
    check_successful_run(exit_status, stdout, stderr)
    exit_status, stdout, stderr = run_testsuite(['--only=basic,test_restart'],
        clean_before=False)
    check_successful_run(exit_status, stdout, stderr)
    timesteps = count_timesteps_in_stats_file(WORKDIR + '/basic/test_restart/YUPRTEST')
    assert timesteps == list(range(60, 121, 10))


# TODO: ICON test is currently not working
# def test_icon_argument():
# 	# first run a plain test
# 	exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic', '--args="--model=icon"'])
# 	check_successful_run(exit_status, stdout, stderr)
# 	# now run with the icon flag
# 	exit_status, stdout, stderr = run_testsuite(['--only=basic,test_basic','--icon'], clean_before=False)
# 	check_successful_run(exit_status, stdout, stderr)
# 	assert 'Running checks for ICON' in stdout


def test_full_testlist_from_xml():
    exit_status, stdout, stderr = run_testsuite()
    check_successful_run(exit_status, stdout, stderr)
