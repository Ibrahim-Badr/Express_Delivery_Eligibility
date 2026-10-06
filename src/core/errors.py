class DomainError(Exception):
    pass

class NotFoundError(DomainError):
    def __init__(self, message: str):
        self.message = message

class InvalidInputError(DomainError):
    def __init__(self, message: str):
        self.message = message

class ModelUnavailableError(DomainError):
    def __init__(self, message: str):
        self.message = message
