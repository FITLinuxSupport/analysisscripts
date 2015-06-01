#!/bin/bash

#specify your folder you'd like this to run on - this is where you symbolic links will be created.
for sourcefolder in home
        do

                #find folders in above folder that are not symbolic links
                for DIRS in $(find /$sourcefolder/ -maxdepth 1 \! -type l | xargs ls -d|grep -vw '/home/')
#|grep -vw '/home/zmp58988')
                        do
                        #get the folder name
                        FOLDERNAME=$(basename $DIRS)
                        TARGETFOLDER=/ceph/home/
			TODELETE=/ceph/tmp/todeleteoldhomedir/
			DATE=echo $(date +"%d-%m-%y")

				#remove the .gvfs problem
				umount $DIRS/.gvfs
                                #move the folder
                                echo "Moving $DIRS"
                                rsync -avv --progress --human-readable $DIRS $TARGETFOLDER
				echo "putting temp/to-delete copy in $TODELETE"
				mv $DIRS $TODELETE$DATE/

                                #create the symbolic link
                                echo "Creating symbolic link for $DIRS"
                                ln -s $TARGETFOLDER$FOLDERNAME /$sourcefolder/$FOLDERNAME

                        done

                done

