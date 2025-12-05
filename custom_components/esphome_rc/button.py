"""Support for 🗿• ESPHome IR Manager 🛠️ Buttons."""
import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ESPHomeRCCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the 🗿• ESPHome IR Manager 🛠️ Button platform."""
    coordinator: ESPHomeRCCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    # Iterate over all stored devices and their commands
    for device_name, commands in coordinator.codes.items():
        for command_name, code in commands.items():
            entities.append(
                ESPHomeIRButton(coordinator, device_name, command_name, code)
            )
            
    async_add_entities(entities)

class ESPHomeIRButton(ButtonEntity):
    """Representation of a learned IR command as a button."""

    def __init__(self, coordinator: ESPHomeRCCoordinator, device_name, command_name, code):
        """Initialize the button."""
        self._coordinator = coordinator
        self._device_name = device_name
        self._command_name = command_name
        self._code = code
        
        # Unique ID combining Hub ID, Sub-device Name, and Command Name
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{device_name}_{command_name}"
        self._attr_name = command_name
        self._attr_should_poll = False

    @property
    def device_info(self):
        """Return information to link this entity to the Sub-device."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._coordinator.entry.entry_id}_{self._device_name}")},
            name=self._device_name,
            via_device=(DOMAIN, self._coordinator.entry.entry_id), # Links to the main Hub
            manufacturer="ESPHome (Virtual)",
            model="IR Sub-device",
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._coordinator.send_button(self._code)