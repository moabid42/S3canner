#!/bin/bash


# get the runtimes from the botocore source code 
lambda_runtimes=$(curl -s https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html \
    | pup '.table-container' | pup ':parent-of(:parent-of(:parent-of(:parent-of(:contains("Supported")))))' \
    | pup 'tbody code text{}' | sed '/^[[:space:]]*$/d' | tr -d ' ' | grep python)

lambda_latest_runtime_version=$(echo $lambda_runtimes | sort -r | head -n 1)

echo "The latest is : $lambda_latest_runtime_version"
