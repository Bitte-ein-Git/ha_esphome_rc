"""Config flow for the 🗿• ESPHome IR Manager 🛠️ integration."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_NAME

from .const import DOMAIN, DEFAULT_FRIENDLY_NAME, CONF_ESPHOME_SERVICE

_LOGGER = logging.getLogger(__name__)

class ESPHomeRCConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for 🗿• ESPHome IR Manager 🛠️."""

    VERSION = 1

    def __init__(self):
        self.data = {}

    @staticmethod
    @callback
    def async_get_options_flow(entry):
        return ESPHomeRCOptionsFlow(entry)
    
    async def async_step_user(self, user_input=None):
        """Step 1: Input details."""
        errors = {}
        if user_input is not None:
            self.data = user_input
            if "." not in user_input[CONF_ESPHOME_SERVICE]:
                errors["base"] = "invalid_service_format"
            else:
                await self.async_set_unique_id(user_input[CONF_ESPHOME_SERVICE])
                self._abort_if_unique_id_configured()
                return await self.async_step_yaml_info()

        schema = vol.Schema({
            vol.Required(CONF_NAME, default=DEFAULT_FRIENDLY_NAME): cv.string,
            vol.Required(CONF_ESPHOME_SERVICE, default="esphome.ir_blaster_send_raw_command"): cv.string,
        })
        return self.async_show_form(step_id="user", errors=errors, data_schema=schema)

    async def async_step_yaml_info(self, user_input=None):
        """Step 2: Show YAML to user."""
        if user_input is not None:
            return self.async_create_entry(title=self.data[CONF_NAME], data=self.data)

        slug_name = self.data[CONF_NAME].lower().replace(" ", "_")
        predicted_entity_id = f"remote.{slug_name}"
        yaml_code = self._get_yaml_code(predicted_entity_id)
        
        return self.async_show_form(
            step_id="yaml_info", 
            description_placeholders={"yaml": yaml_code},
            data_schema=vol.Schema({})
        )
    
    def _get_yaml_code(self, entity_id):
        return f"""
api:
  services:
    - service: send_raw_command
      variables:
        command: int[]
      then:
        - remote_transmitter.transmit_raw:
            code: !lambda 'return command;'
            carrier_frequency: 38kHz

remote_receiver:
  pin: 
    number: GPIO5
    inverted: true
  dump: raw 
  tolerance: 50% 
  idle: 50ms
  on_raw:
    then:
      - homeassistant.service:
          service: esphome_rc.report_code
          data:
            entity_id: {entity_id}
          data_template:
            code: !lambda |
              std::string res = "[";
              for (size_t i = 0; i < x.size(); i++) {{
                if (i > 0) res += ", ";
                res += to_string(x[i]);
              }}
              res += "]";
              return res;
"""


