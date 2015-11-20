#!/bin/bash -x


#standard variables
LOGFILE=/var/log/homebackup$(date +%d-%m-%y_%H:%M:%S)
DATE=$(date +%d-%m-%y)

#setting up test and full run modes
TESTONLY=0
NORMAL=0

while getopts ":tn" opt; do
	case $opt in
		t)
			#set test mode
			TESTONLY=1
			;;

		n)
			#set full run mode
			NORMAL=0
			;;
		/?)
			echo "Invalid option specified: -$OPTARG"
			exit 1
			;;
	esac
done

#Let the user know at the start what mode mode they are running in
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

#putting info into logfile
echo -e "-------------------------------------------------------------" >>$LOGFILE
if [ "$TESTONLY" -eq 1 ];
then
  echo -e "RUNNING IN TEST MODE - NO ACTION WILL BE TAKEN\n" >>$LOGFILE
  echo -e "RUNNING IN TEST MODE - NO ACTION WILL BE TAKEN\n" >>$LOGFILE
else
  echo -e "RUNNING IN FULL MODE - BACKUP WILL HAPPEN!!\n" >>$LOGFILE
  echo -e "RUNNING IN FULL MODE - BACKUP WILL HAPPEN!!\n" >>$LOGFILE
fi
echo -e "-------------------------------------------------------------" >>$LOGFILE



#specify your folder you'd like this to run on.
for SOURCEFOLDER in ceph/home
        do
                echo "Running backup on: $SOURCEFOLDER" >>$LOGFILE
                #find folders in above folder that are not symbolic links
                for DIR in $(find /$SOURCEFOLDER/ -type d -maxdepth 1 | grep -vw /ceph/home/)
                do

		    #get foldername from the path
		    FOLDERNAME=$(basename $DIR)
                    #tar and split this
		    echo "TAR'ing $FOLDERNAME" from "$DIR">>$LOGFILE
		    
		    #run check if in test mode if go just echo commands that would be run, else run commands
		    if ["$TESTONLY" -eq 1];
		    then
  	                echo "tar -cvzf - $DIR |split --bytes=1TB - /ceph/backupstaging/$FOLDERNAME.tar.gz.">>$LOGFILE >>$LOGFILE
                    	echo "xrdcp /ceph/backupstaging/$FOLDERNAME.tar.gz* root://cfacdlf.esc.rl.ac.uk//castor/facilities/prod/isis_backup/$DATE$DIR/" >>$LOGFILE
			echo "removing tempfile /ceph/backupstaging/$FOLDERNAME.tar.gz">>$LOGFILE
                    echo "rm -rf /ceph/backupstaging/$FOLDERNAME.tar.gz*" >>$LOGFILE

		    else
			#tar the files and split into 1TB chunks. This will continue trying to run until completes successfully.
			until tar --use-compress-program=pigz -cvf - $DIR |split --bytes=1TB - /ceph/backupstaging/$FOLDERNAME.tar.gz.; do
				echo "Tar'ing $HOMEFOLDERNAME failed retrying in 5 seconds"
				sleep 5
			done 

			#send the files to CASTOR using xrdcp. Will keep trying until completed successfully 		    
		      	until xrdcp /ceph/backupstaging/$FOLDERNAME.tar.gz* root://cfacdlf.esc.rl.ac.uk//castor/facilities/prod/isis_backup/$DATE$DIR/ ; do
				echo " xrdcp copy has failed on $FOLDERNAME, restarting in 10 secounds...."
				sleep 10
			done
				
			echo "removing tempfile /ceph/backupstaging/$FOLDERNAME.tar.gz" >>$LOGFILE
			echo "rm -rf /ceph/backupstaging/$FOLDERNAME.tar.gz*" >>$LOGFILE
		    	rm -rf /ceph/backupstaging/$FOLDERNAME.tar.gz*
		    fi
         done

done
