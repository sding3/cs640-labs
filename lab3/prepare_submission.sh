#!/bin/bash

# From lab3 instruction:
#> For submitting your work, you should put the following files into a .tar.gz
#>   file, and submit to Canvas folder.
#> blastee.py: Your blastee implementation
#> blaster.py: Your blaster implementation
#> middlebox.py: Your middlebox implementation
#> README.txt: This file will contain a line for each student in your team:
#>   [name_of_student][single whitespace][student’s net id]
#> IMPORTANT: The file names in your hand in directory has to exactly match
#>   the file names above. Otherwise, you will lose points!

target="/tmp/.tar.gz"

tar -czvf "${target}" \
    blastee.py   \
    blaster.py   \
    middlebox.py \
    README.txt
