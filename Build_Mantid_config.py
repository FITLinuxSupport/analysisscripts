#!/usr/bin/python
import json
#import libuser
import urllib
import os
import shutil
import smtplib
import socket
import sys
import collections
import platform
import stat
try:
    import grp
    WinDebug=False
except:
    WinDebug = True

from email.mime.text import MIMEText

from pprint import pprint
from distutils.dir_util import mkpath

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
#

#sysadmin_email = "stephen.rankin@stfc.ac.uk,warren.jeffs@stfc.ac.uk,leon.nell@stfc.ac.uk"
sysadmin_email = ["warren.jeffs@stfc.ac.uk", "leon.nell@stfc.ac.uk", "darren.gilbert@stfc.ac.uk"]

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
#
def check_or_create_rb_link(fedid,rbdir,rbnumber,create_group=True):
    """Function checks if  link to RB folder exist for the user
       and if not creates one"""

    #os.system("chown -R " + fedid + "." + fedid + " " + "/home/"+fedid)
    # Add user to the appropriate group
    if create_group:
        os.system("/usr/sbin/usermod -a -G " + rbnumber + " " + fedid)
    # Create link to appropriate RB folder.
    if os.path.exists("/home/" + fedid + "/" + rbnumber):
        print "Link exists: " + "/home/" + fedid + "/" + rbnumber
        link_created = False
    else:
        os.symlink(rbdir, "/home/" + fedid + "/" + rbnumber) 
        link_created = True
    return link_created


def test_path(path):
    if os.path.exists(path):
        print "Path OK " + path
    else:
        send_error(path,1,1)
#-------------------------------------------------------------
# Server specific part with hard-coded path-es
#-------------------------------------------------------------
if platform.system() == 'Windows':
    sys.path.insert(0,'c:/Mantid/Code/Mantid/scripts/Inelastic/Direct')
    WinDebug=True
else:
    sys.path.insert(0,'/opt/mantidnightly/scripts/Inelastic/Direct/')
    #sys.path.insert(0,'/opt/Mantid/scripts/Inelastic/Direct/')
    WinDebug=False

try:
    from ISISDirecInelasticConfig import MantidConfigDirectInelastic,UserProperties
    buildISISDirectConfig=True
except:
    buildISISDirectConfig=False

#
#-------------------------------------------------------------
# Path needed on server for this script to work
#-------------------------------------------------------------
if WinDebug:
    base = 'd:/Data/Mantid_Testing/config_script_test_folder'
    rootDir = os.path.join(base,'users')
    analysisDir= base
else:
    rootDir = "/home/"
    test_path(rootDir)
    analysisDir = "/instrument/"
    test_path(analysisDir)

# On analysis machines:
MantidDir = '/opt/Mantid'
MapMaskDir = '/usr/local/mprogs/InstrumentFiles/'
UserScriptRepoDir = '/opt/UserScripts'

#Win Debug
if WinDebug:
    MantidDir = r"c:\Mantid\Code\builds\br_master\bin\Release"
    UserScriptRepoDir = os.path.join(analysisDir,"UserScripts")
    MapMaskDir =  os.path.join(analysisDir,"InstrumentFiles")
else:
    home = '/home'




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
#urllib.urlretrieve("http://fitlnxdeploy.isis.cclrc.ac.uk/excitations.txt",ExpDescriptorsFile+'.old')
test_path(ExpDescriptorsFile)

#Open the data
json_data = open(ExpDescriptorsFile)
data = json.load(json_data)

#Open smb.conf so we can add RB number directory exports to it
if not WinDebug:
    test_path("/etc/samba/smb.conf")
    os.system("cp -f /etc/samba/smb.tmpl /etc/samba/smb.conf")
    smb = open('/etc/samba/smb.conf', 'a')
if buildISISDirectConfig:
    try:
        mcf = MantidConfigDirectInelastic(MantidDir,rootDir,UserScriptRepoDir,MapMaskDir)
    except RuntimeError as er:
        send_error(er.message,2,1)
        buildISISDirectConfig=False
        #raise RuntimeError(" Server does not have appropriate folders for DirectInelastic reduction. Can not continue")


user_list = {}
user_verified_list = []
users_rejected_list = []




