

class Callback:
    def __init__(self, estimation_state, scheduling_state):
        self.estimation_state = estimation_state
        self.scheduling_state = scheduling_state

    def callback(self, event):
        raise ValueError('Not implemented')