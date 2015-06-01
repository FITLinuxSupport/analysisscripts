 
#!/bin/bash

# Written by Nick Fielden, v1.1: 13/4/15
# History version changes:
#  1.0 - 10/4/15 - Original version
#  1.1 - 13/4/15 - Changed logging to write to new date/time stamped log files for each run (requested by WJ). Also changed some comments.
#  1.2 - 04/5/15 - Removed san folders and set it to only do home.

# SCRIPT DESCRIPTION:
# Script to check and correct permissions in each home dir under each of the /sanX volumes.
# NOTE: THAT IF THE USER HAS SPECIFICALLY SET ANY FILES OR FOLDERS TO HAVE DIFFERENT OWNERS OR GROUPS, THEN THEY WILL BE OVERRIDDEN!
# It looks for any files and folders in each home dir that are set as root for the owner and group and resets them to the correct user
# As well as displaying messages to the console, it also writes two log files as follows:
# /var/log/home_folder_ownership_resets_<date and time>.log  --> one line for every folder it attempts to change ownership of
# /var/log/home_folder_ownership_nouser_<date and time>.log  --> one line for every folder that it skips due to not matching a user
# It will create new log files each time it runs with the current date and time appended to the filenames
# The current date and time will also be included as a header within each log file at the beginning.
# Don't forget to delete/clean up old log files if you're running this often, otherwise they'll build up.

# Enough waffle, begin the script:
# First check whether the TEST ONLY (No action) or NORMAL (do the changes) switches were specified (if no switch then exit and don't run)
# (if both switches supplied, do test mode (fail safe)
# The test only/no action switch is: -t
# The normal mode switch is: -n

# Initially set the TESTONLY and NORMAL flags to FALSE (0) before checking supplied switches:
TESTONLY=0
NORMAL=0

# Now to check the switches supplied:
while getopts ":tn" opt; do
  case $opt in
    t)
      # Set the TESTONLY flag for later to true (1):
      TESTONLY=1
      ;;
      
    n)
      # Set the NORMAL flag for later to true (1):
      NORMAL=1
      ;;
      
    \?)
      echo "Invalid option specified: -$OPTARG"
      exit 1
      ;;
   esac
done

# echo the TESTONLY flag is: $TESTONLY
# echo the NORMAL flag is: $NORMAL

# First test for TEST mode (this overrides normal mode if that was also specified)
if [ "$TESTONLY" -eq 1 ];
then
  echo -e "RUNNING IN TEST MODE - NO ACTION WILL BE TAKEN!\n"
else
  # Test mode was NOT specified, so now test for NORMAL mode switch:
  if [ "$NORMAL" -eq 1 ];
  then
    echo -e "RUNNING IN NORMAL MODE - OWNNERSHIP CHANGES WILL BE PROCESSED!\n"
  else
    # If we get to here, then neither test mode nor normal mode switches were supplied, so print warning and exit now
    echo -e "\n!!!Neither the test mode (-t) nor normal mode (-n) switches were supplied. Exiting doing nothing!\n\n"
    exit 2
  fi
fi

# Now set the output log filenames - create new log files each time with the current date and time appended to end of the filenames:
FILENAMEDATETIME=`date +%F_%T`
resetlog="/var/log/home_folder_ownership_resets_$FILENAMEDATETIME.log"
nouserlog="/var/log/home_folder_ownership_nouser_$FILENAMEDATETIME.log"

# Now append a header, the current date and time and a test/real mode running status to both log files so you know when each run started and under what conditions:
echo -e "----------------------------------------------------------------------" >>$resetlog
echo -e "----------------------------------------------------------------------" >>$nouserlog
echo -e "New script run starting at:" >>$resetlog
echo -e "New script run starting at:" >>$nouserlog
date >>$resetlog
date >>$nouserlog

