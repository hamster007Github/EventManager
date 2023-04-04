#!/bin/bash

###########################################################
# User configuration
###########################################################
# madmin apply settings / reload url
# adapt 'password' and 'https://madmin.my-external-url.com' for your specific setup
apply_settings_url="-u madmin:password http://madmin.my-external-url.com/reload"

##########################################################
# script -> don't change
##########################################################
http_response=$(curl -s -o /dev/null -w '%{http_code}' $apply_settings_url)
#more information on console:
#http_response=$(curl -s -nv -o /dev/null -w '%{http_code}' $url)

if [ $http_response != "302" ]; then
    # handle error
    echo "mad_custom_apply_settings.sh FAILED with http-code:$http_response"
    exit 1
else
    echo "mad_custom_apply_settings.sh executed successfully"
    exit 0
fi
