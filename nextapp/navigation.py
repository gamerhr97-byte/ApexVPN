"""Small bounded history shared by native back/forward buttons and settings."""


class History:
    def __init__(self):
        self.items = [(0, None)]
        self.index = 0

    def push(self, state):
        if self.items[self.index] == state:
            return
        self.items[self.index + 1:] = [state]
        self.items = self.items[-80:]
        self.index = len(self.items) - 1

    def step(self, delta):
        index = self.index + delta
        if not 0 <= index < len(self.items):
            return None
        self.index = index
        return self.items[index]
