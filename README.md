# check_flexlm.py

Script for checking status of flexlm license server and for returning its 
output in json or nagios format

Uses the LMutil tool to check a FlexLM server for its license status
LMutil must be installed to your system
Our flexlm server is used for autodesk products. I got a copy of the .rpm 
from [autodesk](https://knowledge.autodesk.com/support/maya/downloads/caas/downloads/content/autodesk-network-license-manager-for-linux.html)

# Known issues
On centos, the program will probably crash and complain about 
"bad ELF interpreter", which is fixed by installing the "redhat-lsb" package

Note that I've only tested this with a single vendor license 
(autodesk autocad) and only ran the script from centos. I have no idea if
other configurations will work or not

# Security concerns
As far as I can tell, there is no security for flexlm and lmutil.

This means that if a user has legitimate access to the ports needed for 
normal use of the license server, there is nothing that stops them from 
downloading a copy of lmutil and finding this data on their own

This script is basically a fancy wrapper for the lmutil program

# Command Line Usage
### Arguments available:
```
-l, --lmutil (required)
    The path to the lmutil program
-s, --server (required)
    The IP address or FQDN of the server hosting the license server
-p, --port (required)
    The port the license server daemon is listening to
-j, --json (optional)
    Output the information in JSON format. Not intended for use with
    nagios. See the Other Usage section below
```
#### ex:
```shell
./check_flexlm.py -l /path/to/lmutil \
                  --server LMSERVER.example.com \
                  -p 27000 \
```

# Nagios Usage

Sample Nagios command:
```
define command{
    command_name  check_flexlmpy
    command_line  $USER1$/check_flexlm.py -l /path/to/lmutil -s $HOSTADDRESS$ $ARG1$
}
```

Sample Nagios service:
```
define service{
    use                   generic-service
    host_name             HOST
    service_description   FlexLM
    check_command         check_flexlm.py! -p 27000
}
```

# Other Usage

Ever notice that when autocad can't get a license, it gives the user the 
_ever_ so helpful message:
>"Network License Not Available
> Common causes: all licenses are in use, the server is down, or the license 
>has expired"
Ever had users ask you _constantly_ if the server is down? This extra
feature might help.

Call the script as you would before, but with the -j switch:

```shell
./check_flexlm.py -l /path/to/lmutil \
                  --server LMSERVER.example.com \
                  -p 27000 \
                  -j
```

This outputs the server status in JSON format, given in the following
structure as defined in Typescript:

```typescript
export class AutoCADStatus {
    statusText: string;
    updated: string;
    ok: boolean;
    usage: Array<{
        license: string;
        max: number;
        used: number;
    }>;
    details: Array<{
        license: string;
        expires: string;
        details: Array<{
            username: string;
            start: string;
            workstation: string;
        }>;
    }>;
}
```

Call the script on the server side and return the json to the front end for 
formatting: you've built a user friendly frontend for the commandline lmutil
