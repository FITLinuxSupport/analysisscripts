if [ ! -f  ~/Desktop/HoraceExampleScripts];
then
    ln -s /home/resources/HoraceExampleScripts/ ~/Desktop/HoraceExampleScripts
else
    exit 0
fi