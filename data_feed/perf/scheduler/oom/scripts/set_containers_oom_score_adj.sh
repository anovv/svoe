#!/bin/bash
set -e

# Script setting oom_score_adj and getting pids for running containers
# -c should be in quotes e.g. -c "container1_pod1 container2_pod1 container3_pod2"
# -s score - list of scores, maps to each container_pod string in -c. Allows empty string

# SCRIPT PARAMS ARE SET AS ENV VARS IF RUN LOCALLY
# OR PARSED BY PYTHON AND SET IN TEMPLATE. DO NOT CHANGE NAME
OOM_SCORES_ADJ_PARAM="" # list of scores, maps to each container_pod string "1000 -1000"  Allows empty string
CONTAINERS_PARAM="" # example "container1_pod1 container2_pod1 container3_pod2"

OOM_SCORES_ADJ=$OOM_SCORES_ADJ_PARAM
CONTAINERS=$CONTAINERS_PARAM

container_ids_temp_file=$(mktemp)

write_container_id_to_file() {
  container_name=$1
  id=$(docker ps -f name="$container_name" | awk '{print $1}' | tail -n +2 )
  arr=("$id")
  len=${#arr[@]}
  if [ "$len" -ne 1 ]; then
    echo "Error: found $len container ids for $container_name (should be 1). Check container name"
    exit 1
  fi
  var="$container_name $id"
  echo $var >> $container_ids_temp_file
}

for container_name in $CONTAINERS
do
  write_container_id_to_file $container_name &
done
wait

container_pids_temp_file=$(mktemp)

write_container_pids_to_file() {
  container_name=$1
  container_id=$2
  pids=$(docker top $container_id | awk '{print $2}' | tail -n +2)
  var="$container_name $pids"
  echo $var >> $container_pids_temp_file
}

while read container_name_id; do
  arr=("$container_name_id")
  container_name=${arr[0]}
  container_id=${arr[1]}
  write_container_pids_to_file $container_name $container_id
done < $container_ids_temp_file
wait

set_oom_score_adj() {
  container_name=$1
  pid=$2
  score_adj=$3
  path="proc/$pid/oom_score_adj"
  if test -f $path; then
    if ! test -z $score_adj; then
      echo "$score_adj" > $path
      echo "container: $container_name, pid: $pid, oom_score_adj: $score_adj"
    else
      echo "container: $container_name, pid: $pid"
    fi
  fi
}

count=0
arr_scores=("$OOM_SCORES_ADJ")
len_scores=${#arr_scores[@]}
while read container_name_pids; do
  arr=($container_name_pids) # no quotes here
  container_name=${arr[0]}
  pids=${arr[@]:1}
  oom_score_adj=""
  if [[ "$count" -lt "$len_scores" ]]; then
    oom_score_adj=${arr_scores[$count]}
  fi
  count+=1
  for pid in $pids
  do
    set_oom_score_adj $container_name $pid $oom_score_adj &
  done
done < $container_pids_temp_file
wait

rm -f $container_ids_temp_file
rm -f $container_pids_temp_file