#!/bin/bash

# Script setting oom_score_adj for running containers
# Example: ./set_containers_oom_score_adj -n minikube-1-m02 -c "redis_pod1 data-feed-container_pod1" -s "-1000 0"
# -n node name
# -c should be in quotes e.g. -c "container1_pod1 container2_pod1 container3_pod2"
# -s score - list of scores, maps to each container_pod string in -c
while getopts ":n:c:s:" opt; do
  case $opt in
    n) node="$OPTARG"
    ;;
    c) containers="$OPTARG"
    ;;
    s) oom_scores_adj="$OPTARG"
    ;;
    \?) echo "Invalid option -$OPTARG" >&2
    exit 1
    ;;
  esac

done

shell_command=(
  "
  set -e
  container_ids_temp_file=\$(mktemp)

  function write_container_id_to_file() {
    container_name=\$1
    id=\$(docker ps -f name=\"\$container_name\" | awk '{print \$1}' | tail -n +2 )
    arr=(\$id)
    len=\${#arr[@]}
    if [[ \"\$len\" -ne 1 ]]; then
      echo \"Error: found \$len container ids for \$container_name (should be 1). Check container name\"
      exit 1
    fi
    var=\"\$container_name \$id\"
    echo \$var >> \$container_ids_temp_file
  }

  for container_name in $containers
  do
    write_container_id_to_file \$container_name &
  done
  wait

  tail \$container_ids_temp_file

  container_pids_temp_file=\$(mktemp)

  function write_container_pids_to_file() {
    container_name=\$1
    container_id=\$2
    pids=\$(docker top \$container_id | awk '{print \$2}' | tail -n +2)
    var=\"\$container_name \$pids\"
    echo \$var >> \$container_pids_temp_file
  }

  while read container_name_id; do
    arr=(\$container_name_id)
    container_name=\${arr[0]}
    container_id=\${arr[1]}
    write_container_pids_to_file \$container_name \$container_id
  done < \$container_ids_temp_file
  wait

  tail \$container_pids_temp_file

  function set_oom_score_adj() {
    container_name=\$1
    pid=\$2
    score_adj=\$3
    path=\"proc/\$pid/oom_score_adj\"
    if test -f \$path; then
      echo \"\$score_adj\" > \$path
      echo \"{container: \$container_name, pid: \$pid, oom_score_adj: \$score_adj}\"
    fi
  }

  count=0
  oom_scores_adj=\"$oom_scores_adj\"
  arr_scores=(\$oom_scores_adj)
  while read container_name_pids; do
    arr=(\$container_name_pids)
    container_name=\${arr[0]}
    pids=\${arr[@]:1}
    oom_score_adj=\${arr_scores[\$count]}
    count+=1
    for pid in \$pids
    do
      set_oom_score_adj \$container_name \$pid \$oom_score_adj &
    done
  done < \$container_pids_temp_file
  wait

  rm -f \$container_ids_temp_file
  rm -f \$container_pids_temp_file
  "
)

kubectl node-shell $node -- bash -c "${shell_command[@]}"

# one liner to read on node
# ids=$(docker ps -f name=$name_regex | awk '{print $1}' | tail -n +2 )
# pids_temp_file=$(mktemp)
# for id in $ids; do (docker top $id | awk '{print $2}' | tail -n +2 >> $pids_temp_file &); done
# while read pid; do (path="proc/$pid/oom_score_adj"; if test -f $path; then (cat $path); else echo "huy"; fi); done < $pids_temp_file
