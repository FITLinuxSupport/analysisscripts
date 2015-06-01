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

from email.mime.text import MIMEText

from pprint import pprint
from distutils.dir_util import mkpath

class MantidConfigDirectInelastic(object):
    """Class describes Mantid server specific user's configuration, 
        necessary for Direct Inelastic reduction and analysis to work

        Valid for Mantid 3.3 available on 01/03/2015 and expects server 
        to have: 
        Map/masks folder with layout defined on (e.g. svn checkout)
        https://svn.isis.rl.ac.uk/InstrumentFiles/trunk
        User scripts folder with layout defined on 
        (e.g. git checkout or Mantid script repository set-up):
        git@github.com:mantidproject/scriptrepository.git
        see https://github.com/mantidproject/scriptrepository for details

       The class have to change/to be amended if the configuration 
       changes or has additional features.
    """
    def __init__(self,mantid,home,script_repo,map_mask_folder,paraview):
        """Initialize generic config variables and variables specific to a server"""

        self._mantid_path = str(mantid)
        self._home_path  = str(home)
        self._script_repo = str(script_repo)
        self._map_mask_folder = str(map_mask_folder)
        self._paraview = str(paraview)

        self._check_server_folders_present()
        self._inelastic_instruments = ['MAPS','LET','MERLIN','MARI','HET']

        #
        self._header = ("# This file can be used to override any properties for this installation.\n"
                        "# Any properties found in this file will override any that are found in the Mantid.Properties file\n"
                        "# As this file will not be replaced with futher installations of Mantid it is a safe place to put\n"
                        "# properties that suit your particular installation.\n"
                        "#\n"
                        "# See here for a list of possible options:''# http://www.mantidproject.org/Properties_File#Mantid.User.Properties''\n"
                        "#\n"
                        "#uncomment to enable archive search - ICat and Orbiter\n"
                        "#datasearch.searcharchive = On #  may be important for autoreduction to work,\n")
        #
        self._footer = ("##\n"
                        "## LOGGING\n"
                        "##\n"
                        "\n"
                        "## Uncomment to change logging level\n"
                        "## Default is information\n"
                        "## Valid values are: error, warning, notice, information, debug\n"
                        "#logging.loggers.root.level=information\n"
                        "\n"
                        "## Sets the lowest level messages to be logged to file\n"
                        "## Default is warning\n"
                        "## Valid values are: error, warning, notice, information, debug\n"
                        "#logging.channels.fileFilterChannel.level=debug\n"
                        "## Sets the file to write logs to\n"
                        "#logging.channels.fileChannel.path=../mantid.log\n"
                        "##\n"
                        "## MantidPlot\n"
                        "##\n"
                        "## Show invisible workspaces\n"
                        "#MantidOptions.InvisibleWorkspaces=0\n"
                        "## Re-use plot instances for different plot types\n"
                        "#MantidOptions.ReusePlotInstances=Off\n\n"
                        "## Uncomment to disable use of OpenGL to render unwrapped instrument views\n"
                        "#MantidOptions.InstrumentView.UseOpenGL=Off\n")
        #
        self._dynamic_options_base = ['default.facility=ISIS']
        # Path to python scripts, defined and used by mantid wrt to Mantid Root (this path may be version specific)
        self._python_mantid_path = ['scripts/Calibration/','scripts/Examples/','scripts/Interface/','scripts/Vates/']
        # Static paths to user scripts, defined wrt script repository root
        self._python_user_scripts = set(['direct_inelastic/ISIS/qtiGenie/'])
        # Methods, which build & verify various parts of Mantid configuration
        self._dynamic_options = [self._find_paraview,self._set_default_inst,
                        self._set_script_repo, # this would be necessary to have on an Instrument scientist account, disabled on generic setup
                        self._def_python_search_path,
                        self._set_datasearch_directory,self._set_rb_directory]
        self._instr_name=None
        self._cycle_folder=[]

    def is_inelastic(self,instr_name):
        """Check if the instrument is inelastic"""
        if instr_name in self._inelastic_instruments:
            return True
        else:
            return False
    #
    def setup_user(self,fedid,instr,rb_folder,cycle_folders):
        """Define settings, specific to a user"""
        #
        if not self.is_inelastic(instr):
           raise RuntimeError('Instrument {0} is not among acceptable instruments'.format(instrument))
        self._instr_name=str(instr)

        self._fedid = str(fedid)
        user_folder = os.path.join(self._home_path,self._fedid)
        if not os.path.exists(user_folder):
            raise RuntimeError("User with fedID {0} does not exist. Create such user folder first".format(fedid))
        if not os.path.exists(str(rb_folder)):
            raise RuntimeError("Experiment folder with {0} does not exist. Create such folder first".format(rb_folder))
        #
        self._rb_folder_dir = str(rb_folder)
        # how to check cycle folders, they may not be available
        self._cycle_folder=[]
        for folder in cycle_folders:
            self._cycle_folder.append(str(folder))
        # Initialize configuration settings 
        self._dynamic_options_val = copy.deepcopy(self._dynamic_options_base)
        self._init_config()
    #
    def  _check_server_folders_present(self):
        """Routine checks all necessary server folder are present"""
        if not os.path.exists(self._mantid_path):
            raise RuntimeError("SERVER ERROR: no correct mantid path defined at {0}".format(self._mantid_path))
        if not os.path.exists(self._home_path):
            raise RuntimeError("SERVER ERROR: no correct home path defined at {0}".format(self._home_path))
        if not os.path.exists(self._script_repo):
            raise RuntimeError(("SERVER ERROR: no correct user script repository defined at {0}\n"
                                "Check out Mantid script repository from account, which have admin rights").format(self._script_repo))
        if not os.path.exists(self._map_mask_folder):
            raise RuntimeError(("SERVER ERROR: no correct map/mask folder defined at {0}\n"
                                "Check out Mantid map/mask files from svn at https://svn.isis.rl.ac.uk/InstrumentFiles/trunk")\
                                .format(self._map_mask_folder))

    def _init_config(self):
        """Execute Mantid properties setup methods"""
        for fun in self._dynamic_options:
            fun()
    #
    def _find_paraview(self):
        if os.path.exists(self._paraview):
            self._dynamic_options_val.append('paraview.ignore=0')
        else:
            self._dynamic_options_val.append('paraview.ignore=1')
    #
    def _set_default_inst(self):
        if self._instr_name:
            self._dynamic_options_val.append('default.instrument={0}'.format(self._instr_name))
        else:
            self._dynamic_options_val.append('default.instrument={0}'.format('MARI'))
    #
    def _set_script_repo(self):
        self._dynamic_options_val.append('#ScriptLocalRepository={0}'.format(self._script_repo))
    #
    def _def_python_search_path(self):
        """Define path for Mantid Inelastic python scripts"""
        # Note, instrument name script folder is currently upper case on GIT
        self._python_user_scripts.add(os.path.join('direct_inelastic/',str.upper(self._instr_name))+'/')

        path = os.path.join(self._mantid_path,'scripts/')
        for part in self._python_mantid_path:
            path +=';'+os.path.join(self._mantid_path,part)
        for part in self._python_user_scripts:
            path +=';'+os.path.join(self._script_repo,part)

        self._dynamic_options_val.append('pythonscripts.directories=' + path)
    #
    def _set_rb_directory(self):
       self._dynamic_options_val.append('defaultsave.directory={0}'.format(self._rb_folder_dir))
    #
    def _set_datasearch_directory(self):
        """Note, map/mask instrument folder is lower case as if loaded from SVN. 
           Autoreduction may have it upper case"""

        user_data_dir = os.path.abspath('{0}'.format(self._rb_folder_dir))
        map_mask_dir  = os.path.abspath(os.path.join('{0}'.format(self._map_mask_folder),'{0}'.format(str.lower(self._instr_name))))
        
        all_folders=self._cycle_folder
        data_dir = os.path.abspath('{0}'.format(all_folders[0]))
        for folders in all_folders[1:]:
             data_dir +=';'+os.path.abspath('{0}'.format(all_folders[0]))

        self._dynamic_options_val.append('datasearch.directories='+user_data_dir+';'+map_mask_dir+';'+data_dir)
    #
    def save_config(self):
        """Save generated Mantid configuration file into user's home folder"""

        config_path = os.path.join(self._home_path,self._fedid,'.mantid')
        if not os.path.exists(config_path):
            err = os.mkdir(config_path)
            if err: 
                raise RuntimeError('can not find or create Mantid configuration path {0}'.format(config_path))
        config_file = os.path.join(config_path,'Mantid.user.properties')
        if os.path.exists(config_file):
            return
        #
        fp = open(config_file,'w')
        fp.write(self._header)
        fp.write('## -----   Generated user properties ------------ \n')
        fp.write('##\n')
        for opt in self._dynamic_options_val:
            fp.write(opt)
            fp.write('\n##\n')
        fp.write(self._footer)
        fp.close()
        if platform.system() != 'Windows':
            os.system('chown '+self._fedid+' '+config_file)
