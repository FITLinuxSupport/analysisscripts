#!/bin/bash


#standard variables
LOGFILE=/ceph/backupstaging/homebackup$(date +%d-%m-%y)
DATE=$(date +%d-%m-%y)
#STAGINGAREA=/ceph/backupstaging
STAGINGAREA=/ceph/backupstaging

#folder range - this can be used to limit the certain folders you are backing up. ie 1,5 will take the first 5, 12,20 will take folders 12-20
FOLDERRANGE=1,2

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
			NORMAL=1
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
  echo "Start time: $(date)" >>$LOGFILE

echo -e "-------------------------------------------------------------" >>$LOGFILE



#specify your folder you'd like this to run on.
SOURCEFOLDER=home

    echo "Running backup on: $SOURCEFOLDER" >>$LOGFILE

    #list folders in above folder that are not symbolic links
    for DIR in $(sudo find /$SOURCEFOLDER/ -maxdepth 1 -type d| grep -vw /$SOURCEFOLDER/|sed -n -e $NAMERANGE\p)
    do

		  #get foldername from the path
		  FOLDERNAME=$(basename $DIR)
		  echo "TAR'ing $FOLDERNAME" from "$DIR">>$LOGFILE

		  #run check if in test mode if go just echo commands that would be run, else run commands
		  if [ "$TESTONLY" -eq 1 ];
		    then
  	      echo "tar -czf - $DIR |split --bytes=1TB - $STAGINGAREA/$FOLDERNAME.tar.gz.">>$LOGFILE
          echo "xrdcp $STAGINGAREA/$FOLDERNAME.tar.gz* root://cfacdlf.esc.rl.ac.uk//castor/facilities/prod/isis_backup/$DATE$DIR/" >>$LOGFILE
			    echo "removing tempfile $STAGINGAREA/$FOLDERNAME.tar.gz">>$LOGFILE
          echo "rm -rf $STAGINGAREA/$FOLDERNAME.tar.gz*" >>$LOGFILE
        fi

        if [ "$NORMAL" -eq 1 ]
        then
          #tar the files and split into 1TB chunks. This will continue trying to run until completes successfully.
          echo "Tar start time: $(date)" >> $LOGFILE
            until sudo tar --use-compress-program=pigz -cvf - $DIR 2>>$LOGFILE  |split --bytes=1TB - $STAGINGAREA/$FOLDERNAME.tar.gz. ; do
				    echo "Tar'ing $HOMEFOLDERNAME failed retrying in 5 seconds" >>$LOGFILE
            echo "Tar failed time: $(date)" >>$LOGFILE
				    sleep 5
            echo "Tar restarting time: $(date)" >> $LOGFILE
			    done
			    echo "Tar finish time: $(date)" >> $LOGFILE

			#send the files to CASTOR using xrdcp. Will keep trying until completed successfully
        echo " Copying $FOLDERNAME.tar.gz to SCD Via xrdcp"
        echo "xrdcp start time: $(date)" >> $LOGFILE
          sudo chmod 777 $STAGINGAREA/$FOLDERNAME.tar.gz*
          until xrdcp $STAGINGAREA/$FOLDERNAME.tar.gz* root://cfacdlf.esc.rl.ac.uk//castor/facilities/prod/isis_backup/$DATE$DIR/ ; do
            echo " xrdcp copy has failed on $FOLDERNAME.tar.gz, restarting in 10 secounds...." >>$LOGFILE
            echo " xrdcp copy failed time: $(date)" >> $LOGFILE
				    sleep 10
            echo "xrdcp copy restarting time: $(date)" >>$LOGFILE
          done

			    echo "removing tempfile $STAGINGAREA/$FOLDERNAME.tar.gz" >>$LOGFILE
			    echo "rm -rf $STAGINGAREA/$FOLDERNAME.tar.gz*" >>$LOGFILE
#		    	rm -rf $STAGINGAREA/$FOLDERNAME.tar.gz*
		  fi
done

echo "End time: $(date)" >>$LOGFILE
echo -e "---------------------------------------------------------------" >>$LOGFILE


