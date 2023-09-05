import time
from typing import Any, Dict

from simulation.loop.loop import Loop

import ray

# TODO re blocking calls
# https://stackoverflow.com/questions/56556905/remote-calls-are-blocking-when-used-on-methods-in-an-actor-object

@ray.remote
class SimulationWorkerActor:

    def __init__(self):
        self.loop = None

    def run_loop(self, loop: Loop, split_id: int):
        # TODO check if there is already a running loop
        self.split_id = split_id
        self.loop = loop
        start = time.time()
        print(f'Started loop for split {split_id}')
        loop.run()
        self.run_loop_time = time.time() - start
        print(f'Finished loop for split {split_id} in {self.run_loop_time}s')

    # TODO make actor threaded, otherwise calling this won't work due to block from run_loop
    def interrupt_loop(self):
        self.loop.set_is_running(False)

    def get_run_stats(self) -> Dict:
        # TODO proper method on Portfolio class to get run stats
        return {
            'split_id': self.split_id,
            'run_loop_time ': self.run_loop_time,
            'state_snapshots': self.loop.execution_simulator.state_snapshots
        }

