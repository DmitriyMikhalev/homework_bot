class ConnectApiError(Exception):
    """Failed to get API answer."""

    pass


class ResponseStatusError(Exception):
    """Response HTTP status is not 200."""

    pass
