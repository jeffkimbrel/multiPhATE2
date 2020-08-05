#!/usr/bin/env python

################################################################
#
# CGC_main.py  # Compare Gene Calls Main
#
# Programmer: Carol Zhou
#
# Description:  Accepts a list of input files, each comprising a set of
#    gene calls from a given gene caller program (e.g., Prodigal, Glimmer,
#    GeneMark, RAST, PHANOTATE, custom).  Outputs comparisons accross the gene calls. 
#    Note:  The input files are re-formatted using CGC_parser.py, so that
#    they have a common format and identify the gene caller in the comments
#    at the top of the file.
#
################################################################

# This code was developed by Carol L. Ecale Zhou at Lawrence Livermore National Laboratory.
# THIS CODE IS COVERED BY THE BSD LICENSE. SEE INCLUDED FILE BSD.pdf FOR DETAILS.

import os

PHATE_PIPELINE = True  # Running this code within the PhATE pipeline. Set this to False if running code independently
#PHATE_PIPELINE = False

##### VERBOSITY

# Note: These environment variables are set in CGC_parser.py, which is usually run before CGC_main.py
# Therefore, if you have not run CGC_parser.py first, then you need to set these environment variables
# by hand at the command line. Set env vars to 'True' or 'False' as strings, not booleans.

PHATE_PROGRESS = False
PHATE_MESSAGES = False
PHATE_WARNINGS = False

PHATE_PROGRESS_STRING = os.environ["PHATE_PHATE_PROGRESS"]
PHATE_MESSAGES_STRING = os.environ["PHATE_PHATE_MESSAGES"]
PHATE_WARNINGS_STRING = os.environ["PHATE_PHATE_WARNINGS"]

if PHATE_PROGRESS_STRING.lower() == 'true':
    PHATE_PROGRESS = True
if PHATE_MESSAGES_STRING.lower() == 'true':
    PHATE_MESSAGES = True
if PHATE_WARNINGS_STRING.lower() == 'true':
    PHATE_WARNINGS = True

#DEBUG = True
DEBUG = False

##### Import modules

import sys
import re
import string
import copy
from subprocess import call
import CGC_geneCall
import CGC_compare
import datetime

##### FILES

CODE_BASE = "CGC_main"
CODE_FILE = CODE_BASE + ".py"
LOG_FILE  = CODE_BASE + ".log"  # log file
OUT_FILE  = CODE_BASE + ".out"  # ??? other output?
CGC_FILE  = CODE_BASE + ".gff"  # CGC summary file - list of total gene calls in gff format

infile = ""
#LOG_H = open(LOG_FILE,"w")
#OUT_H = open(OUT_FILE,"w")
#CGC_H = open(CGC_FILE,"w")  # CGC summary file - list of total gene calls in gff format

# Output files for CGC processing
SUPERSET_FILE   = ""
CONSENSUS_FILE  = ""
COMMONCORE_FILE = ""
SUPERSET_H      = "" # file handles
CONSENSUS_H     = ""
COMMONCORE_H    = ""

##### PATTERNS

p_comment    = re.compile('^#')
p_order      = re.compile('Order')
p_log        = re.compile("log=([\w\d\_\-\.\\\/]+)")
p_cgc        = re.compile("cgc=([\w\d\_\-\.\\\/]+)")
p_superset   = re.compile("superset=([\w\d\_\-\.\\\/]+)")
p_consensus  = re.compile("consensus=([\w\d\_\-\.\\\/]+)")
p_commoncore = re.compile("commoncore=([\w\d\_\-\.\\\/]+)")

##### CONSTANTS

HELP_STRING = "This code inputs a list of at least 2 files comprising gene calls (generated by a gene caller program) and outputs the genes that are in common and unique with respect to each caller.  Type: python " + CODE_FILE + " usage|input|detail for more information\n"

USAGE_STRING = "Usage:  python " + CODE_FILE + " <infile>n\n"

INPUT_STRING = "Input for " + CODE_FILE + " comprises a list of path/filenames comprising outputs generated by gene caller programs, with each separated by a single space. The output files are to have been prepared using code \"CGC_parser.py\" to assure that they have a common pre-defined format and indicate the name of the gene caller in the comments section.\nExample:  python " + CODE_FILE + " genemark.calls prodigal.calls\n"

INFO_STRING = "This code currently supports the following gene callers:  GeneMark, Glimmer, Prodigal, RAST, and PHANOTATE. For more information regarding input to " + CODE_FILE + ", type:  " + CODE_FILE + " input"

