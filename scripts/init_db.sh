#!/bin/bash

python _create_database.py
./_restore_dump.sh
python _create_tables.py