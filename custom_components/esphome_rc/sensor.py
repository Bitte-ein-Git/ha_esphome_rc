"""Support for 🗿• ESPHome IR Manager 🛠️ Last Code Sensor."""
import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ESPHomeRCCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the 🗿• ESPHome IR Manager 🛠️ Sensor platform."""
    coordinator: ESPHomeRCCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ESPHomeLastCodeSensor(coordinator)])

class ESPHomeLastCodeSensor(SensorEntity):
    """Sensor that displays the last received IR code."""

    def __init__(self, coordinator: ESPHomeRCCoordinator):
        self._coordinator = coordinator
        self._attr_name = "IR Code Receiver"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_ir_receiver"
        self._attr_icon = "mdi:remote"
        self._attr_native_value = coordinator.last_received_code

    async def async_added_to_hass(self):
        """Register callbacks."""
        self._coordinator.register_sensor_callback(self._update_state)

    @callback
    def _update_state(self):
        """Update the sensor state from coordinator."""
        self._attr_native_value = self._coordinator.last_received_code
        self.schedule_update_ha_state()

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._coordinator.entry.entry_id)},
            name=self._coordinator.device_name,
            manufacturer="ESPHome",
            model="ESPHome IR-Remote Manager",
        )