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
except:
    pass # its probably windows

from email.mime.text import MIMEText

from pprint import pprint
from distutils.dir_util import mkpath


sysadmin_email = ["warren.jeffs@stfc.ac.uk"]

#--------------------------------------------------------------------
#  Routines definitions:
#--------------------------------------------------------------------

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
        print( "Path OK " + path)
    else:
        print( "Fatal error in path: ",path)
        send_error(path,1,1)
#

#--------------------------------------------------------------------
# Server specific part with hard-coded path-es used in configuration
#--------------------------------------------------------------------
if platform.system() == 'Windows':
    sys.path.insert(0,'c:/Mantid/scripts/Inelastic/Direct')
    base = r'd:\Data\Mantid_Testing\config_script_test_folder'
    analysisDir= os.path.join(base,"instrument")

    MantidDir = r"c:\Mantid\_builds\br_master\bin\Release"
    UserScriptRepoDir = os.path.join(base,"UserScripts")
    MapMaskDir =  os.path.join(base ,"InstrumentFiles")

    homeDir = os.path.join(base,'users')
    # user office data location
    ExpDescriptorsFile = "c:/temp/excitations.txt"


    WinDebug = True
else: # Unix
    sys.path.insert(0,'/opt/Mantid/scripts/Inelastic/Direct/')
    #sys.path.insert(0,'/opt/mantidnightly/scripts/Inelastic/Direct/')
# On analysis machines:
    MantidDir = '/opt/Mantid'
    MapMaskDir = '/usr/local/mprogs/InstrumentFiles/'
    UserScriptRepoDir = '/opt/UserScripts'
    #
    homeDir = "/home/"
    test_path(homeDir)
    #
    analysisDir = "/instrument/"
    test_path(analysisDir)

    # user office data location
    ExpDescriptorsFile = "/tmp/excitations.txt"
    WinDebug = False

def check_or_create_rb_link(homeDir,fedid,sys_rbdir,rbnumberID,create_group=True):
    """Function checks if  link to RB folder exist for the user
       and if not creates one
       Inputs:
       homeDir    -- the folder where users are located (usually /home on unix)
       fedid      -- user id in the system
       sys_rbdir -- sys_rbdir physical locations of the RB folders with data in the system
       rbnumberID  -- not a number but the name of rb proposan (includes RB prefix)
       create_group -- if true, add user to group, if false do not
    """

    # Add user to the appropriate group
    if create_group:
        os.system("/usr/sbin/usermod -a -G {0} {1}".format(rbnumberID,fedid))
    # Create link to appropriate RB folder.
    user_rb_dir = os.path.join(homeDir,rbnumberID)
    if os.path.exists(user_rb_dir):
        print( "Link exists: ",user_rb_dir)
        link_created = False
    else:
        if WinDebug:
            os.system("mklink /j {0} {1}".format(user_rb_dir,sys_rbdir))
        else:
            os.symlink(sys_rbdir, user_rb_dir)
        link_created = True
    return link_created
#--------------------------------------------------------------------
#  END Routines definitions
#--------------------------------------------------------------------


# Try to initialize Mantid part to build ISIS direct inelastic configurations
try:
    from ISISDirecInelasticConfig import MantidConfigDirectInelastic,UserProperties
    buildISISDirectConfig=True
    try:
        mcf = MantidConfigDirectInelastic(MantidDir,homeDir,UserScriptRepoDir,MapMaskDir)
        print ("Successfully initialized ISIS Inelastic Configuration script generator")
    except RuntimeError as er:
        send_error(er.message,2,1)
        buildISISDirectConfig=False
        print ("Failed to initialize ISIS Inelastic Configuration script generator")
except:
    print ("Failed to import ISIS Inelastic Configuration script: ",sys.exc_info()[0])
    buildISISDirectConfig=False

#

#admin = libuser.admin()

#list = admin.enumerateUsers("*sfp76")
#list.sort()
#for item in list:
#   print "Found a user named \"" + item + "\"."

# Get the output from the user office data which is published
# as a web page in JSON

#opener = urllib.FancyURLopener(proxies)
# Get the user office data.
urllib.urlretrieve("http://icatingest2.isis.cclrc.ac.uk/excitations.txt",ExpDescriptorsFile)
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


user_list = {}
user_verified_list = []
users_rejected_list = []
rb_key_user_inelastic = {}

