#!/usr/bin/env python

"""
COSMO TECHNICAL TESTSUITE

Python class to wrap around YUPRTEST files and allow the owner
to use it as an iterator in order to read the data line-by-line

c = Compare('YUPRTEST.ref', 'YUPRTEST.ref', 'THRESHOLDS')
c.compare_data()
c.thresholds.mode = "const"
c.thresholds.increase_factor = 1.0
c.update_thresholds()
c.compare_data()
c.print_results()
"""

# built-in modules
import os

# other modules
from ts_thresholds import Thresholds

# information
__author__      = "Oliver Fuhrer, Santiago Moreno"
__email__       = "cosmo-wg6@cosmo.org"
__maintainer__  = "oliver.fuhrer@meteoswiss.ch"

# get name of myself
myname = os.path.basename(__file__)
header = myname + ': '


def column(matrix, i):
    """return a specific column from a list of lists (matrix)"""
    return [row[i] for row in matrix]


class Yuprtest(object):
    """class to wrap around a YUPRTEST file"""


    def __init__(self, filename):
        self._filename = filename  # name of associated YUPRTEST file
        self._file = None  # file handle
        self._raw = []  # raw data
        self._data = []  # processed data
        self._headerlines = 0  # number of header lines
        self._lineno = 0  # current line number (for iterator)
        self.__read_data()

    def __iter__(self):
        return self

    def __read_data(self):
        """read data in file and do some basic processing"""
        lineno = 0
        header = True
        self._file = open(self._filename)  # open file
        for line in self._file:  # read data and parse line
            lineno += 1
            data = self.__parse_line(line, lineno)
            if data:
                header = False
                self._raw.append(line.strip())
                self._data.append(data)
            else:
                if not header:
                    raise IOError('Parse error on line ' + str(lineno))
        self._file.close()

    def __parse_line(self, line, lineno):
        data = line.strip().split()
        if (len(data) == 0):  # check for zero length lines
            self._headerlines += 1
            return None
        if (data[0][0] == "#"):  # remove comment lines
            self._headerlines += 1
            return None
        if (len(data) != 10):
            raise ValueError('Strange record found in ' + self._filename +
                            ' on line number ' + str(lineno))
        data.pop(8)  # remove j-position of maximum
        data.pop(7)  # remove i-position of maximum
        data.pop(5)  # remove j-position of minimum
        data.pop(4)  # remove i-position of minimum
        # entry: var step level minval maxval meanval
        data = [data[0], int(data[1]), int(data[2]), float(data[3]),
                float(data[4]), float(data[5])]
        return data

    def __check_timesteps(self):
        """Check that entries per variable is multiple of # timesteps and that
           all timesteps are present"""
        steps = column(self._data, 1)
        counts = [steps.count(step) for step in set(steps)]
        if not len(set(counts)) == 1:
            raise ValueError('Variables in file contain different timesteps')

    def __str__(self):
        """pretty print thresholds"""
        return (self._data)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._data == other._data
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def variables(self):
        return sorted(list(set(column(self._data, 0))))

    @property
    def steps(self):
        return sorted(list(set(column(self._data, 1))))

    @property
    def levels(self):
        return sorted(list(set(column(self._data, 2))))

    @property
    def data(self):
        return self._data

    def __next__(self):
        return self.next()

    def next(self):
        if self._lineno < len(self._data):
            self._lineno += 1
            return self._data[self._lineno - 1]
        else:
            raise StopIteration()

    def getline(self):
        for i in self._data:
            yield i

    def getSubline(self, subSetSteps):
        # extract subset of lines
        subData = filter(lambda r: r[1] in subSetSteps, self._data)
        for i in subData:
            yield i

    def skip(self, step):
        pass

class YuprLine(object):
    def __init__(self, status, diff, var, step, level, thresh, pos):
        self._status = status
        self._diff = diff
        self._var = var
        self._step = step
        self._level = level
        self._thresh = thresh
        self._pos = pos

    @property
    def pos(self):
        return self._pos

    @property
    def thresh(self):
        return self._thresh

    @property
    def level(self):
        return self._level

    @property
    def step(self):
        return self._step

    @property
    def var(self):
        return self._var

    @property
    def diff(self):
        return self._diff

    @property
    def status(self):
        return self._status

