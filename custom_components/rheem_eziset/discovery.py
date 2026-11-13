"""Discovery of Rheem EziSET devices using the UDP broadcast which the official app uses."""
from __future__ import annotations

import asyncio

from homeassistant.components import network
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac

from .const import DISCOVERY_MESSAGE, DISCOVERY_PORT, DISCOVERY_TIMEOUT, DOMAIN, LOGGER


class _DiscoveryProtocol(asyncio.DatagramProtocol):
    """Collect the replies to a discovery request."""

    def __init__(self) -> None:
        """Initialise with no devices found."""
        self.devices: dict[str, str] = {}

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Decode a reply. Bytes 0-5 are the MAC address and bytes 7-10 are the IPv4 address."""
        if addr[1] != DISCOVERY_PORT or len(data) < 11:
            return
        mac = format_mac(data[0:6].hex())
        self.devices[mac] = ".".join(str(octet) for octet in data[7:11])

    def error_received(self, exc: Exception) -> None:
        """Ignore errors, discovery is best effort."""
        LOGGER.debug("%s - discovery error: %s", DOMAIN, exc)


async def async_discover(hass: HomeAssistant, host: str | None = None, timeout: float = DISCOVERY_TIMEOUT) -> dict[str, str]:
    """
    Return the devices which answer a discovery request as a dict of MAC address to IPv4 address.

    If host is provided, only that host is asked. Otherwise the request is broadcast on every enabled adapter.
    Devices only reply to port 2015, so discovery is not possible if something else is already using that port.
    """
    if host is not None:
        targets = [host]
    else:
        targets = [str(address) for address in await network.async_get_ipv4_broadcast_addresses(hass)]

    protocol = _DiscoveryProtocol()
    try:
        transport, _ = await hass.loop.create_datagram_endpoint(
            lambda: protocol,
            local_addr=("0.0.0.0", DISCOVERY_PORT),
            allow_broadcast=True,
        )
    except OSError as err:
        LOGGER.debug("%s - could not open port %s for discovery: %s", DOMAIN, DISCOVERY_PORT, err)
        return {}

    try:
        for target in targets:
            try:
                transport.sendto(DISCOVERY_MESSAGE, (target, DISCOVERY_PORT))
            except OSError as err:
                LOGGER.debug("%s - could not send discovery request to %s: %s", DOMAIN, target, err)
        await asyncio.sleep(timeout)
    finally:
        transport.close()

    return protocol.devices
