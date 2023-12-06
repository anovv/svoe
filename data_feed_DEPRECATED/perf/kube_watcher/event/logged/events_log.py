
class EventsLog:
    # Base class to store logged/parsed events and trigger callbacks
    def __init__(self, callbacks):
        self.callbacks = callbacks

    # Each subclass should implement it's own parsing logic
    def update_state(self, raw_event):
        raise ValueError('Not implemented')

    # Each subclass should implement it's own logging logic
    def _log_event_and_callback(self, logged_event):
        raise ValueError('Not implemented')