#!/bin/bash

target="/tmp/.tar.gz"

tar -czvf "${target}" \
    myswitch_fifo.py myswitch_stp.py SpanningTreeMessage.py README
