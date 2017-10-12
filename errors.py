__all__ = [
    "SslError",
    "SslCertificateError",
    "SslCertificateVerificationError",
    "SslCertificateInsecureError",
    "SslEofError"
]


class SslError(Exception):
    pass


class SslCertificateError(SslError):
    pass


class SslCertificateVerificationError(SslCertificateError):
    pass


class SslCertificateInsecureError(SslCertificateError):
    pass


class SslEofError(SslError):
    pass

