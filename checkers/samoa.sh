#!/bin/bash
#
#  !!! ATTENTION !!!
# This is not an official SAMOA version by KIT!
# This is a special version that includes the possibility to exclude a given number of boundary lines
# in the check. It works only with netCDF data that include "rlon" and "rlat" as dimensions.
# Burkhardt Rockel, HZG, 2016/06/20
#
##########################################################################################
#  ____    _    __  __  ___    _    
# / ___|  / \  |  \/  |/ _ \  / \   
# \___ \ / _ \ | |\/| | | | |/ _ \  
#  ___) / ___ \| |  | | |_| / ___ \ 
# |____/_/   \_\_|  |_|\___/_/   \_\
#
# SAnity check for MOdels of the Atmosphere (version 1.0)
#
# Copyright (C) 2012 Andrew Ferrone KIT (andrew.ferrone@kit.edu)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
########################################################################################## 
#
# The scripts checks for each variable in the GRIB/netCDF files if the min and max values
# lie within a range specified in a list with variables and min, max values.
# Fields containing NANs are also listed.
# Additionally constant fields (i.e. min=max) are listed (can be switched off).
# Optionally also fields including missing values can be listed (not standard).
#
# In principle this script should work for all model output that can be analysed with CDO
# At present the script is only tested for COSMO-ART model output
# The standard list is presently only for COSMO, COSMO-ART and COSMO-CLM
# If used for other models an alternative list has to be used
#
# Software dependencies:
#
# - to be run from the bourne shell
# - CDO (Climate Data Operators, <http://code.zmaw.de/projects/cdo>) 
#   Version 1.5 needed for GRIB files!
#   CDO needs to be built with GRIB and/or netCDF support
# - UNIX utilities: date, awk or gawk, basename, touch, sed, tail, mktemp
#
# Calling example:
#
# samo.sh [Arguments] ${input_path}/files*
# The nature of the files (GRIB/netCDF) is determined automatically
# Arguments (optional):
#   -cdf: specify manually netCDF files
#   -grb: specify manually GRIB files
#   -l /path/to/file: specify a alternative file containing list of variables
#   -m:    no color output (can be used for e.g. piping to less)
#   --miss_val_test_on: Turn on test for missing values
#   --equl_val_test_of: Turn off test for equal min and max values
#   --skull_off: Do not show ACSII skull art at the end of output
#
# Delivers: 
#
# a list of variables for each model level that do not pass the test to std out,
# with the problem highlighted in red (if -m option not specifed)
#
# Input:
#
# - GRIB/netCDF files that should be checked 
# - a list of varibles to be checked with plausible min and max value.
# 
# This list must be in the form:
#
# Varname     GRIBLev    GRIBno     Scale fac. Min        Max
# SO2         1          1.241      1.0        0          1e+20
#
# Author:                                  
#                                          
# Andrew Ferrone                           
# andrew.ferrone@kit.edu
#
# Contact:
#
# Isabel Kraut
# isabel.kraut@kit.edu                    
#                                                            _  _____ _____ 
# Karlsruhe Institute of Technology (KIT)                   | |/ /_ _|_   _|
# Institute for Meteorology and Climate Research (IMK-TRO)  | ' / | |  | |
# Hermann-von-Helmholtz-Platz 1                             | . \ | |  | |
# 76344 Eggenstein-Leopoldshafen, Germany                   |_|\_\___| |_|
#
# History:
#
# Version    Date       Name
# ---------- ---------- ----
# 1.0        10.2012     Andrew Ferrone
#  Initial Release
# 1.1        03.2013     Andrew Ferrone
#  Replaced readlink -f by $PWD/$0
#  Replaced awk by gawk
#  Added vcoord to exclude list
#  Correct bug in read list for scale
#
#
# Notes from the author:
#
# - The scripts only does a sanity check, it does not check the scientific consitency 
#   of the results
# - We suppose that the script and the standard list file are in the same directory
# - The scale factors is used for grib files to scales the min and max values in list
#
##########################################################################################

