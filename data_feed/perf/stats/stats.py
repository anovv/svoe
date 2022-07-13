import json

from perf.defines import DATA_FEED_CONTAINER


# class to collect statistics about estimation runs
class Stats:
    def __init__(self):
        self.stats = {}

    def add_metrics_to_stats(self, pod_name, metrics_results):
        if pod_name not in self.stats:
            self.stats[pod_name] = {}
        self.stats[pod_name]['metrics'] = metrics_results

    def add_all_df_events(self, pod_name, kube_watcher_state, estimation_state, scheduling_state):
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

        if pod_name not in self.stats:
            self.stats[pod_name] = {}
        self.stats[pod_name]['events'] = events

    def add_reschedules(self, pod_name, scheduling_state):
        if pod_name not in self.stats:
            self.stats[pod_name] = {}
        self.stats[pod_name]['reschedule_reasons'] = scheduling_state.get_reschedule_reasons(pod_name)

    def save(self):
        # TODO file per run?
        # path = f'resources-estimation-{datetime.datetime.now().strftime("%d-%m-%Y-%H:%M:%S")}.json'
        path = 'resources-estimation-out/resources-estimation.json'
        with open(path, 'w+') as outfile:
            json.dump(self.stats, outfile, indent=4, sort_keys=True)
        print(f'[Stats] Saved stats to {path}')