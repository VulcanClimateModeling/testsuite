#!/usr/bin/python

#########################################################
# This script reads in a file containing ICON output,   #
# uses CDO to calculate min., mean, and max. values at  #
# each level for all variables, and prints these values #
# to a text file for use in the technical testsuite.    #
#                                                       #
# Written April 12, 2019 by Katie Osterried.            #
#########################################################

import subprocess
import argparse

# Set up the arguments
parser = argparse.ArgumentParser()
parser.add_argument('-file', dest = 'file', default = '~', help = "ICON output file to process" )
args = parser.parse_args()

print "Processing file:{}".format(args.file)

# Get the min,mean, and max of the variables
procmn = subprocess.Popen("cdo -s fldmin {} min.nc".format(args.file), stdout=subprocess.PIPE, shell=True)
procmx = subprocess.Popen("cdo -s fldmax {} max.nc".format(args.file), stdout=subprocess.PIPE, shell=True)
procmean = subprocess.Popen("cdo -s fldmean {} mean.nc".format(args.file), stdout=subprocess.PIPE, shell=True)

procvar = subprocess.Popen("cdo -s showvar {}".format(args.file), stdout=subprocess.PIPE, shell=True)
(varbs, err) = procvar.communicate()

# Get the max number of time steps in the file
procgtime = subprocess.Popen("cdo -s ntime {}".format(args.file), stdout=subprocess.PIPE, shell=True)
(gnt, err) = procgtime.communicate()

# Wait for the subprocesses to finish before moving on to next step

procmn.wait()
procmx.wait()
procmean.wait()
procvar.wait()
procgtime.wait()

varb = varbs.split()  

# Open text file for writing
f = open('output_stat.dat', 'wb')
f.write("{:>5} {:>3} {:>3} {:>20} {:>5} {:>5} {:>20} {:>5} {:>5} {:>20}\n".format("# var", "nt", "lev", "min", "imin", "jmin", "max", "imax", "jmax", "mean"))

# Print values to text file
for i in range(0,int(gnt)):
    for j in range(0,len(varb)):
        # Get the number of levels and number of time steps
        proctime = subprocess.Popen("cdo -s ntime -selvar,{} {}".format(varb[j], args.file), stdout=subprocess.PIPE, shell=True)
        (nt, err) = proctime.communicate()
    
        proclv = subprocess.Popen("cdo -s nlevel -selvar,{} {}".format(varb[j],args.file), stdout=subprocess.PIPE, shell=True)
        (nlevel, err) = proclv.communicate()
        proctime.wait()
        proclv.wait()

        if int(nt)>0 or i==0:
           procvmean = subprocess.Popen("ncks --trd -V -C -H -v {} -d time,{} -s \"%+16.20f\n\" mean.nc".format(varb[j], i), stdout=subprocess.PIPE, shell=True)
           (meanarray, err) = procvmean.communicate()
           procvmn = subprocess.Popen("ncks --trd -V -C -H -v {} -d time,{} -s \"%+16.20f\n\" min.nc".format(varb[j], i), stdout=subprocess.PIPE, shell=True)
           (minarray, err) = procvmn.communicate()
           procvmx = subprocess.Popen("ncks --trd -V -C -H -v {} -d time,{} -s \"%+16.20f\n\" max.nc".format(varb[j], i), stdout=subprocess.PIPE, shell=True)
           (maxarray, err) = procvmx.communicate()


           procvmean.wait()
           procvmx.wait()
           procvmn.wait()
           mnarray=meanarray.split()
           mnnarray=minarray.split()
           mxarray=maxarray.split()

           for k in range(int(nlevel)):
               f.write("{:>5} {:>3} {:>3} {:1.14E} {:>5} {:>5}  {:1.14E} {:>5} {:>5}  {:1.14E}\n".format(varb[j], i, k, float(mnnarray[k]), 1, 1, float(mxarray[k]), 1, 1, float(mnarray[k])))

f.close()
procrm = subprocess.Popen("rm max.nc min.nc mean.nc", stdout=subprocess.PIPE, shell=True)