# 0) Clean ${TMP_DIR} even if interupted ##################################################

trap cleanup 1 2 3 6

cleanup()
{
  echo "Caught Signal ... cleaning up." 1>&2
  rm -rf ${TMP_DIR}
  echo "Done cleanup ... quitting." 1>&2
  exit 1
}

# 1) Preliminaries #######################################################################

# Get the absolut path to the script
SCRIPT=$PWD/$0
SCRIPTPATH=`dirname $SCRIPT`

# Path to the list with variables (is overwritten when -l specified)
# Assumed to be on the same path as script

path_list=$SCRIPTPATH/samoa.list

# Standard ouput is in color
not_monotone=TRUE

# Initialisations
file_type=NONE
file_type_m=NONE
file_type_a=NONE
problem=FALSE
miss_test_on=FALSE   # standard: no check for missing values
equal_test_on=TRUE   # standard: check if min and max values are equal
show_skull=TRUE  
NBOUNDCUT=0  # standard: the whole domain is evaluated  


# Functions       #######################################################################

# show program usage
usage(){
        echo 1>&2
        echo `basename $0` " SAnity check for MOdels of the Atmosphere (version 1.0)" 1>&2
        echo "Calling example:" 1>&2
        echo `basename $0` " [Arguments] ${input_path}/files*" 1>&2
        echo "The nature of the files (GRIB/netCDF) is determined automatically" 1>&2
        echo "Arguments (optional):" 1>&2
        echo "  -cdf: specify manually netCDF files" 1>&2
        echo "  -grb: specify manually GRIB files" 1>&2
        echo "  -l /path/to/file: specify a alternative file containing list of variables" 1>&2
        echo "  -m:   no color output (can be used for e.g. piping to less)" 1>&2
        echo "  --miss_val_test_on: Turn on test for missing values" 1>&2
        echo "  --equl_val_test_of: Turn off test for equal min and max values" 1>&2
        echo "  --skull_off: Do not show ACSII skull art at the end of output" 1>&2
        echo 1>&2
        exit
}

# Error/Warning handling

error_exit()
{
        echo 1>&2
	    echo "ERROR : ${1:-"Unknown Error"}" 1>&2
        echo "Type "`basename $0`" -h for more info."
        echo "Exiting now" 1>&2
        echo 1>&2
        rm -rf ${TMP_DIR}
	exit 1
}