##### GET INPUT PARAMETERS

fileSet = []
argCount = len(sys.argv)

if argCount > 1:
    # First param is log=<logFile>, 2nd is gff=<gffFile>, 3rd is super=<supersetFile>, 4th is consensus=<consensusFile>
    # remaining params are genecall files to compare
    if PHATE_PIPELINE:
        #LOG_H.close()  # close default log; open log in designated subdir
        #CGC_H.close()  # close default cgc out file; open cgc out file in designated subdir
        if argCount > 5:
            match_log        = re.search(p_log,        sys.argv[1])
            match_cgc        = re.search(p_cgc,        sys.argv[2])
            match_superset   = re.search(p_superset,   sys.argv[3])
            match_consensus  = re.search(p_consensus,  sys.argv[4])
            match_commoncore = re.search(p_commoncore, sys.argv[5])
            if match_log:
                LOG_FILE = match_log.group(1)  # override as named above
                LOG_H    = open(LOG_FILE,"w")
                LOG_H.write("%s%s\n" % ("Opening log at ",datetime.datetime.now()))
            else:
                print("CGC_main says, ERROR: Expecting name of log file as first input parameter. Parameter was:", sys.argv[1])
            if match_cgc:
                CGC_FILE        = match_cgc.group(1)        # override as named above
                CGC_H           = open(CGC_FILE,"w")
            if match_superset:
                SUPERSET_FILE   = match_superset.group(1)      # override as named above
                SUPERSET_H      = open(SUPERSET_FILE,"w")
            if match_consensus:
                CONSENSUS_FILE  = match_consensus.group(1)  # override as named above
                CONSENSUS_H     = open(CONSENSUS_FILE,"w")
            if match_commoncore:
                COMMONCORE_FILE = match_commoncore.group(1)  # override as named above
                COMMONCORE_H    = open(COMMONCORE_FILE,"w")

            fileSet = sys.argv[6:]  # collect remaining command-line arguments
        else:
            print("CGC_main says, ERROR: Insufficient arguments provided")

    else:  # "Help" input parameters should only be encountered if running code independently at command line
        match = re.search("help", sys.argv[1].lower())  
        if match:
            print(HELP_STRING)
            LOG_H.close(); exit(0)

        match = re.search("input", sys.argv[1].lower())
        if match:
            print(INPUT_STRING)
            LOG_H.close(); exit(0)

        match = re.search("usage", sys.argv[1].lower())
        if match:
            print(USAGE_STRING)
            LOG_H.close(); exit(0)

        match = re.search("detail", sys.argv[1].lower())
        if match:
            print(INFO_STRING)
            LOG_H.close(); exit(0)

        match = re.search("info", sys.argv[1].lower())
        if match:
            print(INFO_STRING)
            LOG_H.close(); exit(0)
        else:
            fileSet = sys.argv[1:]  # skip 0th element = name of code

else:
    LOG_H.write("%s\n" % ("Incorrect number of command-line arguments provided"))
    print(USAGE_STRING)
    LOG_H.close()
    exit(0)

##### BEGIN MAIN ################################################################################### 

count = 0
callerList = []
callSet_obj = CGC_geneCall.GeneCallSet()

####################################################################################################
# For each user-provided gene call file, create a call set and add to list of call sets

if PHATE_PROGRESS:
    print("CGC_main says, Iterating through fileSet...")

if PHATE_PIPELINE:
    LOG_H.write("%s%s\n" % ("Iterating through fileSet at ",datetime.datetime.now()))
    LOG_H.write("%s%s\n" % ("fileSet is ",fileSet))

for geneFile in fileSet:
    # First, create a call set
    callSet = copy.deepcopy(callSet_obj)

    LOG_H.write("%s%s\n" % ("Opening geneFile ",geneFile))
    if PHATE_MESSAGES:
        print("CGC_main says, Opening geneFile ",geneFile)
    geneFile_handle = open(geneFile,"r")

    LOG_H.write("%s%s\n" % ("Adding calls from geneFile ",geneFile))
    if PHATE_MESSAGES:
        print("CGC_main says, Adding calls from file", geneFile)
    callSet.AddGeneCalls(geneFile_handle) 
    geneFile_handle.close()

    LOG_H.write("%s%s\n" % ("Appending call set  number of calls is: ", len(callSet.geneCallList)))
    callerList.append(callSet) 

    if PHATE_MESSAGES:
        print("CGC_main says, Number of gene calls in current gene call set:", len(callSet.geneCallList))

