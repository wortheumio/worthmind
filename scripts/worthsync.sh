#!/bin/bash

WORTHSYNC_PID=`pgrep -f 'worth sync'`

if [[ ! $? -eq 0 ]]; then
    echo NOTIFYALERT! worthmindsync quit unexpectedly, saving partial state...
    FILE_NAME=worthmind-$SCHEMA_HASH-`date '+%Y%m%d-%H%M%S'`-partial.tar.lz4

else
    HEAD_AGE=`curl -s http://127.0.0.1:8080/head_age`
    if [ -n "$HEAD_AGE" ]; then
        echo worthmindsync: current head age is $HEAD_AGE seconds
    fi

    # returns 200 if head is < 15s old, signaling sync is complete. else, 500.
    HTTP_CODE=`curl -I -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/head_age`
    if [[ ${HTTP_CODE} -ne 200 ]]; then
        # worth is still syncing, not complete... check back in 5 minutes
        sleep 300
        exit 0
    fi

    echo worthmindsync: sync complete, waiting for worth to exit cleanly...
    kill -SIGINT $WORTHSYNC_PID
    while [ -e /proc/$WORTHSYNC_PID ]; do sleep 0.1; done
    FILE_NAME=worthmind-$SCHEMA_HASH-`date '+%Y%m%d-%H%M%S'`.tar.lz4
fi

echo worthmindsync: stopping postgres service
service postgresql stop

echo worthmindsync: starting a new state file upload operation, compressing directory...
cd /var/lib/postgresql/9.5
echo worthmindsync: postgres data dir size is `du -hs .`
tar cf worthmind.tar.lz4 --use-compress-prog=lz4 -C /var/lib/postgresql/9.5 main
if [[ ! $? -eq 0 ]]; then
  echo NOTIFYALERT! worthmindsync was unable to compress state file, check the logs.
  exit 1
else
  echo worthmindsync: compressed `du -hs worthmind.tar.lz4`
fi

echo worthmindsync: uploading $FILE_NAME to s3://$S3_BUCKET
aws s3 cp worthmind.tar.lz4 s3://$S3_BUCKET/$FILE_NAME --only-show-errors
if [[ ! $? -eq 0 ]]; then
    echo NOTIFYALERT! worthmindsync was unable to upload $FILE_NAME to s3://$S3_BUCKET
    exit 1
fi

FILE_LAST=worthmind-$SCHEMA_HASH-latest.tar.lz4
echo worthmindsync: replacing current version of $FILE_LAST with $FILE_NAME
aws s3 cp s3://$S3_BUCKET/$FILE_NAME s3://$S3_BUCKET/$FILE_LAST --only-show-errors
if [[ ! $? -eq 0 ]]; then
    echo NOTIFYALERT! worthmindsync was unable to overwrite $FILE_LAST with $FILE_NAME
    exit 1
fi

echo worthmindsync: state upload complete, restarting sync...
# sleep 1800

# kill the container starting the process again
echo worthmindsync: killing container and starting a new instance..
RUN_SV_PID=`pgrep -f /etc/service/worthsync`
kill -9 $RUN_SV_PID