#
class UserProperties(object):
    """Helper class to define & retrieve user properties"""
    def __init__(self):
        self.instrument=None
        self.cycle_folder=set()
        self.rb_dir = None
#
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


WinDebug=False
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
Paraview = '/usr/bin/paraview'

#Win Debug
if WinDebug:
    MantidDir = "c:/mprogs/MantidInstall"
    UserScriptRepoDir = r"D:\users\abuts\SVN\Mantid\scriptrepository_mantid/"
    MapMaskDir =  r'D:\users\abuts\SVN\ISIS\InstrumentFiles_svn/'
    Paraview = r"c:\Programming\Paraview_Installed"
#else:
#    san1 = "/san1"
#    test_path(san1)
#    san2 = "/san2"
#    test_path(san2)
#    san3 = "/san3"
#    test_path(san3)
#    san4 = "/san4"
#    test_path(san4)
#    san5 = "/san5"
#    test_path(san5)
#    san6 = "/san6"
#    test_path(san6)

#    san = san6

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

#Open smb.conf so we can add RB number directory exports to it
if not WinDebug:
    test_path("/etc/samba/smb.conf")
    os.system("cp -f /etc/samba/smb.tmpl /etc/samba/smb.conf")
    smb = open('/etc/samba/smb.conf', 'a')