#print len(data["experiments"])
for experiment in data["experiments"]:

    #RB number for the experiment
    nrbnumber  = experiment["RbNumber"]
    rbnumberID = "RB" + nrbnumber

    #Experiment start date
    date = experiment["StartDate"]

    #Instrument name
    instrument = experiment["Instrument"]

    #Cycle number
    cycle = experiment["Cycle"]
    cycle = cycle.upper()
    cycle = "CYCLE" + cycle.replace('/', '')

    #  print rbnumberID
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
            os.system("/usr/sbin/groupmod -o -g {0} {1}".format(nrbnumber,rbnumberID))
            os.system("/usr/sbin/groupadd -o -g {0} {1}".format(nrbnumber,rbnumberID))
            group_members=[]
    else:
        group_members=[]
    # Make generic cycle directories
    cyclerbdir = os.path.join(analysisDir,instrument.upper(),cycle, rbnumberID)
    main_rbData_dir = os.path.join(analysisDir,instrument.upper(),"RBNumber",rbnumberID)
    cycledir = os.path.join(analysisDir,instrument.upper(),cycle)
    #so should be analysisdir/instrumentname/RBNumber/rbnumberID

    #Make the paths to the analysis RB directories.
    mkpath(main_rbData_dir)
    test_path(main_rbData_dir)

    #Change permissions on the RB directories.
    os.system("chgrp {0} {1}".format(rbnumberID,main_rbData_dir))
    os.system("chmod -R 2770 {0}".format(main_rbData_dir))

    #make cycle folder
    if os.path.exists(cycledir):
        print ("Path OK: " +cycledir+ "\n")
    else:
        mkpath(cycledir)


    #make symb links from cycle -> individual RBs
    if os.path.exists(cyclerbdir):
        print ("Link exists: " +cyclerbdir+ "\n")
    else:
        if WinDebug:
            os.system("mklink /j {0} {1}".format(cyclerbdir,main_rbData_dir))
        else:
            os.symlink(main_rbData_dir, cyclerbdir)
    #End

    if not WinDebug:
        # Make SAMBA share available to group members.
        # Make the string to append to the smb.conf file:
        SAMBARB = "        " + "[" + rbnumberID + "]" + "\n"
        SAMBARB = SAMBARB + "        " + "comment = " + rbnumberID + "\n"
        SAMBARB = SAMBARB + "        " + "path = " + main_rbData_dir + "\n"
        SAMBARB = SAMBARB + "        " + "writable = yes" + "\n"
        SAMBARB = SAMBARB + "        " + "printable = no" + "\n"
        SAMBARB = SAMBARB + "        " + "write list = +" + rbnumberID + "\n"
        SAMBARB = SAMBARB + "        " + "force group = " + rbnumberID + "\n"
        SAMBARB = SAMBARB + "        " + "valid users = +" + rbnumberID + "\n"
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

        user_folder = os.path.join(homeDir,str(fedid))

        if not fedid in user_verified_list:
           if not WinDebug and os.system("su -l -c 'exit' " + fedid) != 0:
                user_error=fedid + " User cannot be found - account is either disabled or does not exist."
                users_rejected_list.append(fedid)
                send_error(user_error,3,0)
                continue
           else:
                user_verified_list.append(fedid)
                print (fedid + " OK")
        # Check if person is already in this group
        if fedid in group_members:
            add_to_group = False
        else:
            add_to_group = True
        #
        if os.path.exists(user_folder):
            link_created=check_or_create_rb_link(user_folder,fedid,main_rbData_dir,rbnumberID,add_to_group)
        else:
            # Create user's folder
            mkpath(user_folder)
            test_path(user_folder)
            os.system("chown -R {0}:{1} {2}".format(fedid,fedid,user_folder))
            #--------------
            link_created=check_or_create_rb_link(user_folder,fedid,main_rbData_dir,rbnumberID)
        #end userExists
        #if not old_link_exists:
        #    continue
        if not buildISISDirectConfig:
            continue
        # Define Direct inelastic User
        if mcf.is_inelastic(instrument):
           # make first user a key user for given rb number
            if not rbnumberID in rb_key_user_inelastic:
                rb_key_user_inelastic[str(rbnumberID)] = fedid

            if not fedid in user_list:
                user_list[str(fedid)] = UserProperties(str(fedid))


            current_user = user_list[fedid]
            # Define user's properties, e.g. cycle, instrument, start data 
            # and rb folder. If more then one record per user, the latest will be active
            rb_user_folder = os.path.join(mcf._home_path,str(fedid),str(rbnumberID))
            # rb folder must be present!
            current_user.set_user_properties(str(instrument),rb_user_folder,str(cycle),str(date))
        #end if
json_data.close()
if not WinDebug:
    smb.close()


# Usually user's configuration file is not overwritten if its modification date is late then
# user start date. Set below to True if you want to force overwriting configurations
#mcf._force_change_config = True
# replace users sample script. Should be used only if bugs are identified in the previous sample script.
#mcf._force_change_script = True
print ("*** ************************************************************** ***")
print ("*** Start building ISIS direct inelastic configurations for MANTID ***")
print ("*** ************************************************************** ***")
n_users = 0
# list of users who participate in all cycles but never would participate in an experiment alone
# so no need to generate configuration for them.
service_users = ['gpq43739','wkc26243','wvy65637','isisautoreduce']
if buildISISDirectConfig:
    # Generate Mantid configurations for all users who does not yet have their own
    for userID,user_prop in user_list.items():
        if userID in service_users:
            continue
        try:
            mcf.init_user(user_prop)
            mcf.generate_config(rb_key_user_inelastic)
            n_users +=1
        except (RuntimeError,AttributeError) as er:
            send_error("Configuring user: {0} Error {1}".format(userID,er.message),2,1)
            #pass
        except Exception as er:
            send_error("Configuring user: {0} Script error {1}".format(userID,str(er)),2,1)
            #pass
        #if os.path.isfile('d:\Data\Mantid_Testing\config_script_test_folder\users\kfh56921\RB1610371\MERLINReduction_2015_4.py') :
        #    continue
print ("*** ************************************************************** ***")
print ("*** Configured {0:5} ISIS direct inelastic users               ***".format(n_users))
print ("*** ************************************************************** ***")
