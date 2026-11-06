"""Fresh complete A and AAAA resolution with explicit DNS protocol lifetimes."""

import asyncio
import re
import time
import dns.exception
import dns.asyncresolver

DNS_TIMEOUT = 2.0
MAX_DNS_ADDRESSES = 32


class PreflightError(ValueError):
    """A safe operator-facing publication check failure."""


def resolve_host(host, timeout=DNS_TIMEOUT):
    """Never return partial success if either address-family lookup fails."""
    if not isinstance(host, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,251}[A-Za-z0-9]', host):
        raise PreflightError("Use an existing public DNS hostname")
    timeout = min(timeout, DNS_TIMEOUT)
    if timeout <= 0:
        raise PreflightError("DNS lookup timed out; check both A and AAAA records")

    async def complete():
        resolver = dns.asyncresolver.Resolver()
        resolver.cache = None
        deadline = time.monotonic() + timeout
        addresses = set()
        for family in ('A', 'AAAA'):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise asyncio.TimeoutError()
            answer = await resolver.resolve(host, family, lifetime=remaining, search=False, raise_on_no_answer=False)
            for record in answer:
                addresses.add(record.address)
                if len(addresses) > MAX_DNS_ADDRESSES:
                    raise PreflightError("DNS returned too many addresses; check the hostname records")
        return sorted(addresses)

    async def bounded():
        # The outer cancellation also bounds resolver retry backoff sleeps.
        # dnspython closes its async sockets when this task is cancelled.
        return await asyncio.wait_for(complete(), timeout=timeout)

    try:
        return asyncio.run(bounded())
    except (asyncio.TimeoutError, dns.exception.Timeout):
        raise PreflightError("DNS lookup timed out; check both A and AAAA records") from None
    except dns.exception.DNSException:
        raise PreflightError("DNS lookup failed; check the existing A and AAAA records") from None
