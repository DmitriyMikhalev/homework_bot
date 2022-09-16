class APIConnectionError(Exception):
    """Failed to get API answer."""

    pass


class ResponseError(Exception):
    """Response Error."""

    pass


class ResponseIncorrectError(ResponseError):
    """Response has incorrect format."""

    pass


class ResponseStatusError(ResponseError):
    """Response HTTP status is not 200."""

    pass
