#!/usr/bin/python
###############################################################################
# Kolton Benoit
# Started 20 November 2017
# Last updated 23 March 2017
#------------------------------------------------------------------------------
# Script for checking status of flexlm license server and for returning its 
# output in json or nagios format
#
# The script is basically a fancy wrapper for the lmutil program
#------------------------------------------------------------------------------
# Uses the LMutil tool to check a FlexLM server for its license status
# LMutil must be installed to your system
# Our flexlm server is used for autodesk products. I got a copy of the .rpm 
# from: https://knowledge.autodesk.com/support/maya/downloads/caas/downloads/content/autodesk-network-license-manager-for-linux.html
##############################################################################
# Known issues
##############################################################################
# On centos, the program will probably crash and complain about 
# "bad ELF interpreter", which is fixed by installing the "redhat-lsb" package
#
# Note that I've only tested this with a single vendor license 
# (autodesk autocad) and only ran the script from centos. I have no idea if
# other configurations will work or not
###############################################################################
# Security concerns
###############################################################################
# As far as I can tell, there is no security for flexlm and lmutil.
# 
# This means that if a user has legitimate access to the ports needed for 
# normal use of the license server, there is nothing that stops them from 
# downloading a copy of lmutil and finding this data on their own
#
# This script is basically a fancy wrapper for the lmutil program
#
###############################################################################
###############################################################################
# Command Line Usage
###############################################################################
# Arguments available:
#    -l, --lmools (optional)
#        The path to the lmutil program
#    -s, --server (required)
#        The IP address or FQDN of the server hosting the license server
#    -p, --port (required)
#        The port the license server daemon is listening to
#    -j, --json (optional)
#        Output the information in JSON format. Not intended for use with
#        nagios. See the Other Usage section below
#
# ex: ./check_flexlm.py -l /path/to/lmutil \
#                       --server LMSERVER.example.com \
#                       -p 27000 \
###############################################################################
# Nagios Usage 
###############################################################################
# Sample Nagios command:
# define command{
#     command_name  check_flexlmpy
#     command_line  $USER1$/check_flexlm.py -l /path/to/lmutil -s $HOSTADDRESS$ $ARG1$
# }
#
# Sample Nagios service:
# define service{
#     use                   generic-service
#     host_name             HOST
#     service_description   FlexLM
#     check_command         check_flexlm.py! -p 27000
#}
###############################################################################
# Other Usage
###############################################################################
# Ever notice that when autocad can't get a license it gives the user the 
# _ever_ so helpful message of "Network License Not Available; Common causes:
# all licenses are in use, the server is down, or the license has expired"?
# Ever had users ask you _constantly_ if the server is down? This extra feature
# might help.
#
# Call the script as you would before, but with the -j switch:
# ./check_flexlm.py -l /path/to/lmutil \
#                   --server LMSERVER.example.com \
#                   -p 27000 \
#                   -j
#
# This outputs the server status in JSON format, given in the following
# structure as defined in Typescript:
# export class AutoCADStatus {
#    statusText: string;
#    updated: string;
#    ok: boolean;
#    usage: Array<{
#        license: string;
#        max: number;
#        used: number;
#    }>;
#    details: Array<{
#        license: string;
#        expires: string;
#        details: Array<{
#            username: string;
#            start: string;
#            workstation: string;
#        }>;
#    }>;
#}
#
# Call the script on the server side and return the json to the front end for 
# formatting: you've built a user friendly frontend for the commandline lmutil
###############################################################################

import sys, subprocess, argparse, re, json, datetime

#######################################
# Argument Parsing
#######################################
#Required: LMtools, Port, Server.
parser = argparse.ArgumentParser(description="Check FlexLM server script.")
parser.add_argument("-l", "--lmutil", required=True, help="The path to the LMutil utility.")
parser.add_argument("-s", "--server", required=True, help="The FlexLM server IP or FQDN.")
parser.add_argument("-p", "--port", required=True, help="The FlexLM port.")
parser.add_argument("-j", "--json", action="store_true", default=False, dest="j",
					help="Return output in JSON. Not intended for use with Nagios.")
args = parser.parse_args()

#######################################
# Call lmutil
#######################################
#Build command with arguments
command = [
	args.lmtools,
	"lmstat",
	"-a",
	"-c",
	"{0}@{1}".format(args.port, args.server)
]