class Compare(object):
    """class to compare two YUPRTEST files using a thresholds object"""


    def __init__(self, filename1, filename2, thresh):
        self._filename1 = filename1
        self._filename2 = filename2
        self._yu1 = Yuprtest(filename1)
        self._yu2 = Yuprtest(filename2)
        self._threshold = Thresholds(thresh)

    @property
    def thresholds(self):
        return self._threshold

    def __compute_difference(self, ref, value):
        """calculate difference between to threshold values depending on the given minval"""
        diff = 0.0
        if self._threshold.minval < 0.0:
            diff = abs(value - ref)  # absolute difference
        elif abs(ref) > self._threshold.minval:
            diff = abs((value - ref) / ref)  # relative difference
        return diff

    def __compare_values(self, var, timestep, ref, value):
        """gets the difference of two values based on which a status code is returned"""
        diff = self.__compute_difference(ref, value)
        if self._mode == "compare":
            thresh = self._threshold.get_threshold(var, timestep)
            if diff == 0.0:
                return 0, diff, thresh  # MATCH
            if diff <= thresh:
                return 1, diff, thresh  # OK
            else:
                return 2, diff, thresh  # FAIL
        elif self._mode == "update":
            if (diff > 0.0):
                self._threshold.update_threshold(var, timestep, diff)
            return 0, None, None

    def __compare_entry(self, ref, data):
        """compares min, max and mean of two YUPRTEST files and
        then returns everything needed to evaluate if the test succeeded"""
        (var, step, level, minval1, maxval1, meanval1) = ref
        (var2, step2, level2, minval2, maxval2, meanval2) = data
        if (var, step, level) != (var2, step2, level2):
            raise ValueError('Non-matching data entries cannot be compared on line' + str(self._lineno))
        (status1, diff1, thresh) = self.__compare_values(var, step, minval1, minval2)
        (status2, diff2, thresh) = self.__compare_values(var, step, maxval1, maxval2)
        (status3, diff3, thresh) = self.__compare_values(var, step, meanval1, meanval2)
        if self._mode == "update":
            return None
        status = max([status1, status2, status3])
        diff = max([diff1, diff2, diff3])
        pos = ["minimum", "maximum", "mean"][[diff1, diff2, diff3].index(min([diff1, diff2, diff3]))]
        return YuprLine(status, diff, var, step, level, thresh, pos)

    def __update_status(self, yupr_line):
        rel = yupr_line.diff
        if yupr_line.thresh > 0.0:
            rel = yupr_line.diff / yupr_line.thresh
        step = str(yupr_line.step)
        var = yupr_line.var

        # update status for this timestep
        if not step in self._status.keys():
            self._status[step] = yupr_line.status
        self._status[step] = max(self._status[step], yupr_line.status)
        # update maxdiff for this timestep and variable
        if not step in self._maxdiff.keys():
            self._maxdiff[step] = {}
        if not var in self._threshold.variables:
            var = [yupr_line.var, "*"]
        else:
            var = [yupr_line.var]
        for x in var:
            if not x in self._maxdiff[step].keys():
                self._maxdiff[step][x] = [0, -float('Inf'), -float('Inf')]
            if yupr_line.status >= self._maxdiff[step][x][0] and rel > self._maxdiff[step][x][1]:
                self._maxdiff[step][x] = [yupr_line.status, rel, yupr_line.diff, yupr_line.level, yupr_line.thresh, yupr_line.pos]

    def print_results(self):
        """print results"""
        print('%5s  %s  %7s  %s' % (
            'nt', '  '.join(['%9s' % x for x in self._threshold.variables + ['other']]), 'status', 'reason'))
        for step in [str(x) for x in sorted(set(self._yu1.steps) & set(self._yu2.steps))]:
            vals = [self._maxdiff[step][x][2] for x in self._threshold.variables + ['*']]
            stat = ["MATCH", "OK", "FAIL"][self._status[step]]
            reason = 'none'
            if stat == "FAIL":
                # generate reason
                for var in self._maxdiff[step].keys():
                    if var == "*":
                        continue
                    m = self._maxdiff[step][var]
                    if 'mmax' in locals():
                        if m[0] >= mmax[0] and m[1] > mmax[1]:
                            mmax = m + [var]
                    else:
                        mmax = m + [var]
                if 'mmax' in locals() and mmax[0] > 1:
                    reason = str(mmax[5]) + ' of ' + str(mmax[-1]) + ' on level ' + str(mmax[3]) \
                            + ' (%9.2e' % mmax[2] + ' > ' + str(mmax[4]) + ')'
            print('%5d  %s  %7s  %s' % (int(step), '  '.join(['%9.2e' % x for x in vals]), stat, reason))

    def compare_data(self):
        """compare two yu files line by line and return the highest error"""
        self._mode = "compare"
        self._lineno = 0
        self._maxdiff = {}
        self._status = {}
        steps1 = set(self._yu1.steps)
        steps2 = set(self._yu2.steps)
        commonSteps = steps1 & steps2
        # Only compare common time steps
        for x, y in zip(self._yu1.getSubline(commonSteps), self._yu2.getSubline(commonSteps)):
            yupr_line = self.__compare_entry(x, y)
            self.__update_status(yupr_line)
            self._lineno += 1

        stat = max(self._status.values())
        # fix thresholds variables which were not encountered
        for step in [str(x) for x in self._yu1.steps]:
            if step not in self._maxdiff.keys():
                print("WARNING: Not enough reference data, comparison only until max Time steps reference.")
                print(" Time steps reference:  {steps}".format(steps=str(self._yu2.steps)))
                print(" Time steps comparison: {steps}".format(steps=str(self._yu1.steps)))
                break
            for var in self._threshold.variables + ["*"]:
                if not var in self._maxdiff[step].keys():
                    self._maxdiff[step][var] = [float('NaN'), float('NaN'), float('NaN'), float('NaN')]
        return stat

    def reset_thresholds(self):
        """Reset the thresholds in a loaded file"""
        self._threshold._set_thresholds_to_zero()

    def update_thresholds(self):
        """Updates the thresholds of the corresponding threshold file"""
        # Note: The effect update is done in the __compare_values 
        self._mode = "update"
        self._lineno = 0
        for x, y in zip(self._yu1.getline(), self._yu2.getline()):
            self.__compare_entry(x, y)
            self._lineno += 1
        
        # Set the default threshold to the maximum of all the variables
        self._threshold.update_default_thresholds()
        
    def write_threshold_to_file(self, file_location):
        self._threshold.to_file(file_location)