class ESPHomeRCOptionsFlow(config_entries.OptionsFlow):
    """Options flow for 🗿• ESPHome IR Manager 🛠️."""

    def __init__(self, entry):
        self.entry = entry
        self.coordinator = None
        self._selected_device = None
        self._command_to_learn = None

    async def async_step_init(self, user_input=None):
        self.coordinator = self.hass.data[DOMAIN].get(self.entry.entry_id)
        if not self.coordinator:
            return self.async_abort(reason="unknown")
        
        return await self.async_step_manage_subdevices()

    # --- Sub-device Management ---

    async def async_step_manage_subdevices(self, user_input=None):
        return self.async_show_menu(
            step_id="manage_subdevices",
            menu_options=["add_subdevice", "select_subdevice", "show_yaml"]
        )

    async def async_step_show_yaml(self, user_input=None):
        """Display ESPHome YAML configuration."""
        if user_input is not None:
            return await self.async_step_manage_subdevices()

        slug_name = self.coordinator.device_name.lower().replace(" ", "_")
        predicted_entity_id = f"remote.{slug_name}"
        
        # Helper instance to get yaml string
        flow_helpers = ESPHomeRCConfigFlow()
        yaml_code = flow_helpers._get_yaml_code(predicted_entity_id)

        return self.async_show_form(
            step_id="show_yaml",
            description_placeholders={"yaml": yaml_code},
            data_schema=vol.Schema({})
        )

    async def async_step_add_subdevice(self, user_input=None):
        if user_input is not None:
            name = user_input["subdevice_name"]
            if self.coordinator.add_subdevice(name):
                await self.coordinator.async_save_storage()
                await self.hass.config_entries.async_reload(self.entry.entry_id)
                return self.async_create_entry(title="", data={}) 
            else:
                return self.async_show_form(step_id="add_subdevice", errors={"base": "device_exists"}, data_schema=vol.Schema({vol.Required("subdevice_name"): str}))
        return self.async_show_form(step_id="add_subdevice", data_schema=vol.Schema({vol.Required("subdevice_name"): str}))

    async def async_step_select_subdevice(self, user_input=None):
        if user_input is not None:
            self._selected_device = user_input["device"]
            return await self.async_step_device_actions()

        devices = list(self.coordinator.codes.keys())
        if not devices: return self.async_abort(reason="no_devices")
        return self.async_show_form(step_id="select_subdevice", data_schema=vol.Schema({vol.Required("device"): vol.In(devices)}))

    async def async_step_device_actions(self, user_input=None):
        return self.async_show_menu(
            step_id="device_actions",
            menu_options=["learn_command", "learn_multiple", "delete_command", "delete_subdevice"],
            description_placeholders={"device_name": self._selected_device}
        )

    async def async_step_delete_subdevice(self, user_input=None):
        if user_input is not None:
             if self.coordinator.remove_subdevice(self._selected_device):
                 await self.coordinator.async_save_storage()
                 # IMPORTANT: Reload is needed to remove entities from registry immediately visually
                 await self.hass.config_entries.async_reload(self.entry.entry_id)
                 return self.async_create_entry(title="", data={})
        return self.async_show_form(step_id="delete_subdevice", data_schema=vol.Schema({}), description_placeholders={"device_name": self._selected_device})

    # --- Single Command Learning ---

    async def async_step_learn_command(self, user_input=None):
        if user_input is not None:
            self._command_to_learn = user_input["command_name"]
            return await self.async_step_learn_wait()
        return self.async_show_form(step_id="learn_command", data_schema=vol.Schema({vol.Required("command_name"): str}))

    async def async_step_learn_wait(self, user_input=None):
        errors = {}
        if user_input is not None:
             try:
                code = await self.coordinator.learn_command(timeout=20)
                self.coordinator.codes[self._selected_device][self._command_to_learn] = code
                await self.coordinator.async_save_storage()
                await self.hass.config_entries.async_reload(self.entry.entry_id)
                return self.async_create_entry(title="", data={})
             except Exception as e:
                 errors["base"] = "learn_failed"
                 _LOGGER.error("Learning failed: %s", e)

        return self.async_show_form(
            step_id="learn_wait",
            errors=errors,
            description_placeholders={"command": self._command_to_learn, "device": self._selected_device},
            data_schema=vol.Schema({}) 
        )

    # --- Multiple Command Learning ---

    async def async_step_learn_multiple(self, user_input=None):
        """Input name for next command in loop."""
        if user_input is not None:
            self._command_to_learn = user_input["command_name"]
            return await self.async_step_learn_multiple_wait()

        return self.async_show_form(
            step_id="learn_multiple",
            data_schema=vol.Schema({vol.Required("command_name"): str}),
            description_placeholders={"device": self._selected_device}
        )

    async def async_step_learn_multiple_wait(self, user_input=None):
        """Wait loop for multiple commands."""
        errors = {}
        if user_input is not None:
             try:
                code = await self.coordinator.learn_command(timeout=20)
                self.coordinator.codes[self._selected_device][self._command_to_learn] = code
                await self.coordinator.async_save_storage()
                # Loop back to start without closing flow
                return await self.async_step_learn_multiple()
             except Exception as e:
                 errors["base"] = "learn_failed"

        return self.async_show_form(
            step_id="learn_multiple_wait",
            errors=errors,
            description_placeholders={"command": self._command_to_learn},
            data_schema=vol.Schema({}) 
        )

    # --- Deletion ---

    async def async_step_delete_command(self, user_input=None):
        current_commands = list(self.coordinator.codes[self._selected_device].keys())
        if user_input is not None:
            for cmd in user_input["commands"]:
                self.coordinator.delete_command(self._selected_device, cmd)
            await self.coordinator.async_save_storage()
            await self.hass.config_entries.async_reload(self.entry.entry_id)
            return self.async_create_entry(title="", data={})

        if not current_commands: return await self.async_step_device_actions()
        return self.async_show_form(step_id="delete_command", data_schema=vol.Schema({vol.Required("commands"): cv.multi_select(current_commands)}))