#Call lmutil
proc = subprocess.Popen(command,stdout=subprocess.PIPE)
proc.wait()
output = proc.stdout.read()

#######################################
#Parse returned data for server status
#######################################
#Regex strings
licenseServerR = r"(\S*): license server (.*) .* (v(\d*\.?)*)"
vendorDaemonR = r"Vendor daemon status \(on .*\):\n\n\s*(.*): (.*) (v(\d*\.?)*)"
licenseUsageR = r"Users of (\S*):  \([\D]*(\d*)[\D]*(\d) "
licenseDetailsR = r"\"(\S*)\".* vendor: (.*), expiry: (.*)\s*floating license\s* ((?:\S* \S*.*[a-zA-Z]{3} \d*\/\d* \d*:\d*\s*)*)"
userDetailsR = r"(\S*) (\S*).*([a-zA-Z]{3} \d*\/\d* \d*:\d*)\s*"

#Regex objects
licenseServerRegex = re.compile(licenseServerR)
vendorDaemonRegex = re.compile(vendorDaemonR)
licenseUsageRegex = re.compile(licenseUsageR)
licenseDetailsRegex = re.compile(licenseDetailsR)
userDetailsRegex = re.compile(userDetailsR)

#Search the output
licenseServer = licenseServerRegex.search(output)
vendorDaemon = vendorDaemonRegex.search(output)
licenseUsage = licenseUsageRegex.findall(output)
licenseDetails = licenseDetailsRegex.findall(output)

outputDict = {}

#If the server and the first vendor daemon is up, all is well
try:
	#Check the state of the license server
	if licenseServer.group(2).upper() == "UP":
		ls = True
	else:
		ls = False
	#Check the state of the vendor Daemon
	if vendorDaemon.group(2).upper() == "UP":
		vd = True
	else:
		vd = False
	
	#If both the license server and vendor daemon are up, all is well
	if ls and vd:
		#print("FlexLM OK: License Server and Vendor Daemon are UP.")
		outputDict["statusText"] = "FlexLM OK: License Server and Vendor Daemon are UP."
		outputDict["ok"] = True

		#If license information was returned and found by regex
		if(licenseUsage):
			license = []
			#loop through the output, Add the license's with a usage above 0 to
			#    the output dictionary
			for lu in licenseUsage:
				if int(lu[2]) > 0:
					temp = {}
					temp["license"] = lu[0]
					temp["used"] = lu[2]
					temp["max"] = lu[1]
					license.append(temp)
			outputDict["usage"] = license

		#If details for license information was returned and found by regex
		if(licenseDetails):
			temp = []
			for details in licenseDetails:
				temp2 = {}
				temp2["license"] = details[0]
				temp2["expires"] = details[2]
				temp2["details"] = []
				for user in userDetailsRegex.findall(details[3]):
					temp3 = {}
					temp3["username"] = user[0]
					temp3["workstation"] = user[1]
					temp3["start"] = user[2]
					temp2["details"].append(temp3)
				temp.append(temp2)
			outputDict["details"] = temp
	#Else, report that the server is down, if it isn't up.
	elif not ls:
		outputDict["statusText"] = "FlexLM CRIT: License Server is DOWN"
		outputDict["ok"] = False
	#Else, report that the vendor daemon is down
	else:
		outputDict["statusText"] = "FlexLM CRIT: Vendor Daemon is DOWN"
		outputDict["ok"] = False
	
except Exception as e:
	#check if the lmutil failed to connect to the port
	if "Cannot connect to license server system." in output:
		outputDict["statusText"] = "FlexLM CRIT: LMutil was unable to connect to the port."
		outputDict["ok"] = False
	elif "License server machine is down or not responding." in output:
		outputDict["statusText"] = "FlexLM CRIT: LMutil was unable to connect to the server."
		outputDict["ok"] = False
	else:
		outputDict["statusText"] = "FlexLM UNKNOWN: Unknown error. \n Error: {0} \nRaw lmutil output:{1}\n".format(e, output)
		outputDict["ok"] = False

outputDict["updated"] = str(datetime.datetime.now().strftime("%d %B %Y, %H:%M:%S "))

#Print the json if requested
if args.j:
	print(json.dumps(outputDict))
#Else, print it in a format nagios likes
else: 
	print(outputDict["statusText"])
	for usage in outputDict["usage"]:
		print("{0}: {1} of {2}".format(usage["license"], usage["used"], usage["max"]))