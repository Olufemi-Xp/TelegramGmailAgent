import ipaddress
import socket
from urllib.parse import urlparse
from app.logging_config import get_logger

logger = get_logger(__name__)

BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "::1",
    "metadata.google.internal",
    "instance-data",
}


def is_safe_url(url: str) -> tuple[bool, str]:
    """Validates URL for security:
    - Must be http or https
    - Hostname must not resolve to loopback, private, link-local, or cloud metadata addresses
    Returns (is_safe, error_reason)
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme.lower() not in ("http", "https"):
            return False, f"Unsupported URL scheme: {parsed.scheme}. Only HTTP/HTTPS are allowed."

        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid URL: Missing hostname."

        if hostname.lower() in BLOCKED_HOSTNAMES:
            return False, f"Access to {hostname} is blocked for security."

        # Check if the hostname itself is directly an IP literal
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
                return False, f"Access to private/internal IP address {ip} is blocked."
            return True, ""
        except ValueError:
            pass

        # Resolve hostname to IPv4/IPv6 addresses
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                sockaddr = item[4]
                ip_str = sockaddr[0]
                ip = ipaddress.ip_address(ip_str)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
                    return False, f"Resolved IP {ip_str} for {hostname} belongs to a private/internal network."
        except socket.gaierror as e:
            return False, f"DNS resolution failed for hostname '{hostname}': {e}"

        return True, ""

    except Exception as e:
        logger.warning(f"URL safety check failed unexpectedly for {url}: {e}")
        return False, f"Malformed URL or safety verification error: {str(e)}"
