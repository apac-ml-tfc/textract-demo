#!/bin/bash

STAGINGS3=$1
STACKNAME=$2
AWSPROFILE=$3

TEMPLATEFILE=template.yml
PACKAGEFILE=template.tmp.yml

if [ -z "$AWSPROFILE" ]
then
    echo "AWSPROFILE not provided - using default"
    AWSPROFILE=default
fi

# Colorization (needs -e switch on echo, or to use printf):
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color (end)

if [ -z "$STAGINGS3" ]
then
    echo -e "${RED}Error:${NC} First argument must be an S3 bucket name to build to and deploy from"
    echo "(You must create / select a bucket you have access to as a prerequisite)"
    exit 1
elif [ -z "$STACKNAME" ]
then
    echo -e "${RED}Error:${NC} Second argument must be a name to give your CloudFormation stack"
    echo "(Under 12 characters, all lowercase, which will prefix created AWS resource names)"
    exit 1
fi

echo -e "Using '${CYAN}${AWSPROFILE}${NC}' as AWS profile"
echo -e "Using '${CYAN}${STAGINGS3}${NC}' as source s3 bucket"
echo -e "Using '${CYAN}${STACKNAME}${NC}' as CloudFormation stack name"

# Exit if any build/deploy step fails:
set -e

echo "Running SAM build..."
sam build \
    --use-container \
    --template $TEMPLATEFILE \
    --profile $AWSPROFILE

echo "Running SAM package..."
sam package \
    --output-template-file $PACKAGEFILE \
    --s3-bucket $STAGINGS3 \
    --s3-prefix sam \
    --profile $AWSPROFILE

echo "Copying final CloudFormation template to S3..."
aws s3 cp $PACKAGEFILE "s3://${STAGINGS3}/package.yaml" --profile $AWSPROFILE

echo "Running SAM deploy..."
sam deploy \
    --template-file $PACKAGEFILE \
    --stack-name $STACKNAME \
    --capabilities CAPABILITY_NAMED_IAM \
    --profile $AWSPROFILE
    # --parameter-overrides \
    #     ProjectId=$STACKNAME \

echo -e "${CYAN}Full stack deployed!${NC}"
