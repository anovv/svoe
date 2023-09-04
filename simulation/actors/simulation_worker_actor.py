from typing import Any

from simulation.loop.loop import Loop

import ray


@ray.remote
class SimulationWorkerActor:

    def __init__(self):
        self.loop = None

    def run_loop(self, loop: Loop):
        # TODO check if there is already a running loop
        self.loop = loop
        loop.run()

    def interrupt_loop(self):
        self.loop.set_is_running(False)

    def get_run_stats(self) -> Any:
        # TODO proper method on Portfolio class to get run stats
        return self.loop.portfolio.state_snapshots

