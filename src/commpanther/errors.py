class AppError(Exception):
    def __init__(self, code, user_message, retryable=False, details=None):
        self.code = code
        self.user_message = user_message
        self.retryable = retryable
        self.details = details or {}
        super().__init__(user_message)