error_continue()
{
        echo 1>&2
        echo "ERROR : ${1:-"Unknown Error"}" 1>&2
        echo 1>&2
        rm -rf ${TMP_DIR}/*
        continue
}

warning_continue()
{
        echo 1>&2
        echo "WARNING : ${1:-"Unknown Warning"}" 1>&2
        echo 1>&2
        rm -rf ${TMP_DIR}/*
        continue
}

# Show extracts of Licence

license()
{
  echo 1>&2
  echo  "SAMOA version 1.0 Copyright (C) 2012 Andrew Ferrone KIT " 1>&2
  echo  "  This program comes with ABSOLUTELY NO WARRANTY; for details type '"`basename $0`" -w'. " 1>&2
  echo  "  This is free software, and you are welcome to redistribute it under certain conditions;" 1>&2 
  echo  "  type '"`basename $0`" -c' for details. " 1>&2
  echo 1>&2
}

warranty()
{ 
  if [ ! -f ${SCRIPTPATH}/COPYING ]; then
    echo 1>&2
    echo "License could not be found in:" 1>&2
    echo ${SCRIPTPATH} 1>&2
    echo 1>&2
    echo "Please check <http://www.gnu.org/licenses/> for the full text of the" 1>&2
    echo "GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007." 1>&2
    echo 1>&2
  else
    echo 1>&2
    echo "Extract of the GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007" 1>&2
    echo "The full license can be found here:" 1>&2
    echo ${SCRIPT}/COPYING 1>&2
    echo 1>&2
    sed -n "589,610p" ${SCRIPTPATH}/COPYING 1>&2
    echo 1>&2
  fi

  exit
}

distribute()
{
  if [ ! -f ${SCRIPTPATH}/COPYING ]; then
    echo 1>&2
    echo "License could not be found in:" 1>&2
    echo ${SCRIPTPATH} 1>&2
    echo 1>&2
    echo "Please check <http://www.gnu.org/licenses/> for the full text of the" 1>&2
    echo "GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007." 1>&2
    echo 1>&2
  else
    echo 1>&2
    echo "Extract of the GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007" 1>&2
    echo "The full license can be found here:" 1>&2
    echo ${SCRIPTPATH}/COPYING 1>&2
    echo 1>&2
    sed -n "154,177p" ${SCRIPTPATH}/COPYING 1>&2
    echo 1>&2
  fi

  exit
}

# compare version numbers for cdo
# usage: vercmp <versionnr1> <versionnr2>
#         with format for versions xxx.xxx.xxx.xxx
# returns: -1 if versionnr1 earlier 
#           0 if versionnr1 equal
#           1 if versionnr1 later 

vercmp()
{
  local a1 b1 c1 d1 a2 b2 c2 d2
  v1=$1
  v2=$2
  set -- $( echo "$v1" | sed 's/\./ /g' )
  a1=$1 b1=$2 c1=$3 d1=$4
  set -- $( echo "$v2" | sed 's/\./ /g' )
  a2=$1 b2=$2 c2=$3 d2=$4
  ret=$(( (a1-a2)*1000000000+(b1-b2)*1000000+(c1-c2)*1000+(d1-d2) ))
  if [ $ret -lt 0 ] ; then
    v=-1
  elif [ $ret -eq 0 ] ; then
    v=0
  else
    v=1
  fi
  printf "%d" $v
  return
}

# Arguments       #######################################################################

# show usage if '-h' or  '--help' is the first argument or no argument is given
case $1 in
    ""|"-h"|"--help") license; usage ;;
esac

# Case selection for arguments    
for arg in "$@" ; do
    case ${arg} in
        -*)  true ;
             case ${arg} in
               -cdf) if [[ ${file_type_m} == "GRB" ]] ; then
                        echo "Incompatible arguments"
                        usage
                     else 
                     file_type_m="CDF"
                     shift 
                     fi ;;
               -grb) if [[ ${file_type_m} == "CDF" ]] ; then
                        echo "Incompatible arguments"
                        usage
                     else   
                     file_type_m="GRB"
                     shift
                     fi  ;;
               -l) if [[ ${2%${2#?}} != "-" ]] ; then
                     path_list=$2
                     shift 2
                   else
                     echo "Please provide a file with argument -l"
                     usage
                   fi ;;
                -m) not_monotone=FALSE
                    shift ;;
                -nb) if [[ ${2%${2#?}} != "-" ]] ; then
                     NBOUNDCUT=$2
                     shift 2
                   else
                     echo "Please provide a file with argument -nb"
                     usage
                   fi ;;
                --miss_val_test_on) miss_test_on=TRUE
                    shift ;;
                --equl_val_test_of) equal_test_on=FALSE
                    shift ;;
                --skull_off) show_skull=FALSE
                    shift ;;
                -w) warranty 
                    shift ;;
                -c) distribute 
                    shift ;;                                                            
               -*) echo "Unrecognized argument: " ${arg}
                   usage
               ;;
            esac
        ;;
    esac
done            

#  Get the list of files to be transformed
    file_list="${@}"

# Print license information

license

# Check if input files are provided    
if [[ ! -n ${file_list} ]]; then
   error_exit "Please provide at least one GRIB/netCDF input file"
fi    
    
# Create temporay directory
TMP_DIR=$(mktemp -dt $(basename $0).$$.XXXXXXXXXX) 

# Check if ${path_list} exist and is not empty    
if [ ! -s ${path_list} ]; then
    error_exit ${path_list}" does not exist or is empty."
fi 

# Check if ${path_list} is an ASCII file file with six columns
# Ignore lines starting with #
awk '/^[[:space:]]*#/{ NR--;next}{if(NF != 6)print $0}' ${path_list} > ${TMP_DIR}/list_test
if [[ -s ${TMP_DIR}/list_test ]]; then
    error_exit  ${path_list}" does not seem to be an ASCII text file with six columns."
fi    

# Minimal version for which CDO has been tested

min_version=1.5.0

# Get CDO version on system

version=`/apps/dom/UES/jenkins/6.0.UP04/gpu/easybuild/software/CDO/1.9.0-CrayGNU-17.08/bin/cdo -V 2>&1 | head -1 | awk '{for(x=1;x<=NF;x++) if($x~"version") print $(x+1)}'`

# Warn the user if version is lower than min_version

v=$( vercmp $version $min_version )

if [[ $v -lt 0 ]]; then
  warning_continue "The CDO version on this system is: "${version}".
          This script has been tested for version "${min_version}".
          In particular for GRIB files the script might not work."
fi

# 2) File loop ###########################################################################

for file in ${file_list} ; do

# Check if ${file} exists
if [ ! -s ${file} ]; then
    error_continue ${file}" does not exists."
fi

# Determine the file type (GRIB/netCDF) using CDO
/apps/dom/UES/jenkins/6.0.UP04/gpu/easybuild/software/CDO/1.9.0-CrayGNU-17.08/bin/cdo -s sinfo ${file} > ${TMP_DIR}/file_type

# Check if cdo exited properly
if [ "$?" != "0" ]; then
  error_continue "CDO is not able to read file: "${file}
fi

# Get file type out of sinfo dump
file_type_a=`awk 'NR>1{exit};{print $3}' ${TMP_DIR}/file_type`

# If the file type has been manually specified
if [ ${file_type_m} != "NONE" ]; then
  file_type=${file_type_m}
else

# Get automatic file type
  case ${file_type_a} in 
     "netCDF"|"netCDF2"|"netCDF4") file_type="CDF" ;;
     "GRIB") file_type="GRB" ;;
     *) error_continue "The file "${file}" seems to have type "${file_type_a}"
        which is not implemented in this version of SAMOA.
        If the file type is nevertheless GRIB/netCDF try specifying it manually."
   esac
fi

#  Get the file name (without path) and print it to the user
   file_name=`basename ${file}`
   echo 1>&2
   echo "Checking "$file_name " ("${file_type} " file)" 1>&2
   echo 1>&2
   
#  Get for all varibales info via CDO
   if [[ ${file_type} == "CDF" ]]; then   
     IE_TOT=$(/opt/cray/pe/netcdf/4.4.1/bin/ncdump -h ${file}  | grep -m 1 "rlon =" | cut -d\  -f 3)
     JE_TOT=$(/opt/cray/pe/netcdf/4.4.1/bin/ncdump -h ${file}  | grep -m 1 "rlat =" | cut -d\  -f 3)
     let "IESPONGE = ${IE_TOT} - NBOUNDCUT - 1"
     let "JESPONGE = ${JE_TOT} - NBOUNDCUT - 1"
     /apps/daint/UES/jenkins/6.0.UP02/gpu/easybuild/software/NCO/4.6.0-CrayGNU-2016.11/bin/ncks -h -d rlon,${NBOUNDCUT},${IESPONGE} -d rlat,${NBOUNDCUT},${JESPONGE} ${file} tmp.nc
     /apps/dom/UES/jenkins/6.0.UP04/gpu/easybuild/software/CDO/1.9.0-CrayGNU-17.08/bin/cdo -s infov tmp.nc > ${TMP_DIR}/${file_name}_info
     rm tmp.nc
   else
     /apps/dom/UES/jenkins/6.0.UP04/gpu/easybuild/software/CDO/1.9.0-CrayGNU-17.08/bin/cdo -s info ${file} > ${TMP_DIR}/${file_name}_info
   fi

# Check if cdo exited properly
if [ "$?" != "0" ]; then
  error_continue "CDO is not able to read "${file_type}" file:"${file}
fi

# Get the title line starting with "-1" for later usage
  echo > ${TMP_DIR}/first_line 
  echo "The following problems were detected in: "$file_name >> ${TMP_DIR}/first_line
  echo >> ${TMP_DIR}/first_line  
  awk '{ORS=" "}; {if ( $1 == -1 ) {printf ("%-10s %-8s %-16s %-8s %-4s %-2s %-11s %-11s %-11s \n", \
       $3, $4, $5, $6, $7, $9, $10, $11, $13);exit}}'  ${TMP_DIR}/${file_name}_info >> ${TMP_DIR}/first_line
# Remove all lines not starting with a numeric postive value
  awk -F" " ' $1 ~ "^[0-9][0-9]*$" { print $0 }' ${TMP_DIR}/${file_name}_info > ${TMP_DIR}/${file_name}_info_no_head
  
#Create an empty file that will contain variables not found in ${TMP_DIR}/${file_name}_info
touch ${TMP_DIR}/var_not_in_list
touch ${TMP_DIR}/was_problem

# Create basic string for testing 
log_test='$(9)<min[$13]*scale[$13]||$(11)>max[$13]*scale[$13]||$(10)<min[$13]*scale[$13]'
log_test=${log_test}'||$(10)>max[$13]*scale[$13]'

# Add test for missing value if option has been chosen
if [[ ${miss_test_on} == "TRUE" ]]; then   
     log_test=${log_test}'||$(7)!=0'
fi

# Add test for equal min and max values if option has been chosen
if [[ ${equal_test_on} == "TRUE" ]]; then   
     log_test=${log_test}'||$(9)==$(11)'
fi

   
# Check for each line of ${TMP_DIR}/${file_name}_info_no_head the log_test for
# variable provided in ${TMP_DIR}/min_max_file, and if test not passed print out
# line from ${TMP_DIR}/${file_name}_info_no_head
# In case varible not found in ${path_list} put it into ${TMP_DIR}/var_not_in_list

awk 'BEGIN { 
     while ((getline < "'${path_list}'") > 0)
       {if ( "'${file_type}'" == "CDF") 
        { var[$1] = 1 ; scale[$1] = 1 ; min[$1] = $5 ; max[$1] = $6 }  
       else
        { var[$3] = 1 ; name[$3] = $1 ; scale[$3] = $4 ; min[$3] = $5 ; max[$3] = $6 } 
     } } 
       # END BEGIN 
     {if ($13 in var) {
       # In grib files T_SO uses "0" as Missing Value
      {if ( "'${file_type}'" == "GRB" && name[$5] == "T_SO" ) min[$5] = 0 }
      {if ('`echo ${log_test}`')
       { line = $(0)
        while ((getline < "'${TMP_DIR}/first_line'") > 0) 
         # If we first encounter a test that is not passed, print out first line
        { print }
        $(0) = line
        {if ( "'${not_monotone}'" == "TRUE") { # Check if output in color
         {if ($(9) < min[$13]*scale[$13]) # Color in red the ouput that causes the problem
          {print "True" > "'${TMP_DIR}/was_problem'";
           line_min = "\033[1;31m"$9"\033[0m"; $9 = line_min} }
         {if ($(10) < min[$13]*scale[$13] || $(10) > max[$13]*scale[$13])
          {print "True" > "'${TMP_DIR}/was_problem'";
           line_mean = "\033[1;31m"$10"\033[0m"; $10 = line_mean} } 
         {if ($(11) > max[$13]*scale[$13])
          {print "True" > "'${TMP_DIR}/was_problem'";
           line_max = "\033[1;31m"$11"\033[0m"; $11 = line_max} }
         {if ("'${miss_test_on}'" == "TRUE" && $(7) != 0) 
          {print "True" > "'${TMP_DIR}/was_problem'";
           line_miss = "\033[1;31m"$7"\033[0m"; $7 = line_miss} }
         {if ("'${equal_test_on}'" == "TRUE" && $(9)==$(11)) 
          {print "True" > "'${TMP_DIR}/was_problem'";
           line_min = "\033[1;31m"$9"\033[0m"; $9 = line_min;
           line_mean = "\033[1;31m"$10"\033[0m"; $10 = line_mean;
           line_max = "\033[1;31m"$11"\033[0m"; $11 = line_max} }                             
        }  }
        {if ( "'${file_type}'" == "GRB")
         {name_now = name[$5]"("$13")" # Replace the GRIB number by varname(GRIB number)
          $13=name_now  } }
        {printf ("%-10s %-8s %-16s %-8s %-4s %-2s %-11s %-11s %-11s  \n", \
                 $3, $4, $5, $6, $7, $9, $10, $11, $13) 
         print "True" > "'${TMP_DIR}/was_problem'"}
        } } } 
       else
        # The following variables are not checked
        { if (!($13 =="Name" || $13=="slonu" || $13=="slatu" || $13=="slonv" || $13=="slatv" || $13=="vcoord")) 
        { print $13 > "'${TMP_DIR}/var_not_in_list'" } } 
      }' ${TMP_DIR}/${file_name}_info_no_head             

# Check if  ${TMP_DIR}/var_not_in_list  is not empty
             
    if [[ -s ${TMP_DIR}/var_not_in_list ]] ; then
      # Remove dublicate lines
      awk '!x[$0]++' ${TMP_DIR}/var_not_in_list > ${TMP_DIR}/var_not_in_list.no_dublicates
      # Output info about missing varibles
      warning_continue "The following variable(s):  
      "`tr "\n" ", " < ${TMP_DIR}/var_not_in_list.no_dublicates`" 
      could not be found in "${path_list}
    fi
    
    [[ -s ${TMP_DIR}/was_problem ]] && problem=TRUE
    
   rm  ${TMP_DIR}/* # Clean up
   
done    # file loop

if [[ ${problem} == "TRUE" && ${show_skull} == "TRUE" ]]; then
  # Create skull file (last 23 lines of the present script)
  tail -23 ${SCRIPT} > ${TMP_DIR}/skull
  # And print it (with check for monotone output)
  if [[ ${not_monotone} == "TRUE" ]]; then
    awk '{print "\033[5m"$0"\033[0m"}' ${TMP_DIR}/skull 1>&2
  else
    awk '1' ${TMP_DIR}/skull 1>&2
  fi # monotone
fi # problem


# 3) Clean up ############################################################################

 rm -rf ${TMP_DIR}

if [ ${problem} == "TRUE" ] ; then
  exit 2
else
  exit 0
fi 
 
#

# Skull  #################################################################################
# DO NOT ADD LINES BELOW THE SKULL (from <http://www.ascii-art.de/ascii/s/skull.txt>)


            _,.-----.,_            
         ,-~           ~-.         
       ,^___           ___^.       
      /~"   ~"   .   "~   "~\      
     Y  ,--._    I    _.--.  Y     
     | Y     ~-. | ,-~     Y |     
     | |        }:{        | |     
     j l       / | \       ! l     
  .-~  (__,.--" .^. "--.,__)  ~-.  
 (           / / | \ \           ) 
  \.____,   ~  \/"\/  ~   .____,/  
   ^.____                 ____.^   
      | |T ~\  !   !  /~ T| |      
      | |l   _ _ _ _ _   !| |      
      | l \/V V V V V V\/ j |      
      l  \ \|_|_|_|_|_|/ /  !      
       \  \[T T T T T TI/  /       
        \  `^-^-^-^-^-^'  /        
         \               /         
          \.           ,/          
            "^-.___,-^"            

