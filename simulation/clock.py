class Clock:

    def __init__(self, start: float):
        self.now = start

    def advance(self, step: float):
        self.now += step