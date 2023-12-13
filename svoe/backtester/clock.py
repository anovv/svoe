class Clock:

    def __init__(self, start: float):
        self.now = start

    def set(self, time: float):
        self.now = time