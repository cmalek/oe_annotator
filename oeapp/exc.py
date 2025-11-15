class DoesNotExist(Exception):  # noqa: N818
    """Exception raised when a resource does not exist."""

    def __init__(self, resource_type: str, resource_id: int | str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f'{resource_type} with ID "{resource_id!s}" does not exist')


class AlreadyExists(Exception):  # noqa: N818
    """Exception raised when a resource already exists."""

    def __init__(self, resource_type: str, resource_id: int | str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f'{resource_type} with ID "{resource_id!s}" already exists')
