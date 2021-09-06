#!/bin/bash
echo "Ready to release tutorial pdf file?" 
echo "Tell me which tutorial you are working on (e.g., t1)..."
read varname

cp -fr slides.pdf $varname/$varname.pdf

read -n 1 -s -r -p "Got it! Press any key to continue."