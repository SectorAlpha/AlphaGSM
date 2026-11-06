"""TLS settings for the outbound Sector Alpha agent."""

import ssl


def client_context():
    """Verified HTTPS context that refuses TLS 1.0 and 1.1."""
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    return context
