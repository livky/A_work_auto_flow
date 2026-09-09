"""所有记忆入口共享的预期错误，避免 CLI 把保存失败包装成成功。"""

EXIT_CODES = {
    "INVALID_ARGUMENT": 2, "INVALID_SCHEMA": 2, "NOT_FOUND": 2,
    "UNRESOLVED_REFERENCE": 2, "ACCESS_DENIED": 4, "UNSAFE_PATH": 4,
    "VERSION_CONFLICT": 5, "STALE_BASIS": 5, "IDEMPOTENCY_CONFLICT": 5,
    "LOCKED": 6, "INTEGRITY_ERROR": 7, "STORAGE_ERROR": 8,
    "INDEX_PENDING": 3, "EVIDENCE_INELIGIBLE": 9, "INVALID_TRANSITION": 9,
    "CAPABILITY_UNAVAILABLE": 10,
}


class MemoryError(Exception):
    """业务拒绝携带可解析定位；details 不应包含未获准来源的正文。"""

    def __init__(self, code, message, details=None, errors=None):
        super().__init__(message)
        self.code = code
        self.details = details or {}
        self.errors = errors or []

    @property
    def exit_code(self):
        return EXIT_CODES.get(self.code, 8)

    def as_dict(self):
        return {"code": self.code, "message": str(self),
                "details": self.details, "errors": self.errors}
