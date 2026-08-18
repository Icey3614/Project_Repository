class BizError(Exception):
    """业务异常：message 为用户可见信息，code 为业务码，status_code 为 HTTP 状态。"""

    def __init__(self, message: str, code: int = 4000, status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(BizError):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, code=404, status_code=404)


class PermissionDenied(BizError):
    def __init__(self, message: str = "无权限执行此操作"):
        super().__init__(message, code=403, status_code=403)
