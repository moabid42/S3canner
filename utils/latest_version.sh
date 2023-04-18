#!/bin/bash

# Terraform var file
terraform_var="./terraform/modules/lambda/variables.tf"

# The current python runtime version
pv=$(cat $terraform_var | grep python | grep -oP '(?<=python)\d+\.\d+' )
previous_version="python$pv"

# get the runtimes from the botocore source code 
RuntimeVersionsURL="https://raw.githubusercontent.com/boto/botocore/develop/botocore/data/lambda/2015-03-31/service-2.json"
latest_version=$(curl -s $RuntimeVersionsURL | jq -r '.shapes.Runtime.enum[]' | grep python | tr ' ' '\n' | sort -r | head -n 1)

# Replace the value of sedme in the python_runtime_version variable definition with the value of the MYVAR environment variable
sed -i -e "s/$previous_version/$latest_version/g" $terraform_var

