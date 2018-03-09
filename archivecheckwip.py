##This script is to check if a mount point is mounted or not, if its not it will try and mount it, this will try 5 times before erroring.

import os
import smtplib
import socket 
import sys
import time
from email.mime.text import MIMEText

#--------------------------------------------------------------------
#  User Settings:
#--------------------------------------------------------------------

mountpoint = "/archive"
sysadmin_email = ["warren.jeffs@stfc.ac.uk"]

#--------------------------------------------------------------------
#  Routines definitions:
#--------------------------------------------------------------------

#Sending email routine
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
#Map error codes to email messages
def send_error(MessBody=None,ErrorCode=0,ExitScript=0):
    if ErrorCode == 1:
        sub = mountpoint + " Not mounted on" + socket.gethostname() + " attempting remount"
        msg = 'CRITICAL ERROR ' + mountpoint + " not mounted. Attempting remount"
    elif ErrorCode == 2:
	sub = 'CRITICAL ERROR ' + mountpoint + " could not be remounted on " + socket.gethostname()
	msg = 'CRITICAL ERROR ' + mountpoint + " could not be remounted on " + socket.gethostname()
    else:
        sub = 'CRITICAL ERROR: mount check of '  + mountpoint + " on " + socket.gethostname()
	msg = 'CRITICAL ERROR: mount check of '  + mountpoint + " on " + socket.gethostname()	
	
    send_alert_email('mountcheck@' + socket.gethostname(),sysadmin_email,sub, msg)

    if ErrorCode == 1:
	sys.exit()

#--------------------------------------------------------------------
#  End of Routines
#--------------------------------------------------------------------
	
	
#retry 5 times
for retry in range(5):

        #check if mounted
        if os.path.ismount(mountpoint) == True:
                #if mounted break and finish
                print "/archive is mounted"
                break
        else:
                #try and remount archive
                print "/archive is not mounted, Attempting remount"
                mountcommand = "mount " + mountpoint
		print(mountcommand)
		os.system(mountcommand)
		send_error("",1,1)
		time.sleep(5)

else:
        #if after 5 tries still fails, close with error and send email
	send_error("",2,1)
        exit(1)

