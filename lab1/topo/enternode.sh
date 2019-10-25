#!/bin/bash

if [ "$(whoami)" != "root" ]; then
    echo "You need to be root or run with sudo"
    exit 1
fi

line="$(lsns -t net | grep "${1}"$)"
pid="$(awk '{print $4}' <<< $line)"

if [ "$pid" == "" ]; then
    echo "$1 not found"
    exit 1
fi

export PS1="🌐 $1 $ "
nsenter -n/proc/"${pid}"/ns/net bash --norc
