"""🗿• ESPHome IR Manager 🛠️ integration."""
import logging
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_ENTITY_ID
from homeassistant.helpers import entity_registry as er
from .const import DOMAIN
from .coordinator import ESPHomeRCCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.REMOTE, Platform.BUTTON, Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up from a config entry."""
    coordinator = ESPHomeRCCoordinator(hass, entry)
    await coordinator.async_init()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    # Register service if not already registered
    if not hass.services.has_service(DOMAIN, "report_code"):
        async def handle_report_code(call: ServiceCall):
            """Handle the report_code service call from ESPHome."""
            entity_id = call.data.get(CONF_ENTITY_ID)
            code = call.data.get("code")
            
            if not entity_id or not code:
                _LOGGER.error("Service report_code requires entity_id and code")
                return

            # Find the coordinator for this entity
            # We assume the entity_id passed is the REMOTE entity of the hub
            ent_reg = er.async_get(hass)
            entity_entry = ent_reg.async_get(entity_id)
            
            if not entity_entry or entity_entry.platform != DOMAIN:
                _LOGGER.error(f"Entity {entity_id} not found or not part of esphome_rc")
                return

            config_entry_id = entity_entry.config_entry_id
            coordinator = hass.data[DOMAIN].get(config_entry_id)

            if coordinator:
                await coordinator.async_receive_code(code)
            else:
                _LOGGER.error(f"Coordinator not found for entry {config_entry_id}")

        hass.services.async_register(DOMAIN, "report_code", handle_report_code)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)