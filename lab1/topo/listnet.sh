#!/bin/bash

if [ "$(whoami)" != "root" ]; then
    echo "You need to be root or run with sudo"
    exit 1
fi

lsns -t net
