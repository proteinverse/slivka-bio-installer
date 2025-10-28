#! /bin/bash

# A workaround to expose the database files as outputs.
mkdir dbs
cp $ABSOLVE_DBS/*.aa.fa dbs/

absolve "$@"
