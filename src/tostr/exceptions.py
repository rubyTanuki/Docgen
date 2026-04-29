
class ToasterError(Exception):
    """Base exception for all Toaster domain errors."""
    pass

class StructNotFoundError(ToasterError):
    pass

class APIKeyError(ToasterError):
    pass

class ResolveError(ToasterError):
    pass

class LanguageNotSupportedError(ToasterError):
    pass

class TargetFileNotFoundError(ToasterError):
    pass

class DatabaseNotFoundError(ToasterError):
    pass