"""Support for 🗿• ESPHome IR Manager 🛠️ Hub."""
import logging
import asyncio
from homeassistant.components.remote import (
    ATTR_COMMAND,
    ATTR_DEVICE,
    ATTR_DELAY_SECS,
    ATTR_NUM_REPEATS,
    RemoteEntity,
    RemoteEntityFeature,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntryType

from .const import DOMAIN
from .coordinator import ESPHomeRCCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the 🗿• ESPHome IR Manager 🛠️ Remote entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ESPHomeRCHub(coordinator)])

class ESPHomeRCHub(RemoteEntity):
    """The main Hub Entity for the ESPHome IR Blaster."""
    
    def __init__(self, coordinator: ESPHomeRCCoordinator):
        self._coordinator = coordinator
        self._attr_name = coordinator.device_name
        self._attr_unique_id = f"{coordinator.entry.entry_id}_hub"
        
    @property
    def should_poll(self):
        return False

    @property
    def available(self):
        return True

    @property
    def is_on(self):
        return True

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._coordinator.entry.entry_id)},
            name=self._coordinator.device_name,
            manufacturer="ESPHome",
            model="IR Hub Custom",
            entry_type=DeviceEntryType.SERVICE,
        )
    
    @property
    def extra_state_attributes(self):
        return {
            "linked_service": self._coordinator.service_string,
            "sub_devices_count": len(self._coordinator.codes)
        }

    @property
    def supported_features(self):
        return RemoteEntityFeature.LEARN_COMMAND | RemoteEntityFeature.DELETE_COMMAND

    async def async_send_command(self, command, **kwargs):
        """Send a list of commands."""
        device = kwargs.get(ATTR_DEVICE, None)
        repeat = kwargs.get(ATTR_NUM_REPEATS, 1)
        repeat_delay = kwargs.get(ATTR_DELAY_SECS, 0.5)
        
        for n in range(repeat):
            for cmd in command:
                code_to_send = cmd
                if device:
                    codes = self._coordinator.codes.get(device)
                    if not codes:
                        _LOGGER.warning(f"Device '{device}' not found.")
                        continue
                    if cmd not in codes:
                        _LOGGER.warning(f"Command '{cmd}' not found for device '{device}'.")
                        continue
                    code_to_send = codes[cmd]
                
                await self._coordinator.send_button(code_to_send)
                
                if repeat_delay > 0:
                    await asyncio.sleep(repeat_delay)

    async def async_learn_command(self, **kwargs):
        """Standard service learn command."""
        device = kwargs.get(ATTR_DEVICE)
        commands = kwargs.get(ATTR_COMMAND)
        
        if not device or not commands:
            raise ValueError("Device and Command are required.")
            
        command_name = commands[0]
        self._coordinator.add_subdevice(device)
        
        try:
            self.hass.components.persistent_notification.create(
                f"Learning mode active for {device} -> {command_name}. Please press button.",
                title="🗿• ESPHome IR Manager 🛠️"
            )
            
            code = await self._coordinator.learn_command(timeout=30)
            self._coordinator.codes[device][command_name] = code
            await self._coordinator.async_save_storage()
            
            self.hass.components.persistent_notification.create(
                f"Code successfully learned!", title="🗿• ESPHome IR Manager 🛠️"
            )
                 
        except Exception as e:
            raise HomeAssistantError(f"Failed to learn: {e}")

    async def async_delete_command(self, **kwargs):
        device = kwargs.get(ATTR_DEVICE)
        commands = kwargs.get(ATTR_COMMAND)
        if not device or not commands: return
        for cmd in commands:
            self._coordinator.delete_command(device, cmd)
        await self._coordinator.async_save_storage()