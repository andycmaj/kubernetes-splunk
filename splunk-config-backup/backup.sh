#!/bin/bash

set -e

# check if REPO_PATH is a repo already
if [ -d $BACKUP_PATH ]; then
    echo "Backup dir exists. Deleting before updating."
    rm -rf $BACKUP_PATH
fi
mkdir -p $BACKUP_PATH

# rsync SPLUNK_CONFIG_PATH -> REPO_PATH
echo "Syncing backup working dir with current Splunk config..."
rsync -azq $SPLUNK_CONFIG_PATH $BACKUP_PATH

zip -r splunk-configuration-latest.zip $BACKUP_PATH
echo "aws s3 cp splunk-configuration-latest.zip s3://$CONFIG_BACKUP_S3_BUCKET/splunk-configuration-latest.zip"
aws s3 cp --acl public-read splunk-configuration-latest.zip s3://$CONFIG_BACKUP_S3_BUCKET/splunk-configuration-latest.zip
echo "pushed to s3"
