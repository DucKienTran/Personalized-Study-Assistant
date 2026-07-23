from app.exceptions.base import InternalServerError


class ClassifierParseError(InternalServerError):
    """
    Raised when the AI classifier returns
    invalid or unparseable output.
    """

    def __init__(
        self,
        message: str = "Failed to parse AI classification output.",
    ):
        super().__init__(message)
