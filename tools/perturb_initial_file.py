#!/usr/bin/python

#########################################################
# This script reads in a file containing ICON input,    #
# and uses NCO to generate a random perturbation to the #
# prognostic variables.                                 #
#                                                       #
# Written May 6, 2019 by Katie Osterried.               #
#########################################################

import argparse
import subprocess

# Set up the arguments
parser = argparse.ArgumentParser()
parser.add_argument('-file', dest = 'file', default = '~', help = "ICON input file to process" )
parser.add_argument('-rperturb', dest = 'rperturb', default = '0.0', help = "perturbation coefficient" )
parser.add_argument('-outputfile', dest = 'outputfile', default = '~', help = "output file name" )
args = parser.parse_args()

print "Processing file:{} with {} perturbation coefficient".format(args.file, args.rperturb)

#Make a temporary folder 
procmkdir = subprocess.Popen("mkdir temp", stdout=subprocess.PIPE, shell=True)
procmkdir.wait()

# Copy the original file
proccp = subprocess.Popen("cp {} {}".format(args.file, args.outputfile), stdout=subprocess.PIPE, shell=True)
proccp.wait()

# Loop over the prognostic variables
for var in ['T']: 
    # Convert variable to double precision
    procconv = subprocess.Popen("ncap2 -O -s '{}=double({})' {} {}".format(var,var,args.outputfile,args.outputfile), stdout=subprocess.PIPE, shell=True)
    procconv.wait()
    # Extract the variable into it's own file
    procselvar = subprocess.Popen("cdo -s -b F64 -selvar,{} {} temp/{}.nc".format(var,args.file,var), stdout=subprocess.PIPE, shell=True)
    procselvar.wait()
    # Get the number of levels
    proclv = subprocess.Popen("cdo -s nlevel temp/{}.nc".format(var), stdout=subprocess.PIPE, shell=True)
    (nlevel, err) = proclv.communicate()
    proclv.wait()
    #Generate a random field for each level of the variable
    for i in range(int(nlevel)):
        procrand = subprocess.Popen("cdo -s -f nc4 -b F64 random,temp/{}.nc,{} temp/random{}.nc".format(var,i+4450,i), stdout=subprocess.PIPE, shell=True)
        procrand.wait()
    #Concatenate all the random field files
    proccat = subprocess.Popen("ncecat -h temp/random*.nc temp/rand.nc", stdout=subprocess.PIPE, shell=True)
    proccat.wait()
    # Change range from (0,1) to (-1,1) and multiply by perturbation coefficient
    # eps = rperturb * (2.0 * random - 1.0)
    procrand1 = subprocess.Popen("cdo -s -b F64 mulc,2.0 temp/rand.nc temp/rand1.nc", stdout=subprocess.PIPE, shell=True)
    procrand1.wait()
    procrand2 = subprocess.Popen("cdo -s -b F64 subc,1.0 temp/rand1.nc temp/rand2.nc", stdout=subprocess.PIPE, shell=True)
    procrand2.wait()
    procrand3 = subprocess.Popen("cdo -s -b F64 mulc,{} temp/rand2.nc temp/eps.nc".format(args.rperturb), stdout=subprocess.PIPE, shell=True)
    procrand3.wait()
    # Multiply the field by the perturbation factor
    # field = field * (1.0 + eps)
    proceps1 = subprocess.Popen("cdo -s -b F64 addc,1.0 temp/eps.nc temp/eps1.nc", stdout=subprocess.PIPE, shell=True)
    proceps1.wait()
    proceps2 = subprocess.Popen("cdo -s -b F64 mul temp/eps1.nc temp/{}.nc temp/{}pert.nc".format(var,var), stdout=subprocess.PIPE, shell=True)
    proceps2.wait()   
    # Add the perturbation to the original file
    procreplace = subprocess.Popen("ncks -A -v {} temp/{}pert.nc {}".format(var,var,args.outputfile), stdout=subprocess.PIPE, shell=True)
    procreplace.wait()
    #Remove the temporary files
    procrmtmp = subprocess.Popen("rm temp/*.nc", stdout=subprocess.PIPE, shell=True)
    procrmtmp.wait()
procrmdir = subprocess.Popen("rm -r temp", stdout=subprocess.PIPE, shell=True)
procrmdir.wait()
