import json
import datetime
import os

from perf.defines import DATA_FEED_CONTAINER
from perf.kube_api.utils import get_payload_config, get_payload_hash


# class to collect statistics about estimation runs
class Stats:
    def __init__(self):
        self.stats = {}
        self.logs = {}

    def add_pod_info(self, payload, pod_name):
        payload_config = get_payload_config(payload)
        payload_hash = get_payload_hash(payload)
        if payload_hash not in self.stats:
            self.stats[payload_hash] = {}
        self.stats[payload_hash]['pod_name'] = pod_name
        self.stats[payload_hash]['payload_config'] = payload_config
        if 'symbol_distribution' in payload['svoe']:
            self.stats[payload_hash]['symbol_distribution'] = payload['svoe']['symbol_distribution']
        else:
            self.stats[payload_hash]['symbol_distribution'] = 'UNKNOWN_SYMBOL_DISTRIBUTION'

    def add_metrics_to_stats(self, payload, metrics_results):
        if metrics_results is None:
            return
        payload_hash = get_payload_hash(payload)
        if payload_hash not in self.stats:
            self.stats[payload_hash] = {}
        self.stats[payload_hash]['metrics'] = metrics_results

    def add_all_df_events(self, payload, pod_name, kube_watcher_state, estimation_state, scheduling_state):
        events = []
        if pod_name in kube_watcher_state.event_queues_per_pod:
            events.extend(kube_watcher_state.event_queues_per_pod[pod_name].queue)
        if pod_name in estimation_state.phase_events_per_pod:
            events.extend(estimation_state.phase_events_per_pod[pod_name])
        if pod_name in estimation_state.result_events_per_pod:
            events.extend(estimation_state.result_events_per_pod[pod_name])
        if pod_name in scheduling_state.phase_events_per_pod:
            events.extend(scheduling_state.phase_events_per_pod[pod_name])
        if pod_name in scheduling_state.result_events_per_pod:
            events.extend(scheduling_state.result_events_per_pod[pod_name])
        events.sort(key=lambda event: event.local_time)
        events = list(
            filter(lambda event: event.container_name is None or event.container_name == DATA_FEED_CONTAINER, events))
        events = list(map(lambda event: str(event), events))

        payload_hash = get_payload_hash(payload)
        if payload_hash not in self.stats:
            self.stats[payload_hash] = {}
        self.stats[payload_hash]['events'] = events

    def add_final_result(self, payload, pod_name, estimation_state):
        payload_hash = get_payload_hash(payload)
        if payload_hash not in self.stats:
            self.stats[payload_hash] = {}
        self.stats[payload_hash]['final_result'] = estimation_state.get_last_result_event_type(pod_name)

    def add_reschedules(self, payload, pod_name, scheduling_state):
        payload_hash = get_payload_hash(payload)
        if payload_hash not in self.stats:
            self.stats[payload_hash] = {}
        self.stats[payload_hash]['reschedule_reasons'] = scheduling_state.get_reschedule_reasons(pod_name)

    def should_fetch_df_logs(self, payload, pod_name):
        payload_config = get_payload_config(payload)
        exchange, instrument_type = self._get_logs_key(pod_name, payload_config)
        return exchange not in self.logs \
               or instrument_type not in self.logs[exchange] \
               or len(self.logs[exchange][instrument_type]) < 2 # max 2 log files per exchange+instrument_type

    def add_df_logs(self, payload, pod_name, logs):
        payload_config = get_payload_config(payload)
        payload_hash = get_payload_hash(payload)
        exchange, instrument_type = self._get_logs_key(pod_name, payload_config)
        log_file_local_name = pod_name + '.log'
        if exchange not in self.logs:
            self.logs[exchange] = {}
        if instrument_type not in self.logs[exchange]:
            self.logs[exchange][instrument_type] = [[log_file_local_name, logs]]
        else:
            # make sure no duplicates, if duplicated, update to latest logs version
            duplicate = False
            for el in self.logs[exchange][instrument_type]:
                if el[0] == log_file_local_name:
                    duplicate = True
                    el[1] = logs

            if not duplicate:
                self.logs[exchange][instrument_type].append([log_file_local_name, logs])

        # add reference to stats
        if payload_hash not in self.stats:
            self.stats[payload_hash] = {}
        if 'log_files' not in self.stats[payload_hash]:
            self.stats[payload_hash]['log_files'] = [log_file_local_name]
        else:
            if log_file_local_name not in self.stats[payload_hash]['log_files']:
                self.stats[payload_hash]['log_files'].append(log_file_local_name)

    def _get_logs_key(self, pod_name, payload_config):
        # hack, we should fetch instrument type from config
        instrument_type = None
        for it in ['perpetual', 'spot', 'option', 'futures']:
            if it in pod_name:
                instrument_type = it
                break
        exchange = list(payload_config.keys())[0]
        return exchange, instrument_type

    def save(self):
        if len(self.stats) == 0:
            print('[Stats] Stats are empty, not saving')
            return
        # TODO file per run?
        # path = f'resources-estimation-{datetime.datetime.now().strftime("%d-%m-%Y-%H:%M:%S")}.json'
        path_prefix = f'resources-estimation-out/{datetime.datetime.now().strftime("%d-%m-%Y-%H-%M-%S")}/'
        path_stats = path_prefix + 'resources-estimation.json'
        # save stats
        os.makedirs(os.path.dirname(path_stats), exist_ok=True)
        with open(path_stats, 'w+') as outfile:
            json.dump(self.stats, outfile, indent=4, sort_keys=True)
        print(f'[Stats] Saved stats to {path_stats}')
        # save logs
        for exchange in self.logs:
            for it in self.logs[exchange]:
                for log_file_local_name, logs in self.logs[exchange][it]:
                    path_log = path_prefix + 'logs/' + log_file_local_name
                    os.makedirs(os.path.dirname(path_log), exist_ok=True)
                    with open(path_log, 'w+') as outfile:
                        outfile.write(logs)
                    print(f'[Stats] Saved logs to {path_log}')