# Communicate
LOG_H.write("%s%s\n" % ("All call sets have been added to caller list. Number of call sets in callerList: ", len(callerList)))
callerString = ""; callers = "" 
for callSet in callerList:
    currentCaller = callSet.geneCaller + ' '
    callers += currentCaller 
LOG_H.write("%s%s\n" % ("callerList is ",callers))
totalCalls = 0
for callSet in callerList:
    totalCalls += len(callSet.geneCallList)
LOG_H.write("%s%s\n" % ("Total number of gene calls across callerList call sets is: ", totalCalls))
if PHATE_MESSAGES:
    print("CGC_main says, callerList is:", end=' ') 
    for callSet in callerList:
        callSet.PrintAll_brief() 

####################################################################################################
# Sort calls in each list

LOG_H.write("%s\n" % ("Sorting gene calls for each caller"))
if PHATE_PROGRESS:
    print("CGC_main says, Sorting gene calls for each caller...")

# Sort calls for each caller
for callSet in callerList:
    LOG_H.write("%s\n" % ("Processing a callSet"))
    LOG_H.write("%s%s%s%s\n" % ("Before sorting, Length of callerList for caller ", callSet.geneCaller, " is ", len(callSet.geneCallList)))
    callSet.SortGeneCalls()
    LOG_H.write("%s%s%s%s\n" % ("After sorting, Length of callerList for caller ", callSet.geneCaller, " is ", len(callSet.geneCallList)))
LOG_H.write("%s\n" % ("callSet processing complete"))

####################################################################################################
# Begin process to compare across the call sets

LOG_H.write("%s\n" % ("Comparing across the call sets..."))
if PHATE_PROGRESS:
    print("CGC_main says, Comparing accross the call sets....")
# Create comparison object
compareGCs = CGC_compare.Comparison()

####################################################################################################
# Merge the call sets

LOG_H.write("%s\n" % ("Merging the geneCall sets...."))
if PHATE_PROGRESS:
    print("CGC_main says, Merging the gene call sets....")
for callSet in callerList:
    compareGCs.Merge(callSet.geneCallList)  # Merge() merges one at a time, adding each gene call list the the existing merge

LOG_H.write("%s\n" % ("Final merged genes:"))
compareGCs.PrintMergeList2file(LOG_H)

####################################################################################################
# Compare the merged calls

LOG_H.write("%s\n" % ("Comparing across geneCall sets...."))
if PHATE_PROGRESS:
    print("CGC_main says, Comparing across gene call sets....")

# Fist, identify unique gene calls
compareGCs.Compare()

# Next, score the gene calls
LOG_H.write("%s\n" % ("Scoring gene calls...."))
if PHATE_PROGRESS:
    print("CGC_main says, Scoring gene calls....")
compareGCs.Score()

# Then, identify gene calls in common
LOG_H.write("%s\n" % ("Identifying common core..."))
if PHATE_PROGRESS:
    print("CGC_main says, Identifying gene calls in common...")
compareGCs.IdentifyCommonCore()
LOG_H.write("%s\n" % ("This is the Common Core List:"))
compareGCs.PrintCommonCore2file(LOG_H)

####################################################################################################
# Print GFF output file and final report 

# Print GFF
LOG_H.write("%s\n" % ("Printing gene-call superset, consensus, and common_core in GFF and CGC formats"))
if PHATE_PROGRESS:
    print("CGC_main says, printing GFF formatted gene-call file....")

#compareGCs.PrintGenecalls2file_gff(GFF,"superset")
compareGCs.PrintGenecalls2file_cgc(SUPERSET_H,"superset")
compareGCs.PrintGenecalls2file_cgc(CONSENSUS_H,"consensus")
compareGCs.PrintGenecalls2file_cgc(COMMONCORE_H,"common_core")

LOG_H.write("%s\n" % ("Printing report...."))
if PHATE_PROGRESS:
    print("CGC_main says, printing report....")
compareGCs.PrintReport2file(LOG_H)
compareGCs.PrintReport()
compareGCs.PrintUniqueList2file(LOG_H)

##### CLEAN UP #####

if PHATE_PROGRESS:
    print("CGC_main says, Processing complete.")
LOG_H.write("%s%s\n" % ("Code complete at ",datetime.datetime.now()))
LOG_H.close()
