class CH9329Error(Exception):
    pass


class InvalidModifier(CH9329Error):
    pass


class InvalidKey(CH9329Error):
    pass


class TooManyKeysError(CH9329Error):
    pass


class ProtocolError(CH9329Error):
    pass
