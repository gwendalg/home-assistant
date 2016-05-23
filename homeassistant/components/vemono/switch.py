"""
Support for VeMono switches.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.vemono/
"""
import logging

from homeassistant.components import vemono
from homeassistant.components.switch import SwitchEntity

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the vemono platform for switches."""
    if not vemono.DEVICES:
        return
    devs = []
    for host in vemono.DEVICES:
        device = vemono.DEVICES[host]
        for plug in range(device.max_plug):
            devs.append(VeMonoSwitch(device, plug))

    add_entities(devs)


class VeMonoSwitch(vemono.VeMonoDeviceEntity, SwitchEntity):
    """Representation of the value of a VeMono Switch child node."""

    @property
    def is_on(self):
        """Return True if switch is on."""
        return self.state_data("state") == "ON"

    def turn_on(self):
        """Turn the switch on."""
        self.set_state("ON")

    def turn_off(self):
        """Turn the switch off."""
        self.set_state("OFF")
