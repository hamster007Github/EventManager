#!/bin/bash

###########################################################
# User configuration
###########################################################
# madmin apply settings / reload url
# Examples for madmin reload urls (madmin runing on same server):
#  - without madmin passwort (e.g. using nginx passwort instead):  address="http://localhost:5000/reload"
#  - with madmin passwort: address="-u madmin:password http://localhost:5000/reload"

#How many instances do you want to apply settings to
instance_count=1

#Address of the madmin webserver
address="http://localhost"

#For each instance, place its port number below. 
#Example (5000 50001 5002 5003 5004) and etc.
#Remember to increment the instance_count for each port number!
ports=(5000)


##########################################################
# script -> don't change
##########################################################
loop=0
if [ ${#ports[@]} != $instance_count ]; then
	echo "Instance count does not match amount of ports"
fi
while [ $loop != $instance_count ]; do
echo " " #output spacer
port=${ports[$loop]}
url="$address:$port/reload"

http_response=$(curl -s -o /dev/null -w '%{http_code}' $url)
#more information on console:
#http_response=$(curl -s -nv -o /dev/null -w '%{http_code}' $url)

if [ $http_response != "302" ]; then
    # handle error
    echo "Instance ${ports[$loop]} Failed to reload"
else
    echo "Instance ${ports[$loop]} successfully reloaded"
	
fi
((loop++))
sleep 2
done
