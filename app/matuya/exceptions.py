class MatuyaError(Exception):
    pass


class MatuyaRequestError(MatuyaError):
    pass


class MatuyaFormParseError(MatuyaError):
    pass


class MatuyaSubmitError(MatuyaError):
    pass
