"""Coordinator for 🗿• ESPHome IR Manager 🛠️."""
import logging
import asyncio
import json
import ast
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.storage import Store
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import CONF_NAME, Platform
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr

from .const import (
    DOMAIN,
    CONF_ESPHOME_SERVICE,
    CODE_STORAGE_VERSION,
    CODE_STORAGE_CODES,
)

_LOGGER = logging.getLogger(__name__)

class ESPHomeRCCoordinator:
    """Class to manage the ESPHome IR Device and Storage."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        
        self.config = entry.data
        self._name = self.config.get(CONF_NAME)
        self._service_string = self.config.get(CONF_ESPHOME_SERVICE)
        
        try:
            self._service_domain, self._service_name = self._service_string.split('.')
        except ValueError:
            self._service_domain = "esphome"
            self._service_name = self._service_string

        self._storage = None
        self._codes = {} 
        
        # Sensor state
        self._last_received_code = "Ready to receive..."
        self._sensor_update_callbacks = []
        self._reset_timer_handle = None
        
        # Learning control
        self._learn_future = None

    async def async_init(self):
        """Initialize the coordinator."""
        await self._async_load_storage_files()

    @property
    def codes(self):
        return self._codes

    @property
    def device_name(self):
        return self._name
    
    @property
    def last_received_code(self):
        return self._last_received_code

    @property
    def service_string(self):
        return self._service_string

    def register_sensor_callback(self, callback_func):
        self._sensor_update_callbacks.append(callback_func)

    def _update_sensor_listeners(self):
        for cb in self._sensor_update_callbacks:
            cb()

    def _lookup_code_name(self, code):
        """Find best matching command name for received code."""
        # 1. Prepare search data
        search_str = str(code).strip()
        received_list = None
        
        # Normalize list format if possible
        try:
            if search_str.startswith("["):
                loaded = json.loads(search_str)
                search_str = json.dumps(loaded) # normalized string
                received_list = loaded
        except:
            pass

        # 2. Phase 1: Check for EXACT matches first
        for device, commands in self._codes.items():
            for cmd_name, cmd_code in commands.items():
                stored_str = str(cmd_code).strip()
                # Normalize stored too
                try:
                    if stored_str.startswith("["):
                        stored_str = json.dumps(json.loads(stored_str))
                except:
                    pass
                
                if stored_str == search_str:
                    return f"{device}: {cmd_name}"

        # 3. Phase 2: Find BEST fuzzy match (lowest error)
        if received_list:
            best_match_name = None
            lowest_error_avg = 0.25 # Start with max tolerance (25%)

            for device, commands in self._codes.items():
                for cmd_name, cmd_code in commands.items():
                    # Parse stored code to list
                    stored_list = None
                    try:
                        s_code = str(cmd_code).strip()
                        if s_code.startswith("["):
                            stored_list = json.loads(s_code)
                    except:
                        continue

                    if stored_list and len(received_list) == len(stored_list):
                        # Calculate error
                        total_error = 0
                        valid_candidate = True
                        
                        for i, r_val in enumerate(received_list):
                            s_val = stored_list[i]
                            # Handle zero division / exact zero
                            if s_val == 0:
                                if r_val != 0: 
                                    valid_candidate = False; break
                                continue
                            
                            diff = abs(r_val - s_val) / abs(s_val)
                            if diff > 0.25: # Reject if any single pulse is too far off
                                valid_candidate = False; break
                            total_error += diff
                        
                        if valid_candidate:
                            avg_error = total_error / len(received_list)
                            # If this match is better than previous best, keep it
                            if avg_error < lowest_error_avg:
                                lowest_error_avg = avg_error
                                best_match_name = f"{device}: {cmd_name}"
            
            if best_match_name:
                return best_match_name

        # No match found
        return str(code)

    # --- Inbound Data (From ESPHome) ---

    async def async_receive_code(self, code):
        """Called by the service when ESPHome sends a code."""
        _LOGGER.debug(f"Received code from ESPHome: {code}")
        
        if self._reset_timer_handle:
            self._reset_timer_handle.cancel()
            self._reset_timer_handle = None

        # Resolve name
        display_text = self._lookup_code_name(code)
        self._last_received_code = display_text
        self._update_sensor_listeners()
            
        # Resolve learning future
        if self._learn_future and not self._learn_future.done():
            self._learn_future.set_result(code)
            
        # Reset after 5s
        self._reset_timer_handle = self.hass.loop.call_later(5, self._reset_sensor_state)

    @callback
    def _reset_sensor_state(self):
        self._last_received_code = "Ready to receive..."
        self._update_sensor_listeners()
        self._reset_timer_handle = None

    # --- Storage & Management ---

    async def _async_load_storage_files(self):
        if not self._storage:
            self._storage = Store(self.hass, CODE_STORAGE_VERSION, CODE_STORAGE_CODES)
        data = await self._storage.async_load()
        if data:
            self._codes.update(data)

    async def async_save_storage(self):
        if self._storage:
            await self._storage.async_save(self._codes)

    def add_subdevice(self, name):
        if name not in self._codes:
            self._codes[name] = {}
            return True
        return False

    def remove_subdevice(self, name):
        """Remove a subdevice, its entities, and its device entry."""
        if name in self._codes:
            del self._codes[name]
            
            ent_reg = er.async_get(self.hass)
            dev_reg = dr.async_get(self.hass)
            
            # Find the Device Entry
            # Identifier defined in button.py: (DOMAIN, f"{self.entry.entry_id}_{name}")
            device_identifier = (DOMAIN, f"{self.entry.entry_id}_{name}")
            device = dev_reg.async_get_device(identifiers={device_identifier})
            
            if device:
                # Remove all entities linked to this device
                entries_to_remove = [
                    entry.entity_id 
                    for entry in ent_reg.entities.values() 
                    if entry.device_id == device.id
                ]
                
                for entity_id in entries_to_remove:
                    ent_reg.async_remove(entity_id)
                
                # Remove the device itself
                dev_reg.async_remove_device(device.id)
                _LOGGER.debug(f"Removed device and entities for {name}")
            else:
                # Fallback: Try to clean up by unique_id if device wasn't found (legacy/orphan check)
                entries_to_remove = []
                prefix = f"{self.entry.entry_id}_{name}_"
                for entity in ent_reg.entities.values():
                    if entity.config_entry_id == self.entry.entry_id:
                        if entity.unique_id.startswith(prefix):
                            entries_to_remove.append(entity.entity_id)
                
                for entity_id in entries_to_remove:
                    ent_reg.async_remove(entity_id)

            return True
        return False

    def delete_command(self, device_name, command_name):
        if device_name in self._codes and command_name in self._codes[device_name]:
            del self._codes[device_name][command_name]
            
            ent_reg = er.async_get(self.hass)
            unique_id = f"{self.entry.entry_id}_{device_name}_{command_name}"
            entity_id = ent_reg.async_get_entity_id(Platform.BUTTON, DOMAIN, unique_id)
            if entity_id:
                ent_reg.async_remove(entity_id)
                
            return True
        return False

    # --- Outbound Operations ---

    async def learn_command(self, timeout=30):
        if self._learn_future and not self._learn_future.done():
             self._learn_future.cancel()

        self._learn_future = asyncio.get_running_loop().create_future()
        
        try:
            code = await asyncio.wait_for(self._learn_future, timeout=timeout)
            return code
        except asyncio.TimeoutError:
            self._learn_future = None
            raise TimeoutError("No signal received.")
        except asyncio.CancelledError:
            self._learn_future = None
            raise
        finally:
            self._learn_future = None

    async def send_button(self, code_data):
        try:
            payload = code_data
            if isinstance(code_data, str):
                code_data = code_data.strip()
                if code_data.startswith("[") and code_data.endswith("]"):
                    try:
                        payload = json.loads(code_data)
                    except (json.JSONDecodeError, ValueError):
                        try:
                            payload = ast.literal_eval(code_data)
                        except:
                            pass
            
            await self.hass.services.async_call(
                self._service_domain,
                self._service_name,
                {"command": payload},
                blocking=True
            )
        except Exception as e:
             _LOGGER.error("Send error: %s", e)
             raise HomeAssistantError(f"Failed to call ESPHome service: {e}")