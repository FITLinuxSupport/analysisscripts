import urllib
import json
#import libuser
import os
import shutil
import smtplib
import socket
import sys
import collections
import platform
import stat
import copy
try:
    import grp
    WinDebug=False
except:
    WinDebug = True

from email.mime.text import MIMEText

from pprint import pprint
from distutils.dir_util import mkpath



def copy_and_overwrite(from_path, to_path):
    if os.path.exists(to_path):
        shutil.rmtree(to_path)
    shutil.copytree(from_path, to_path)

def getUidByUname(uname):
    return os.popen("id -u %s" % uname).read().strip()

def send_alert_email(from_address,to_address, subject, message):
    # The maile SMTP server used to send mail
    smtp_server = 'exchsmtp.stfc.ac.uk'

    # A text/plain message as a test
    msg = MIMEText(message)

    # from_address == the sender's email address
    # to_address == the recipient's email address
    msg['Subject'] = subject
    msg['From'] = from_address
    msg['To'] =  ', '.join(to_address)

    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    s = smtplib.SMTP(smtp_server)
    s.sendmail(from_address, to_address, msg.as_string())
    s.quit()

#sysadmin_email = "stephen.rankin@stfc.ac.uk,warren.jeffs@stfc.ac.uk,leon.nell@stfc.ac.uk"
sysadmin_email = ["warren.jeffs@stfc.ac.uk", "leon.nell@stfc.ac.uk"]

def send_error(MessBody=None,ErrorCode=0,ExitScript=0):
    if ErrorCode == 1:
        sub = 'CRITICAL ' + MessBody + " missing."
        msg = 'CRITICAL ERROR ' + MessBody + " missing. Cannot continue to make directories on "
        msg = msg + socket.gethostname() + " aborting script"       
    elif ErrorCode == 2:
        sub = 'CRITICAL ' + MessBody + " Mantid init missing."
        msg = 'CRITICAL ERROR ' + MessBody + " while building Mantid configuration. Cannot continue to set up Mantid"
    elif ErrorCode == 3:
        sub = 'CRITICAL ' + MessBody
        msg = 'CRITICAL ERROR ' + MessBody + " please could the user's account be added and/or made active."
    elif ErrorCode == 4:
        sub = 'CRITICAL ' + MessBody
        msg = 'CRITICAL ERROR ' + MessBody
    else:
        sub = 'CRITICAL ' + MessBody
        msg = 'CRITICAL ERROR ' + MessBody + " unknown error."

    send_alert_email('root@' + socket.gethostname(),sysadmin_email,sub, msg)

    if ErrorCode == 1:
        sys.exit()

  
def test_path(path):
    if os.path.exists(path):
        print "Path OK " + path
    else:
        send_error(path,1,1)


#-------------------------------------------------------------
# Path needed on server for this script to work
#-------------------------------------------------------------
if WinDebug:
    rootDir = r"d:\users\abuts\Documenst/"
    analysisDir= r'd:\users\abuts\SVN\Mantid\Mantid_testing/'
else:
    rootDir = "/home/"
    test_path(rootDir)
    analysisDir = "/instrument/"
    test_path(analysisDir)

# On Rutherford:
MantidDir = '/opt/Mantid'
#UserScriptRepoDir = '/usr/local/mprogs/User/Mantid_ScriptRepository'
MapMaskDir = '/usr/local/mprogs/InstrumentFiles/'
#MapMaskDir = '/usr/local/mprogs/InstrumentFiles/'
UserScriptRepoDir = '/opt/UserScripts'

#Win Debug
if WinDebug:
    MantidDir = "c:/mprogs/MantidInstall"
    UserScriptRepoDir = r"D:\users\abuts\SVN\Mantid\scriptrepository_mantid/"
    MapMaskDir =  r'D:\users\abuts\SVN\ISIS\InstrumentFiles_svn/'
    Paraview = r"c:\Programming\Paraview_Installed"

#admin = libuser.admin()

#list = admin.enumerateUsers("*sfp76")
#list.sort()
#for item in list:
#   print "Found a user named \"" + item + "\"."

# Get the output from the user office data which is published
# as a web page in JSON

# Setup web proxy
proxies = {'http': 'http://wwwcache.rl.ac.uk:8080'}
opener = urllib.FancyURLopener(proxies)

if WinDebug:
    ExpDescriptorsFile = "c:/temp/excitations.txt"
else:
    ExpDescriptorsFile = "/tmp/excitations.txt"

# Get the user office data.
urllib.urlretrieve("http://icatingest.isis.cclrc.ac.uk/excitations.txt",ExpDescriptorsFile)
test_path(ExpDescriptorsFile)

#Open the data
json_data = open(ExpDescriptorsFile)
data = json.load(json_data)


for experiment in range(len(data["experiments"])):

    #RB number for the experiment
    nrbnumber = data["experiments"][experiment]["RbNumber"]
    rbnumber = "RB" + nrbnumber

    #Experiment start date
    date = data["experiments"][experiment]["StartDate"]

    #Instrument name
    instrument = data["experiments"][experiment]["Instrument"]
    instrument = instrument

    #Cycle number
    cycle = data["experiments"][experiment]["Cycle"]
    cycle = cycle.upper()
    cycle = "CYCLE" + cycle.replace('/', '')

    #  print rbnumber
    #  print date
    #  print instrument
    #  print cycle


    if WinDebug:
        rbdir = r'd:\users\abuts\SVN\Mantid\Mantid_testing\tt'
        cycle_dir1 = r'd:\users\abuts\SVN\Mantid\Mantid_testing'
    else:
        try:
            group_descriptor = grp.getgrgid(nrbnumber)
            # we assume that if group already exist, all folders below exist
            group_members = group_descriptor[3]
            # let's check if autoreduction is already a member
            # as the script below worked appropriately before
            if 'isisautoreduce' in group_members:
                continue
        except KeyError:
            #Make a group
            os.system("/usr/sbin/groupmod -o " "-g " +nrbnumber+ " " +rbnumber)
            os.system("/usr/sbin/groupadd -o " "-g " +nrbnumber+ " " +rbnumber)
        rbdir = analysisDir + instrument.upper() + "/" + cycle + "/" + rbnumber

        #Make the paths to the analysis RB directories.
        cycle_dir1 = analysisDir + instrument
    cycle_dir2 = cycle_dir1 + "/" + cycle
    #
    mkpath(cycle_dir1)
    test_path(cycle_dir1)
    mkpath(cycle_dir2)
    test_path(cycle_dir2)

    mkpath(rbdir)
    test_path(rbdir)
    if WinDebug:
        continue
    #Change permissions on the RB directories.
    os.system("chgrp " + rbnumber + " " + rbdir)
    os.system("chmod 2770 " + rbdir)

    os.system("/usr/sbin/usermod -a -G " + rbnumber + " isisautoreduce")

json_data.close()