try:
    mcf = MantidConfigDirectInelastic(MantidDir,rootDir,UserScriptRepoDir,MapMaskDir,Paraview)
except RuntimeError as er:
    send_error(er.message,2,1)


user_list = {}

#print len(data["experiments"])
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
    if not WinDebug:
        #Change permissions on the RB directories.
        os.system("chgrp " + rbnumber + " " + rbdir)
        os.system("chmod 2770 " + rbdir)

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

    for permission in range(len(data["experiments"][experiment]["Permissions"])):
        email = data["experiments"][experiment]["Permissions"][permission]["email"]
        fedid = data["experiments"][experiment]["Permissions"][permission]["fedid"]

        if WinDebug:
            user_folder = os.path.join(rootDir,str(fedid))
            mkpath(user_folder)
        else:
            if os.system("su -l -c 'exit' " + fedid) != 0:
                user_error=fedid + " User cannot be found - account is either disabled or does not exist."
                send_error(user_error,3,0)
            else:
                print fedid + " OK"
                if os.path.exists("/home/"+fedid):
                    os.system("chown -R " + fedid + "." + fedid + " " + "/home/"+fedid)
                    if os.path.exists("/home/" + fedid + "/" + rbnumber):
                        print "Link exists: " + "/home/" + fedid + "/" + rbnumber
                        os.system("/usr/sbin/usermod -a -G " + rbnumber + " " + fedid)
                    else:
                        os.symlink(rbdir, "/home/" + fedid + "/" + rbnumber)
                        os.system("/usr/sbin/usermod -a -G " + rbnumber + " " + fedid)
                else:
                    mkpath(san + "/" + fedid)
                    test_path(san + "/" + fedid)
                    os.system("chown -R " + fedid + "." + fedid + " " + san+"/"+fedid)
                    if os.path.exists("/home/"+fedid):
                        if os.path.exists("/home/" + fedid + "/" + rbnumber):
                            print "Link exists: " + "/home/" + fedid + "/" + rbnumber
                            os.system("/usr/sbin/usermod -a -G " + rbnumber + " " + fedid)
                        else:
                            os.symlink(rbdir, "/home/" + fedid + "/" + rbnumber)
                            os.system("/usr/sbin/usermod -a -G " + rbnumber + " " + fedid)
                    else:
                        os.symlink(san+"/"+fedid,"/home/"+fedid)
                        os.symlink(rbdir, "/home/" + fedid + "/" + rbnumber)
                        os.system("/usr/sbin/usermod -a -G " + rbnumber + " " + fedid)
                    
        # Define user
        if mcf.is_inelastic(instrument):
            if not fedid in user_list:
                user_list[fedid] = UserProperties()
            current_user = user_list[fedid]
            # Define instrument user will deploy (only one currently supported)
            current_user.instrument= instrument
            # define data search path
            current_user.cycle_folder.add(cycle_dir2)
            # define curent (recent) rb folder
            current_user.rb_dir = rbdir
        #end if
json_data.close()
if not WinDebug:
    smb.close()

# Generate Mantid configurations for all users who does not yet have their own
for fedid,user_prop in user_list.iteritems():
    try:
        mcf.setup_user(fedid,user_prop.instrument,user_prop.rb_dir,user_prop.cycle_folder)
        mcf.save_config()
    except RuntimeError as er:
        send_error(er.message,2,1)

