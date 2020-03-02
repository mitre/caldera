#!/bin/bash

function wifi_scan {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        /System/Library/PrivateFrameworks/Apple80211.framework/Versions/A/Resources/airport scan
    else
        nmcli dev wifi
    fi
}

function wifi_pref {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        networksetup -listpreferredwirelessnetworks en0
    else
        nmcli -f autoconnect-priority,name c
    fi
}

function wifi_on {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        networksetup -setairportpower en0 on
    else
        nmcli radio wifi on
    fi
}

function wifi_off {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        networksetup -setairportpower en0 off
    else
        nmcli radio wifi off
    fi
}


if [ $1 = "scan" ]; then
    wifi_scan
elif [ $1 = "pref" ]; then
    wifi_pref
elif [ $1 = "on" ]; then
    wifi_on
elif [ $1 = "off" ]; then
    wifi_off
else
  echo "no action"
fi