#!/bin/bash

POPULATE_CMD="$(which worth)"

WORTHSYNC_PID=`pgrep -f 'worth sync'`

if [[ ! $? -eq 0 ]]; then
    echo NOTIFYALERT! worthmindsync quit unexpectedly, restarting worth sync...
    cd $APP_ROOT
    exec "${POPULATE_CMD}" sync 2>&1&
fi

sleep 30

WORTHSERVER_PID=`pgrep -f 'worth server'`

if [[ ! $? -eq 0 ]]; then
    echo NOTIFYALERT! worthmindserver quit unexpectedly, restarting worth server...
    cd $APP_ROOT
    exec "${POPULATE_CMD}" server 2>&1&
fi

# prevent flapping
sleep 120