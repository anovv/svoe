import datetime
import time
import threading

from perf.kube_watcher.event.logged.pod_logged_event import PodLoggedEvent


# base class for state which is made of phase->result steps
class PhaseResultState:
    def __init__(self):
        self.phase_events_per_pod = {}
        self.result_events_per_pod = {}
        self.wait_event_per_pod = {}

    def get_interrupts(self):
        raise ValueError('Not implemented')

    def is_interrupted(self, pod_name):
        return self.get_last_result_event(pod_name) in self.get_interrupts()

    def get_last_result_event(self, pod_name):
        if pod_name in self.result_events_per_pod:
            return self.result_events_per_pod[pod_name][-1]
        return None

    def get_last_result_event_type(self, pod_name):
        event = self.get_last_result_event(pod_name)
        if event is None:
            return None
        return event.type

    def has_result_type(self, pod_name, result_type):
        if pod_name not in self.result_events_per_pod:
            return False
        for result_event in self.result_events_per_pod[pod_name]:
            if result_event.type == result_type:
                return True
        return False

    def add_result_event(self, pod_name, estimation_result_event_type):
        event = PodLoggedEvent(
            estimation_result_event_type,
            pod_name, container_name=None,
            data=None,
            cluster_time=None, local_time=datetime.datetime.now(),
            raw_event=None
        )
        if pod_name in self.result_events_per_pod:
            self.result_events_per_pod[pod_name].append(event)
        else:
            self.result_events_per_pod[pod_name] = [event]

        # TODO debug
        # print(event)

    def get_last_phase_event(self, pod_name):
        if pod_name in self.phase_events_per_pod:
            return self.phase_events_per_pod[pod_name][-1]
        return None

    def get_last_phase_event_type(self, pod_name):
        event = self.get_last_phase_event(pod_name)
        if event is None:
            return None
        return event.type

    def add_phase_event(self, pod_name, estimation_phase_event_type):
        event = PodLoggedEvent(
            estimation_phase_event_type,
            pod_name, container_name=None,
            data=None,
            cluster_time=None, local_time=datetime.datetime.now(),
            raw_event=None
        )
        if pod_name in self.phase_events_per_pod:
            self.phase_events_per_pod[pod_name].append(event)
        else:
            self.phase_events_per_pod[pod_name] = [event]

        # TODO debug
        # TODO debug
        # print(event)

    def wake_event(self, pod_name):
        self.wait_event_per_pod[pod_name].set()
        # TODO use locks instead
        time.sleep(0.01) # to avoid race between kube watcher threads and estimator thread

    def wait_event(self, pod_name, timeout):
        # TODO check if the previous event is awaited/reset
        self.wait_event_per_pod[pod_name] = threading.Event()
        return self.wait_event_per_pod[pod_name].wait(timeout=timeout)

    def clean_phase_result_events(self, pod_name):
        if pod_name in self.result_events_per_pod:
            del self.result_events_per_pod[pod_name]
        if pod_name in self.phase_events_per_pod:
            del self.phase_events_per_pod[pod_name]
