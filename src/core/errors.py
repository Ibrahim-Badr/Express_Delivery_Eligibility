class DomainError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class NotFoundError(DomainError):
    pass

class InvalidInputError(DomainError):
    pass

class ModelUnavailableError(DomainError):
    pass
