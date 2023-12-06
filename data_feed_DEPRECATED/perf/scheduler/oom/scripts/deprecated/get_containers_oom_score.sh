#!/bin/bash

# Script getting oom score and oom_score_adj for all processes running in specified containers
# Example: ./set_containers_oom_score_adj -n minikube-1-m02 -c "redis_pod1 data-feed-container_pod1"
# -n node name
# -c should be in quotes e.g. -c "container1_pod1 container2_pod2 container3_pod1"
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

done

shell_command=(
  "
  set -e
  for container in $containers
  do
    id=\$(docker ps -f name=\$container | awk '{print \$1}' | tail -n +2 )
    arr_ids=(\$id)
    len=\${#arr_ids[@]}

    if [[ \"\$len\" -ne 1 ]]; then
      echo \"Error: found \$len container ids for \$container (should be 1). Check container name\"
      exit 1
    fi
    pids=\$(docker top \$id | awk '{print \$2}' | tail -n +2)
    for pid in \$pids
    do
      path_score=\"proc/\$pid/oom_score\"
      path_score_adj=\"proc/\$pid/oom_score_adj\"
      if test -f \$path_score; then
        oom_score=\$(cat \$path_score)
        if test -f \$path_score_adj; then
          oom_score_adj=\$(cat \$path_score_adj)
          echo \"container: \$container, pid: \$pid, oom_score: \$oom_score, oom_score_adj: \$oom_score_adj\"
        else
          echo \"container: \$container, pid: \$pid, oom_score: \$oom_score, oom_score_adj: None\"
        fi
      else
        if test -f \$path_score_adj; then
          echo \"container: \$container, pid: \$pid, oom_score: None, oom_score_adj: \$oom_score_adj\"
        else
          echo \"container: \$container, pid: \$pid, oom_score: None, oom_score_adj: None\"
        fi
      fi
    done
  done
  "
)

kubectl node-shell $node -- bash -c "${shell_command[@]}"
