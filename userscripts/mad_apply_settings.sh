#!/bin/bash 

###########################################################
# User configuration
###########################################################
# madmin apply settings / reload url
# Examples for madmin reload urls (madmin runing on same server):
#  - without madmin passwort (e.g. using nginx passwort instead):  apply_settings_url="http://localhost:5000/reload"
#  - with madmin passwort: apply_settings_url="-u madmin:password http://localhost:5000/reload"
apply_settings_url="http://localhost:5000/reload"

##########################################################
# script -> don't change
##########################################################
http_response=$(curl -s -o /dev/null -w '%{http_code}' $apply_settings_url)
#more information on console:
#http_response=$(curl -s -nv -o /dev/null -w '%{http_code}' $apply_settings_url)

if [ $http_response != "302" ]; then
    # handle error
    echo "mad_apply_settings.sh FAILED with http-code:$http_response"
    exit 1
else
    echo "mad_apply_settings.sh executed successfully"
    exit 0
fi
