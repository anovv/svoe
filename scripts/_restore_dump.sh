#!/bin/bash

# TODO support mysql restore

echo '.read svoe_db_sqlitedump.sql' | sqlite3 /tmp/svoe/sqlite/svoe_db.db