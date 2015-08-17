#!/bin/bash

#specify your folder you'd like this to run on - this is where you symbolic links will be created.
for sourcefolder in home
        do

                #find folders in above folder that are not symbolic links
                for DIRS in $(find /$sourcefolder/ -maxdepth 1 \! -type l | xargs ls -d|grep -vw '/home/')
                        do
                        #get the folder name
                        FOLDERNAME=$(basename $DIRS)
                                
								#Making home dirs
                                echo "Making Desktop folder for missing accounts"
                                mkdir /$sourcefolder/$FOLDERNAME/.config/
								mkdir /$sourcefolder/$FOLDERNAME/.config/autostart
                                #move the folder
                                echo "Copying desktop items"
                                yes | cp -f /etc/skel/.config/autostart/statuspage.desktop /$sourcefolder/$FOLDERNAME/.config/autostart/
                                echo " /$sourcefolder/$FOLDERNAME/.config/autostart/ Done"
								echo " "
                        done

                done


