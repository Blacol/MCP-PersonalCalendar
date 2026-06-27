class TimeZoneInfoError(Exception):
    """
    时区数据错误时抛出异常
    """
    def __init__(self,message):
        self.message = message
    def __str__(self):
        return self.message
class ItemNumberException(Exception):
    """
    数据数量不正确时抛出异常
    """
    def __init__(self,message):
        self.message = message
    def __str__(self):
        return self.message
class NoneClientError(Exception):
    """
    数据数量不正确时抛出异常
    """
    def __init__(self,message):
        self.message = message
    def __str__(self):
        return self.message