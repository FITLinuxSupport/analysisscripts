import os

#retry 5 times
for retry in range(5):
	
	#check if mounted	
	if os.path.ismount("/archive") == True:
		#if mounted break and finish
        	print "/archive is mounted"
		break
	else:
		#try and remount archive
		print "/archive is not mounted, Attempting remount"
		os.system('mount -a')

else: 
	#if after 5 tries still fails, close with error
	exit(1)