#print len(data["experiments"])
for experiment in data["experiments"]:

    #RB number for the experiment
    nrbnumber  = experiment["RbNumber"]
    rbnumber = "RB" + nrbnumber

    #Experiment start date
    date = experiment["StartDate"]

    #Instrument name
    instrument = experiment["Instrument"]

    #Cycle number
    cycle = experiment["Cycle"]
    cycle = cycle.upper()
    cycle = "CYCLE" + cycle.replace('/', '')

    #  print rbnumber
    #  print date
    #  print instrument
    #  print cycle

    if not WinDebug:
        try:
            group_descriptor = grp.getgrgid(nrbnumber)
            # we assume that if group already exist, all folders below exist
            group_members = group_descriptor[3]
        except KeyError:
            #Make new empty group
            os.system("/usr/sbin/groupmod -o " "-g " +nrbnumber+ " " +rbnumber)
            os.system("/usr/sbin/groupadd -o " "-g " +nrbnumber+ " " +rbnumber)
            group_members=[]
        cyclerbdir = os.path.join(analysisDir,instrument.upper(),cycle, rbnumber)
        rbdir = os.path.join(analysisDir,instrument.upper(),"RBNumber",rbnumber)
        cycledir = os.path.join(analysisDir,instrument.upper(),cycle)
        #so should be analysisdir/instrumentname/RBNumber/rbnumber

        #Make the paths to the analysis RB directories.

        mkpath(rbdir)
        test_path(rbdir)

        #Change permissions on the RB directories.
        os.system("chgrp " + rbnumber + " " + rbdir)
        os.system("chmod 2770 " + rbdir)

        #make cycle folder
        if os.path.exists(cycledir):
            print "Path OK: " +cycledir+ "\n"
        else:
            mkpath(cycledir)


        #make symb links from cycle -> individual RBs
        if os.path.exists(cyclerbdir):
            print "Link exists: " +cyclerbdir+ "\n"
        else:
            os.symlink(rbdir, cyclerbdir +rbnumber) 
        
        
        
        # Make SAMBA share available to group members.
        # Make the string to append to the smb.conf file:
        SAMBARB = "        " + "[" + rbnumber + "]" + "\n"
        SAMBARB = SAMBARB + "        " + "comment = " + rbnumber + "\n"
        SAMBARB = SAMBARB + "        " + "path = " + rbdir + "\n"
        SAMBARB = SAMBARB + "        " + "writable = yes" + "\n"
        SAMBARB = SAMBARB + "        " + "printable = no" + "\n"
        SAMBARB = SAMBARB + "        " + "write list = +" + rbnumber + "\n"
        SAMBARB = SAMBARB + "        " + "force group = " + rbnumber + "\n"
        SAMBARB = SAMBARB + "        " + "valid users = +" + rbnumber + "\n"
        SAMBARB = SAMBARB + "        " + "create mask = 2660" + "\n"
        SAMBARB = SAMBARB + "        " + "directory mask = 2770" + "\n" + "\n"
        # Append the string to the smb.conf file:
        smb.write(SAMBARB)

    participents = experiment["Permissions"]
    for participent in participents:
        email = participent["email"]
        fedid = participent["fedid"]

        if fedid in users_rejected_list:
            continue

        if WinDebug:
            # Create user for testing purpose. In real life it is created
            # somewhere else.
            user_folder = os.path.join(rootDir,str(fedid))
            mkpath(user_folder)
            # for testing purposes we will create rb folders within users folder
            # and would not deal with linking these folders
            rbdir = os.path.join(user_folder,rbnumber)
            mkpath(rbdir)
            old_link_exist = False
        else:
            if not fedid in user_verified_list:
                if os.system("su -l -c 'exit' " + fedid) != 0:
                    user_error=fedid + " User cannot be found - account is either disabled or does not exist."
                    users_rejected_list.append(fedid)
                    send_error(user_error,3,0)
                    continue
                else:
                   user_verified_list.append(fedid)
            print fedid + " OK"
            # Check if person is already in this group
            if fedid in group_members:
                add_to_group = False
            else:
                add_to_group = True
            #
            if os.path.exists("/home/"+fedid):
                old_link_exist=check_or_create_rb_link(fedid,rbdir,rbnumber,add_to_group)
            else:
                # Create user's folder
                mkpath(home + "/" + fedid)
                test_path(home  + "/" + fedid)
                os.system("chown -R " + fedid + "." + fedid + " " + home +"/"+fedid,add_to_group)
                #--------------
                old_link_exist=check_or_create_rb_link(fedid,rbdir,rbnumber)
        if old_link_exist:
            continue
        if not buildISISDirectConfig:
            continue
        # Define Direct inelastic User
        if mcf.is_inelastic(instrument):
            if not fedid in user_list:
                user_list[str(fedid)] = UserProperties(str(fedid))
            current_user = user_list[fedid]
            # Define user's properties, e.g. cycle, instrument, start data 
            # and rb folder. If more then one record per user, the latest will be active
            rb_user_folder = os.path.join(mcf._home_path,str(fedid),str(rbnumber))
            # rb folder must be present!
            current_user.set_user_properties(str(instrument),str(date),str(cycle),rb_user_folder)
        #end if
json_data.close()
if not WinDebug:
    smb.close()


# Usually user's configuration file is not overwritten if its modification date is late then
# user start date. Set below to True if you want to force overwriting configurations
#mcf._force_change_config = True
# replace users sample script. Should be used only if bugs are identified in the previous sample script.
#mcf._force_change_script = True
if buildISISDirectConfig:
    # Generate Mantid configurations for all users who does not yet have their own
    for user_prop in user_list.itervalues():
        try:
            mcf.init_user(user_prop)
            mcf.generate_config()
        except RuntimeError as er:
            send_error(er.message,2,1)


