

class Callback:
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.estimation_state = scheduler.estimation_state
        self.scheduling_state = scheduler.scheduling_state

    def callback(self, event):
        raise ValueError('Not implemented')
