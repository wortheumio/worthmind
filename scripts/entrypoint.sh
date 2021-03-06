#!/bin/bash

# NOTE: this script will be executed again if worth crashes or aborts. This
# could happen in the case of an unexpected upstream/API response, or when
# a non-micro-fork was encountered. Worth has a startup routine which attempts
# to recover automatically, so database should be kept intact between restarts.

# eb with self-contained postgres need to set: RUN_IN_EB, S3_BUCKET, and SYNC_TO_S3 (boolean) if a syncer
# eb with external postgres do not require RUN_IN_EB, S3_BUCKET, or SYNC_TO_S3
# with external postgres need to set: SYNC_SERVICE if a syncer
# worth expects: DATABASE_URL, LOG_LEVEL, WORTHS_URL, JUSSI_URL
# default DATABASE_URL should be postgresql://postgres:postgres@localhost:5432/postgres

POPULATE_CMD="$(which worth)"

if [[ "$RUN_IN_EB" ]]; then
  mkdir /var/lib/postgresql/9.5/main
  if [[ $? -ne 0 ]]; then
    echo worthmind: restarted -- db already exists. skip init, start postgres
    service postgresql start
  else
    chown -R postgres:postgres /var/lib/postgresql/9.5
    cd /var/lib/postgresql/9.5

    echo worthmind: attempting to pull in state file from s3://$S3_BUCKET/worthmind-$SCHEMA_HASH-latest.tar.lz4

    finished=0
    count=1
    while [[ $count -le 5 ]] && [[ $finished == 0 ]]
    do
      s3cmd get s3://$S3_BUCKET/worthmind-$SCHEMA_HASH-latest.tar.lz4 - | lz4 -d | tar x
      if [[ $? -ne 0 ]]; then
        sleep 1
        echo notifyalert worthmind: unable to pull state from S3 - attempt $count
        (( count++ ))
      else
        finished=1
      fi
    done

    if [[ $finished == 0 ]]; then
      if [[ ! "$SYNC_TO_S3" ]]; then
        echo notifyalert worthmind: unable to pull state from S3 - exiting
        exit 1
      else
        echo worthmindsync: state file for schema version $SCHEMA_HASH not found, creating a new one from genesis
        chpst -upostgres /usr/lib/postgresql/9.5/bin/initdb -D /var/lib/postgresql/9.5/main
      fi
    else
      echo worthmind: state file loaded successfully
    fi

    service postgresql start

    # following config assumes 12GB mem available for pg
    chpst -upostgres psql -c "ALTER SYSTEM SET effective_cache_size = '7GB';"
    chpst -upostgres psql -c "ALTER SYSTEM SET maintenance_work_mem = '512MB';"
    chpst -upostgres psql -c "ALTER SYSTEM SET random_page_cost = 1.0;"
    chpst -upostgres psql -c "ALTER SYSTEM SET shared_buffers = '3GB';"
    chpst -upostgres psql -c "ALTER SYSTEM SET work_mem = '512MB';"
    chpst -upostgres psql -c "ALTER SYSTEM SET synchronous_commit = 'off';"
    chpst -upostgres psql -c "ALTER SYSTEM SET checkpoint_completion_target = 0.9;"
    chpst -upostgres psql -c "ALTER SYSTEM SET checkpoint_timeout = '30min';"
    chpst -upostgres psql -c "ALTER SYSTEM SET max_wal_size = '4GB';"

    chpst -upostgres psql -c "ALTER USER postgres WITH PASSWORD 'postgres';"

    service postgresql restart
  fi
  cd $APP_ROOT
  # startup worth
  echo worthmind: starting sync
  exec "${POPULATE_CMD}" sync 2>&1&

  echo worthmind: starting server
  if [[ ! "$SYNC_TO_S3" ]]; then
      exec "${POPULATE_CMD}" server
  else
      exec "${POPULATE_CMD}" server --log-level=warning 2>&1&
      mkdir -p /etc/service/worthsync
      cp /usr/local/bin/worthsync.sh /etc/service/worthsync/run
      chmod +x /etc/service/worthsync/run
      echo worthmind: starting worthsync service
      runsv /etc/service/worthsync
  fi
else
  # start worth with an external postgres
  cd $APP_ROOT
  if [[ "$SYNC_SERVICE" ]]; then
    echo worthmind: starting sync
    exec "${POPULATE_CMD}" sync 2>&1&
    echo worthmind: starting server
    exec "${POPULATE_CMD}" server 2>&1&
    # make sure worth sync and server continually run
    mkdir -p /etc/service/worthsync
    cp /usr/local/bin/worthsynccontinue.sh /etc/service/worthsync/run
    chmod +x /etc/service/worthsync/run
    runsv /etc/service/worthsync
  else
    echo worthmind: starting server
    exec "${POPULATE_CMD}" server
  fi
fi

echo worthmind: application has stopped, see log for errors
