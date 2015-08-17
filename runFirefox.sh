 #!/bin/sh

#variables
userName=$2
displayNumber=$4

export HOME=/home/$userName
export DISPLAY=:$displayNumber
export PATH="/bin:/usr/bin"

firefox http://130.246.36.145 0<&- &>/dev/null &

exit 0