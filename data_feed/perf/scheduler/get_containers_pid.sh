#!/bin/bash

# read input
# -c should be in quotes e.g. -c "container1 container2 container3"
while getopts ":n:c:" opt; do
  case $opt in
    n) node="$OPTARG"
    ;;
    c) containers="$OPTARG"
    ;;
    \?) echo "Invalid option -$OPTARG" >&2
    exit 1
    ;;
  esac

  case $OPTARG in
    -*) echo "Option $opt needs a valid argument"
    exit 1
    ;;
  esac
done

# name_regex="part1|part2|part3"
names_regex=""
for cname in $containers
do
  names_regex+="$cname|"
done
names_regex=${names_regex%?} # remove last |

shell_command=("ids=\$(docker ps -f name=\"$names_regex\" | awk '{print \$1}' | tail -n +2 | awk 'BEGIN { ORS = \" \" } { print }') && docker inspect -f '{{.State.Pid}}' \$ids")

kubectl node-shell $node -- bash -c "${shell_command[@]}"