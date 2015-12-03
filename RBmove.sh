#!/bin/bash

FOLDER=instrument

#for each instrument
for INSTRUMENT in $(find /$FOLDER/ -maxdepth 1 \! -type l | xargs ls -d | grep -vw '/$FOLDER/')
        do
        echo "$FOLDER = FOLDER Variable"
        echo "$INSTRUMENT = INSTRUMENT Variable"

#for each cycle
        for CYCLE in $(find $INSTRUMENT -maxdepth 1 \! -type l | xargs ls -d | grep 'CYCLE')
                do
                echo "$CYCLE = CYCLE Variable"

#for each RBNumber
                for RBPATH in $(find $CYCLE -maxdepth 1 \! -type l | xargs ls -d | grep 'RB')
                        do
                        echo "$RBPATH = RBPATH Variable"
                        RB=$(basename $RBPATH)
                        echo "$RB = RB Variable"
                        

			echo " Moving $RB"
			mv $RBPATH $INSTRUMENT/RBNumber/
			
			echo "Creating Sym link for $RB"
			ln -s $INSTRUMENT/RBNumber/$RB $RBPATH

                        done

                echo "==================================================="
                echo "==================================================="
        done
done