if [ "$TESTONLY" -eq 1 ];
then
  echo -e "RUNNING IN TEST MODE - NO ACTION WILL BE TAKEN\n" >>$resetlog
  echo -e "RUNNING IN TEST MODE - NO ACTION WILL BE TAKEN\n" >>$nouserlog
else
  echo -e "RUNNING IN NORMAL MODE - OWNNERSHIP CHANGES WILL BE PROCESSED!\n" >>$resetlog
  echo -e "RUNNING IN NORMAL MODE - OWNNERSHIP CHANGES WILL BE PROCESSED!\n" >>$nouserlog
fi

echo -e "----------------------------------------------------------------------\n" >>$resetlog
echo -e "----------------------------------------------------------------------\n" >>$nouserlog

# OK let's start working through each /sanX folder in turn:
for SANDIR in home
do
  # Print out which SAN folder we're currently processing:
  echo -e "Processing SAN folder: /$SANDIR\n"
  
  # Now, within this SAN folder, let's work through every top level directory entry,
  # checking for whether it's a user's home folder or not (ie. does the dir name match a valid user id);
  # If the dir entry is a user's home dir, then we'll check and correct the permissions if needed...
  
  # so, the following "for" command now loops through every top level dir entry in the SAN folder that does NOT match the names "root" or "lost+found", which we wouldn't want to touch:
  for dir in $(ls /$SANDIR | grep -vw root | grep -vw lost+found )
  do
    # Print out which dir entry we're currently working on in this loop (held in the $dir variable):
    echo -e "Doing dir entry: /$SANDIR/$dir :"
    
    # Now let's do a lookup to check if that dir entry matches a valid user id.
    # We'll save any returned matching username to a variable but discard any error output to null as we don't need to see any error output if the match fails.
    USERNAME=`id -un $dir 2>/dev/null`
    
    # Now let's check the exit code from the above command, which is held in the $? system variable. 0 = a successful match, whereas anything else means no user match:
    if [ "$?" -eq 0 ];
    then
      # Ok, so this dir entry did also exactly match a valid user id (which we've stored in the $USERNAME var).  So we must now assume that this is a user's home dir.
      
      # Now recursively reset both the owner and group to the username for this folder and down its entire subtree, affecting all files and folders,
      # with the exception of symbolic links (the owneeeeeership of the symlinks themselves will be changed in the home dir, but NOT those of the end folders and files
      # they point to.  This is the default behaviour of the -R switch; we don't want it going into the symlinks and changing ownership of the targets!)
      # NOTE: THAT IF THE USER HAS SPECIFICALLY SET ANY FILES OR FOLDERS TO HAVE DIFFERENT OWNERS OR GROUPS, THEN THEY WILL BE OVERRIDDEN!
      # Also write this out to a log file to log the folders we attempt to change
      echo -e "  Resetting owner+group for /$SANDIR/$dir (and subtree) to: $USERNAME:$USERNAME"
      echo -e "  Resetting owner+group for /$SANDIR/$dir (and subtree) to: $USERNAME:$USERNAME" >>$resetlog
      # Now test if we're running in test mode or whether we should actually do the ownership changes:
      if [ "$TESTONLY" -eq 1 ];
      then
	echo -e "(RUNNING IN TEST MODE - NO ACTION TAKEN)"
	echo -e "(RUNNING IN TEST MODE - NO ACTION TAKEN)" >>$resetlog
      else
	# Running in normal mode, let's take a deep breath and do the ownership changes!:
	# echo "--Normal mode: doing changes--"
	# echo "--Normal mode: doing changes--" >>$resetlog
	chown -R $USERNAME:$USERNAME /$SANDIR/$dir
      fi
    
    else
      # This dir entry did NOT match a user id, so print that out to console and then also to a log file:
      echo -e "  NO user match fournd for dir entry: /$SANDIR/$dir.  Skipping this dir."
      echo -e "  NO user match fournd for dir entry: /$SANDIR/$dir.  Skipping this dir." >>$nouserlog
    fi
    
  echo -e "\n"
  done
echo -e "\n"  
done

