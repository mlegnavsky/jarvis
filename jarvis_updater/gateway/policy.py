class APIError(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code
