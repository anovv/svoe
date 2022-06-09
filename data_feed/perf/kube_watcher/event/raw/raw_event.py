
class RawEvent:
    def __init__(self, raw_event):
        self.type = raw_event['type']
        self.resource_version = raw_event['object'].metadata.resource_version
