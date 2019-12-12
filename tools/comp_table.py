#!/usr/bin/env python2

"""
COSMO TECHNICAL TESTSUITE

General purpose script to compare two files containing tables
Only lines with given table pattern are considered
"""

# built-in modules
import os, sys, string

# information
__author__     = "Xavier Lapillonne"
__maintainer__ = "xavier.lapillonne@meteoswiss.ch"


def cmp_table(file1,file2,colpattern,minval,threshold,verbose=1,maxcompline=-1):

    # General purpose script to compare two files containing tables
    # Only lines with given table column pattern. Column to be compared are marked with c
    # column to discard with x 

    #init
    ncomp=0
    nerror=0
    lerror=False
    epsilon=1e-16 #used to avoid division by zero in case minval is zero
    
    # check file existence
    if not(os.path.exists(file1)):
        print('File %s does not exist' %(file1))
        return -1
    elif not(os.path.exists(file2)):
        print('File %s does not exist' %(file2))
        print('File '+file2+' does not exist')
        return -1

    # convert input
    colpattern=[x=='c' for x in list(colpattern)]
    threshold=float(threshold)
    minval=float(minval)
    
    # open file
    data1=open(file1).readlines()
    data2=open(file2).readlines()

    # get max record
    nd1=len(data1)
    nd2=len(data2)

    # check that files are not empty
    if nd1==0:
        print('file %s is empty!' %(file1))
        return -1
    if nd2==0:
        print('file %s is empty!' %(file2))
        return -1

    if nd1!=nd2 and verbose>1:
        print('Warning: %s and %s have different size, comparing commun set only \n' %(file1,file2))

    ncdata=min(nd1,nd2)
    if (maxcompline>0):
        ncdata=min(ncdata,maxcompline)


    # Iterates through the lines
    for il in range(ncdata):
        l1=data1[il].split()
        l2=data2[il].split()
        l1match=matchColPattern(l1,colpattern)
        l2match=matchColPattern(l2,colpattern)
        # compare values if both lines are compatible
        if l1match and l2match:
            for ic in range(len(colpattern)):
                if colpattern[ic]:
                    v1=float(l1[ic])
                    v2=float(l2[ic])
                    val_abs_max=max(abs(v1),abs(v2))
                    if val_abs_max > minval:
                        ncomp+=1
                        diff=abs(v1-v2)/(val_abs_max+epsilon)
                        if diff>threshold:
                            nerror+=1
                            # Print error
                            if verbose>1:
                                print('Error %2.2e above %2.2e thresold at line %i, col %i' %(diff,threshold,il+1,ic+1))
                                print('> %s' %(file1))
                                print(data1[il])
                                print('< %s' %(file2))
                                print(data2[il])
                            #save line for first error
                            if not lerror:
                                differ=diff
                                linerr=il+1
                                colerr=ic+1
                                linerr1=data1[il]
                                linerr2=data2[il]
                                
                            lerror=True
    


    if ncomp==0:
        print('Warning :no line to compare')
        nerror=-2

    if lerror and verbose>0:
        print('Compared values: %i, errors above threshold: %i ; %i %% ' %(ncomp,nerror,nerror*100./ncomp))
        if verbose==1:
            print('First error %2.2e above %2.2e thresold at line %i, col %i' %(differ,threshold,linerr,colerr))
            print('> %s' %(file1))
            print(linerr1)
            print('< %s' %(file2))
            print(linerr2)

    return nerror

#----------------------------------------------------------------------------
# Local functions
def matchColPattern(line,colpattern):
    if len(line)!=len(colpattern):
        return False

    try:
        for i in range(len(colpattern)):
            if colpattern[i]: f=float(line[i])
    except ValueError:
        return False
        
    return True

#-----------------------------------
#execute as a script 
if __name__ == "__main__":

    if len(sys.argv)==6:
        cmp_table(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4], \
             sys.argv[5])
    elif len(sys.argv)==7:
        cmp_table(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4], \
             sys.argv[5],sys.argv[6])
    elif len(sys.argv)==8:
        cmp_table(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4], \
             sys.argv[5],sys.argv[6],sys.argv[7])    
    else:
        print('''USAGE : ./comp_table file1 file2 colpattern minval threshold [verbose maxcompline]
        General purpose script to compare two files containing tables         
        Only lines with given table column pattern. Column to be compared must be numbers are marked with c 
        column to discard with x 
        colpattern c for compare or x for ignore, ex: xccx discard first and last column of a 4 column table 
''')

