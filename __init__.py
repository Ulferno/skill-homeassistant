"""
Home Assistant skill
"""  # pylint: disable=C0103
from os.path import join as pth_join

from mycroft import MycroftSkill, intent_handler
from mycroft.messagebus.message import Message
from mycroft.skills.core import FallbackSkill
from mycroft.util import get_cache_directory
from mycroft.util.format import nice_number
from quantulum3 import parser
from requests.exceptions import (HTTPError, InvalidURL, RequestException,
                                 SSLError, Timeout, URLRequired)
# pylint: disable=E0401
from requests.packages.urllib3.exceptions import MaxRetryError

from .ha_client import HomeAssistantClient, check_url

__author__ = 'robconnolly, btotharye, nielstron'

# Timeout time for HA requests
TIMEOUT = 10


# pylint: disable=R0912, W0105, W0511, W0233
class HomeAssistantSkill(FallbackSkill):
    """Main skill class"""

    def __init__(self) -> None:
        MycroftSkill.__init__(self)
        super().__init__(name="HomeAssistantSkill")
        self.ha_client = None
        self.enable_fallback = False
        self.tracker_file = ""

    def _setup(self, force: bool = False) -> None:
        if self.settings is not None and (force or self.ha_client is None):
            # Check if user filled IP, port and Token in configuration
            ip_address = check_url(str(self.settings.get('host')))
            token = self.settings.get('token')

            """Inform user if ip/url or token not or incorrectly filed"""
            if not ip_address:

                self.speak_dialog('homeassistant.error.setup', data={
                              "field": "I.P."})
                return

            if not token:
                self.speak_dialog('homeassistant.error.setup', data={
                              "field": "token"})
                return

            port_number = self.settings.get('portnum')
            try:
                port_number = int(port_number)
            except TypeError:
                port_number = 8123
            except ValueError:
                # String might be some rubbish (like '')
                self.speak_dialog('homeassistant.error.setup', data={
                              "field": "port"})
                return

            config = {'ip_address': ip_address,
                      'token': token,
                      'port_number': port_number,
                      'ssl': self.settings.get('ssl'),
                      'verify': self.settings.get('verify'),
                      }

            self.ha_client = HomeAssistantClient(config)
            if self.ha_client.connected():
                # Check if conversation component is loaded at HA-server
                # and activate fallback accordingly (ha-server/api/components)
                # TODO: enable other tools like dialogflow
                conversation_activated = self.ha_client.find_component(
                    'conversation'
                )
                if conversation_activated:
                    self.enable_fallback = \
                        self.settings.get('enable_fallback')

                # Register tracker entities
                self._register_tracker_entities()

    def _force_setup(self) -> None:
        self.log.debug('Creating a new HomeAssistant-Client')
        self._setup(True)

    def _register_tracker_entities(self) -> None:
        """List tracker entities.

        Add them to entity file and registry it so
        Padatious react only to known entities.
        Should fix conflict with Where is skill.
        """
        types = ['device_tracker']
        entities = self.ha_client.list_entities(types)

        if entities:
            cache_dir = get_cache_directory(type(self).__name__)
            self.tracker_file = pth_join(cache_dir, "tracker.entity")

            with open(self.tracker_file, 'w', encoding='utf8') as voc_file:
                voc_file.write('\n'.join(entities))

            # Workaround: If https://github.com/MycroftAI/mycroft-core/pull/3101
            # will be merged, next two lines could be changed to proper usage
            # self.register_entity_file(self.tracker_file)
            name = '{}:tracker'.format(self.skill_id)
            self.intent_service.register_padatious_entity(name, self.tracker_file)

    def initialize(self) -> None:
        """Initialize skill, set language and priority."""
        # pylint: disable=W0201
        self.language = self.config_core.get('lang')

        # Needs higher priority than general fallback skills
        self.register_fallback(self.handle_fallback, 2)
        # Check and then monitor for credential changes
        # pylint: disable=W0201
        self.settings_change_callback = self.on_websettings_changed
        self._setup()

    def on_websettings_changed(self) -> None:
        """
        Force a setting refresh after the websettings changed
        otherwise new settings will not be regarded.
        """
        self._force_setup()

    # Try to find an entity on the HAServer
    # Creates dialogs for errors and speaks them
    # Returns None if nothing was found
    # Else returns entity that was found
    def _find_entity(self, entity: str, domains: list) -> dict:
        """Handle communication with HA client for entity finding

        Returns:
            Entity
        """
        self._setup()
        if self.ha_client is None:
            self.speak_dialog('homeassistant.error.setup')
            return False
        # TODO if entity is 'all', 'any' or 'every' turn on
        # every single entity not the whole group
        ha_entity = self._handle_client_exception(self.ha_client.find_entity,
                                                  entity, domains)
        if ha_entity is None:
            self.speak_dialog('homeassistant.error.device.unknown', data={
                              "dev_name": entity})
        return ha_entity

    def _check_availability(self, ha_entity: dict) -> bool:
        """ Simple routine for checking availability of entity inside
        Home Assistant.

        Returns:
            True/False state
        """

        if ha_entity['state'] == 'unavailable':
            """Check if state is unavailable, if yes, inform user about it."""

            self.speak_dialog('homeassistant.error.device.unavailable', data={
                            "dev_name": ha_entity['dev_name']})
            """Return result to underlining function."""
            return False
        return True

    def _handle_client_exception(self, callback, *args, **kwargs):
        """Calls passed method and catches often occurring exceptions

        Returns:
            Function output or False"""
        try:
            return callback(*args, **kwargs)
        except Timeout:
            self.speak_dialog('homeassistant.error.offline')
        except (InvalidURL, URLRequired, MaxRetryError) as error:
            if error.request is None or error.request.url is None:
                # There is no url configured
                self.speak_dialog('homeassistant.error.needurl')
            else:
                self.speak_dialog('homeassistant.error.invalidurl', data={
                                  'url': error.request.url})
        except SSLError:
            self.speak_dialog('homeassistant.error.ssl')
        except HTTPError as error:
            # check if due to wrong password
            if error.response.status_code == 401:
                self.speak_dialog('homeassistant.error.wrong_password')
            else:
                self.speak_dialog('homeassistant.error.http', data={
                    'code': error.response.status_code,
                    'reason': error.response.reason})
        except (ConnectionError, RequestException) as exception:
            # TODO find a nice member of any exception to output
            self.speak_dialog('homeassistant.error', data={
                    'url': exception.request.url})

        return False

    # Intent handlers
    @intent_handler('show.camera.image.intent')
    def handle_show_camera_image_intent(self, message: Message) -> None:
        """Handle show camera image intent."""
        message.data["Entity"] = message.data.get("entity")
        self._handle_camera_image_actions(message)

    @intent_handler('turn.on.intent')
    def handle_turn_on_intent(self, message: Message) -> None:
        """Handle turn on intent."""
        self.log.debug("Turn on intent on entity: %s", message.data.get("entity"))
        message.data["Entity"] = message.data.get("entity")
        message.data["Action"] = "on"
        self._handle_turn_actions(message)

    @intent_handler('turn.off.intent')
    def handle_turn_off_intent(self, message: Message) -> None:
        """Handle turn off intent."""
        self.log.debug("Turn off intent on entity: %s", message.data.get("entity"))
        message.data["Entity"] = message.data.get("entity")
        message.data["Action"] = "off"
        self._handle_turn_actions(message)

    @intent_handler('open.intent')
    def handle_open(self, message: Message) -> None:
        """Handle open intent."""
        message.data["Entity"] = message.data.get("entity")
        message.data["Action"] = "open"
        self._handle_open_close_actions(message)

    @intent_handler('close.intent')
    def handle_close(self, message: Message) -> None:
        """Handle close intent."""
        message.data["Entity"] = message.data.get("entity")
        message.data["Action"] = "close"
        self._handle_open_close_actions(message)

    @intent_handler('stop.intent')
    def handle_stop(self, message: Message) -> None:
        """Handle stop intent."""
        message.data["Entity"] = message.data.get("entity")
        message.data["Action"] = "stop"
        self._handle_stop_actions(message)

    @intent_handler('toggle.intent')
    def handle_toggle_intent(self, message: Message) -> None:
        """Handle toggle intent."""
        self.log.debug("Toggle intent on entity: %s", message.data.get("entity"))
        message.data["Entity"] = message.data.get("entity")
        message.data["Action"] = "toggle"
        self._handle_turn_actions(message)

    @intent_handler('sensor.intent')
    def handle_sensor_intent(self, message: Message) -> None:
        """Handle sensor intent."""
        self.log.debug("Turn on intent on entity: %s", message.data.get("entity"))
        message.data["Entity"] = message.data.get("entity")
        self._handle_sensor(message)

    @intent_handler('set.light.brightness.intent')
    def handle_light_set_intent(self, message: Message) -> None:
        """Handle set light brightness intent."""
        self.log.debug("Change light intensity: %s to %s percent", message.data.get("entity"),
                       message.data.get("brightnessvalue"))
        message.data["Entity"] = message.data.get("entity")
        message.data["Brightnessvalue"] = message.data.get("brightnessvalue")
        self._handle_light_set(message)

    @intent_handler('increase.light.brightness.intent')
    def handle_light_increase_intent(self, message: Message) -> None:
        """Handle increase light brightness intent."""
        self.log.debug("Increase light intensity: %s", message.data.get("entity"))
        message.data["Entity"] = message.data.get("entity")
        message.data["Action"] = "up"
        self._handle_light_adjust(message)

    @intent_handler('decrease.light.brightness.intent')
    def handle_light_decrease_intent(self, message: Message) -> None:
        """Handle decrease light brightness intent."""
        self.log.debug("Decrease light intensity: %s", message.data.get("entity"))
        message.data["Entity"] = message.data.get("entity")
        message.data["Action"] = "down"
        self._handle_light_adjust(message)

    @intent_handler('automation.intent')
    def handle_automation_intent(self, message: Message) -> None:
        """Handle automation intent."""
        self.log.debug("Automation trigger intent on entity: %s", message.data.get("entity"))
        message.data["Entity"] = message.data.get("entity")
        self._handle_automation(message)

    @intent_handler('tracker.intent')
    def handle_tracker_intent(self, message: Message) -> None:
        """Handle tracker intent."""
        self.log.debug("Turn on intent on entity: %s", message.data.get("tracker"))
        message.data["Entity"] = message.data.get("tracker")
        self._handle_tracker(message)

    @intent_handler('set.climate.intent')
    def handle_set_thermostat_intent(self, message: Message) -> None:
        """Handle set climate intent."""
        self.log.debug("Set thermostat intent on entity: %s", message.data.get("entity"))
        message.data["Entity"] = message.data.get("entity")
        message.data["Temp"] = message.data.get("temp")
        self._handle_set_thermostat(message)

    @intent_handler('add.item.shopping.list.intent')
    def handle_shopping_list_intent(self, message: Message) -> None:
        """Handle add item to shopping list intent."""
        self.log.debug("Add %s to the shoping list", message.data.get("entity"))
        message.data["Entity"] = message.data.get("entity")
        self._handle_shopping_list(message)

    def _handle_camera_image_actions(self, message: Message) -> None:
        """Handler for camera image actions."""
        entity = message.data["Entity"]

        if not self.gui.connected:
            self.speak_dialog('homeassistant.error.no_gui')
            return

        ha_entity = self._find_entity(entity, ['camera'])

        if not ha_entity or not self._check_availability(ha_entity):
            return

        attributes = ha_entity['attributes']
        entity_picture = attributes.get('entity_picture')

        self.acknowledge()

        self.gui.clear()
        self.gui.show_image(f"{self.ha_client.url}{entity_picture}", override_idle=15)

    def _handle_turn_actions(self, message: Message) -> None:
        """Handler for turn on/off and toggle actions."""
        self.log.debug("Starting Switch Intent")
        entity = message.data["Entity"]
        action = message.data["Action"]
        self.log.debug("Entity: %s", entity)
        self.log.debug("Action: %s", action)

        # Handle turn on/off all intent
        try:
            if self.voc_match(entity, "all_lights"):
                domain = "light"
            elif self.voc_match(entity, "all_switches"):
                domain = "switch"
            else:
                domain = None

            if domain is not None:
                ha_entity = {'dev_name': entity}
                ha_data = {'entity_id': 'all'}

                self.ha_client.execute_service(domain, "turn_{action}", ha_data)
                self.speak_dialog(f'homeassistant.device.{action}', data=ha_entity)
                return
        # TODO: need to figure out, if this indeed throws a KeyError
        except KeyError:
            self.log.debug("Not turn on/off all intent")
        except Exception as error:  # pylint: disable=W0703
            self.log.debug("Unexpected error in turn all intent: %s", error)

        # Handle single entity

        ha_entity = self._find_entity(
            entity,
            [
                'group',
                'light',
                'fan',
                'switch',
                'scene',
                'input_boolean',
                'climate'
            ]
        )

        # Exit if entity not found or is unavailabe
        if not ha_entity or not self._check_availability(ha_entity):
            return

        self.log.debug("Entity State: %s", ha_entity['state'])

        ha_data = {'entity_id': ha_entity['id']}

        # IDEA: set context for 'turn it off' again or similar
        # self.set_context('Entity', ha_entity['dev_name'])
        if ha_entity['state'] == action:
            self.log.debug("Entity in requested state")
            self.speak_dialog('homeassistant.device.already', data={
                "dev_name": ha_entity['dev_name'], 'action': action})
        elif action == "toggle":
            self.ha_client.execute_service("homeassistant", "toggle",
                                           ha_data)
            if ha_entity['state'] == 'off':
                action = 'on'
            else:
                action = 'off'
            self.speak_dialog(f'homeassistant.device.{action}',
                              data=ha_entity)
        elif action in ["on", "off"]:
            self.speak_dialog(f'homeassistant.device.{action}',
                              data=ha_entity)
            self.ha_client.execute_service("homeassistant", f"turn_{action}",
                                           ha_data)
        else:
            self.speak_dialog('homeassistant.error.sorry')
            return

    def _handle_light_set(self, message: Message) -> None:
        """Handle set light action."""
        entity = message.data["entity"]
        try:
            brightness_req = float(message.data["Brightnessvalue"])
            if brightness_req > 100 or brightness_req < 0:
                self.speak_dialog('homeassistant.brightness.badreq')
        except KeyError:
            brightness_req = 10.0
        brightness_value = int(brightness_req / 100 * 255)
        brightness_percentage = int(brightness_req)
        self.log.debug("Entity: %s", entity)
        self.log.debug("Brightness Value: %s", brightness_value)
        self.log.debug("Brightness Percent: %s", brightness_percentage)

        ha_entity = self._find_entity(entity, ['group', 'light'])
        # Exit if entity not found or is unavailabe
        if not ha_entity or not self._check_availability(ha_entity):
            return

        ha_data = {'entity_id': ha_entity['id']}

        # IDEA: set context for 'turn it off again' or similar
        # self.set_context('Entity', ha_entity['dev_name'])
        # Set values for HA
        ha_data['brightness'] = brightness_value
        self.ha_client.execute_service("light", "turn_on", ha_data)
        # Set values for Mycroft reply
        ha_data['dev_name'] = ha_entity['dev_name']
        ha_data['brightness'] = brightness_req
        self.speak_dialog('homeassistant.brightness.dimmed',
                          data=ha_data)

        return

    def _handle_shopping_list(self, message: Message) -> None:
        """Handler for add item to shopping list action."""
        entity = message.data["Entity"]
        ha_data = {'name': entity}
        self.ha_client.execute_service("shopping_list", "add_item", ha_data)
        self.speak_dialog("homeassistant.shopping.list")

    def _handle_open_close_actions(self, message: Message) -> None:
        """Handler for open and close actions."""
        entity = message.data["Entity"]
        action = message.data["Action"]

        if self.voc_match(entity, "HomeAssistant"):
            if not self.gui.connected:
                self.speak_dialog('homeassistant.error.no_gui')
                return

            if action == "open":
                self.acknowledge()
                self.gui.clear()
                self.gui.show_url(self.ha_client.url, override_idle=True)
            elif action == "close":
                self.acknowledge()
                self.gui.release()
            return

        ha_entity = self._find_entity(entity, ['cover'])
        # Exit if entity not found or is unavailabe
        if not ha_entity or not self._check_availability(ha_entity):
            return

        entity = ha_entity['id']
        domain = entity.split(".")[0]

        ha_data = {'entity_id': ha_entity['id']}

        if domain == "cover":
            response = self.ha_client.execute_service("cover", f"{action}_cover", ha_data)

            if response.status_code != 200:
                return

            if action == "open":
                self.speak_dialog("homeassistant.device.opening",
                                  data=ha_entity)
            elif action == "close":
                self.speak_dialog("homeassistant.device.closing",
                                  data=ha_entity)
            return

        return

    def _handle_stop_actions(self, message):
        """Handler for stop actions."""
        entity = message.data["Entity"]

        ha_entity = self._find_entity(entity, ['cover'])
        # Exit if entity not found or is unavailabe
        if not ha_entity or not self._check_availability(ha_entity):
            return

        entity = ha_entity['id']
        domain = entity.split(".")[0]

        ha_data = {'entity_id': ha_entity['id']}

        if domain == "cover":
            response = self.ha_client.execute_service("cover", "stop_cover", ha_data)

            if response.status_code != 200:
                return

            self.speak_dialog("homeassistant.device.stopped",
                              data=ha_entity)
            return
        return

    def _handle_light_adjust(self, message: Message) -> None:
        """Handler for light brightness increase and decrease action"""
        entity = message.data["Entity"]
        action = message.data["Action"]
        brightness_req = 10.0
        brightness_value = int(brightness_req / 100 * 255)
        # brightness_percentage = int(brightness_req) # debating use
        self.log.debug("Entity: %s", entity)
        self.log.debug("Brightness Value: %s", brightness_value)

        # Set the min and max brightness for bulbs. Smart bulbs
        # use 0-255 integer brightness, while spoken commands will
        # use 0-100% brightness.
        min_brightness = 5
        max_brightness = 255

        ha_entity = self._find_entity(entity, ['group', 'light'])
        # Exit if entity not found or is unavailabe
        if not ha_entity or not self._check_availability(ha_entity):
            return
        ha_data = {'entity_id': ha_entity['id']}
        # IDEA: set context for 'turn it off again' or similar
        # self.set_context('Entity', ha_entity['dev_name'])

        if action == "down":
            if ha_entity['state'] == "off":
                self.speak_dialog('homeassistant.brightness.cantdim.off',
                                  data=ha_entity)
            else:
                light_attrs = self.ha_client.find_entity_attr(ha_entity['id'])
                if light_attrs['unit_measure'] == "":
                    self.speak_dialog(
                        'homeassistant.brightness.cantdim.dimmable',
                        data=ha_entity)
                else:
                    ha_data['brightness'] = light_attrs['unit_measure'] - brightness_value
                    if ha_data['brightness'] < min_brightness:
                        ha_data['brightness'] = min_brightness
                    self.ha_client.execute_service("homeassistant",
                                                   "turn_on",
                                                   ha_data)
                    ha_data['dev_name'] = ha_entity['dev_name']
                    ha_data['brightness'] = round(100 / max_brightness * ha_data['brightness'])
                    self.speak_dialog('homeassistant.brightness.decreased',
                                      data=ha_data)
        elif action == "up":
            if ha_entity['state'] == "off":
                self.speak_dialog(
                    'homeassistant.brightness.cantdim.off',
                    data=ha_entity)
            else:
                light_attrs = self.ha_client.find_entity_attr(ha_entity['id'])
                if light_attrs['unit_measure'] == "":
                    self.speak_dialog(
                        'homeassistant.brightness.cantdim.dimmable',
                        data=ha_entity)
                else:
                    ha_data['brightness'] = light_attrs['unit_measure'] + brightness_value
                    if ha_data['brightness'] > max_brightness:
                        ha_data['brightness'] = max_brightness
                    self.ha_client.execute_service("homeassistant",
                                                   "turn_on",
                                                   ha_data)
                    ha_data['dev_name'] = ha_entity['dev_name']
                    ha_data['brightness'] = round(100 / max_brightness * ha_data['brightness'])
                    self.speak_dialog('homeassistant.brightness.increased',
                                      data=ha_data)
        else:
            self.speak_dialog('homeassistant.error.sorry')
            return

    def _handle_automation(self, message: Message) -> None:
        """Handler for triggering automations."""
        entity = message.data["Entity"]
        self.log.debug("Entity: %s", entity)
        ha_entity = self._find_entity(
            entity,
            ['automation', 'scene', 'script']
        )

        # Exit if entity not found or is unavailabe
        if not ha_entity or not self._check_availability(ha_entity):
            return

        ha_data = {'entity_id': ha_entity['id']}

        # IDEA: set context for 'turn it off again' or similar
        # self.set_context('Entity', ha_entity['dev_name'])

        self.log.debug("Triggered automation/scene/script: %s", ha_entity['id'])
        if "automation" in ha_entity['id']:
            self.ha_client.execute_service('automation', 'trigger', ha_data)
            self.speak_dialog('homeassistant.automation.trigger',
                              data={"dev_name": ha_entity['dev_name']})
        elif "script" in ha_entity['id']:
            self.speak_dialog('homeassistant.automation.trigger',
                              data={"dev_name": ha_entity['dev_name']})
            self.ha_client.execute_service("script", "turn_on",
                                           data=ha_data)
        elif "scene" in ha_entity['id']:
            self.speak_dialog('homeassistant.scene.on',
                              data=ha_entity)
            self.ha_client.execute_service("scene", "turn_on",
                                           data=ha_data)

    def _handle_sensor(self, message: Message) -> None:
        """Handler sensors reading"""
        entity = message.data["Entity"]
        self.log.debug("Entity: %s", entity)

        ha_entity = self._find_entity(
            entity,
            [
                'light',
                'climate',
                'sensor',
                'switch',
                'binary_sensor',
                'cover'
            ]
        )

        # Exit if entity not found or is unavailabe
        if not ha_entity or not self._check_availability(ha_entity):
            return

        entity = ha_entity['id']
        domain = entity.split(".")[0]
        attributes = ha_entity['attributes']

        # IDEA: set context for 'read it out again' or similar
        # self.set_context('Entity', ha_entity['dev_name'])

        unit_measurement = self.ha_client.find_entity_attr(entity)
        sensor_unit = unit_measurement.get('unit_measure') or ''

        sensor_name = unit_measurement['name']
        sensor_state = unit_measurement['state']
        # extract unit for correct pronunciation
        # this is fully optional

        if unit_measurement != '':
            quantity = parser.parse(f'{sensor_name} is {sensor_state} {sensor_unit}')
            if len(quantity) > 0:
                quantity = quantity[0]
                if quantity.unit.name != "dimensionless":
                    sensor_unit = quantity.unit.name
                    sensor_state = quantity.value

        try:
            value = float(sensor_state)
            sensor_state = nice_number(value, lang=self.language)
        except ValueError:
            pass

        if domain == "climate" and sensor_state != '':
            current_temp = nice_number((float(attributes['current_temperature'])))
            target_temp = nice_number((float(attributes['temperature'])))
            self.speak_dialog('homeassistant.sensor.thermostat', data={
                "dev_name": sensor_name,
                "value": sensor_state,
                "current_temp": current_temp,
                "targeted_temp": target_temp})

            self._display_sensor_dialog(
                sensor_name,
                attributes['current_temperature'],
                sensor_state
            )
        elif domain == "cover":
            self.speak_dialog(f'homeassistant.device.{sensor_state}', data={
                "dev_name": sensor_name})

            sensor_states = self.translate_namedvalues(
                'homeassistant.sensor.cover.state')
            sensor_state = sensor_states[sensor_state]

            self._display_sensor_dialog(sensor_name, sensor_state)
        elif domain == "binary_sensor":
            sensor_states = self.translate_namedvalues(
                f'homeassistant.binary_sensor.{sensor_state}')
            sensor_state = sensor_states['default']

            if attributes.get('device_class') in sensor_states:
                sensor_state = sensor_states[attributes['device_class']]

            self.speak_dialog('homeassistant.sensor.binary_sensor', data={
                "dev_name": sensor_name,
                "value": sensor_state})

            self._display_sensor_dialog(sensor_name, sensor_state)
        else:
            self.speak_dialog('homeassistant.sensor', data={
                "dev_name": sensor_name,
                "value": sensor_state,
                "unit": sensor_unit})

            self._display_sensor_dialog(sensor_name, unit_measurement['state'])
        # IDEA: Add some context if the person wants to look the unit up
        # Maybe also change to name
        # if one wants to look up "outside temperature"
        # self.set_context("SubjectOfInterest", sensor_unit)

    # In progress, still testing.
    # Device location works.
    # Proximity might be an issue
    # - overlapping command for directions modules
    # - (e.g. "How far is x from y?")
    def _handle_tracker(self, message: Message) -> None:
        """Handler for finding trackers position."""
        entity = message.data["Entity"]
        self.log.debug("Entity: %s", entity)

        ha_entity = self._find_entity(entity, ['device_tracker'])
        # Exit if entity not found or is unavailabe
        if not ha_entity or not self._check_availability(ha_entity):
            return

        # IDEA: set context for 'locate it again' or similar
        # self.set_context('Entity', ha_entity['dev_name'])

        entity = ha_entity['id']
        dev_name = ha_entity['dev_name']
        dev_location = ha_entity['state']
        self.speak_dialog('homeassistant.tracker.found',
                          data={'dev_name': dev_name,
                                'location': dev_location})

    def _handle_set_thermostat(self, message: Message) -> None:
        """Handler for setting thermostats."""
        entity = message.data["entity"]
        self.log.debug("Entity: %s", entity)
        self.log.debug("This is the message data: %s", message.data)
        temperature = message.data["temp"]
        self.log.debug("Temperature: %s", temperature)

        ha_entity = self._find_entity(entity, ['climate'])
        # Exit if entity not found or is unavailabe
        if not ha_entity or not self._check_availability(ha_entity):
            return

        climate_data = {
            'entity_id': ha_entity['id'],
            'temperature': temperature
        }
        climate_attr = self.ha_client.find_entity_attr(ha_entity['id'])
        self.ha_client.execute_service(
            "climate",
            "set_temperature",
            data=climate_data
        )

        self.speak_dialog(
            'homeassistant.set.thermostat',
            data={
                "dev_name": climate_attr['name'],
                "value": temperature,
                "unit": climate_attr['unit_measure']
            }
        )

    def _display_sensor_dialog(self, name, value, description=""):
        self.gui.clear()
        self.gui["sensorName"] = name
        self.gui["sensorValue"] = value
        self.gui["sensorDescription"] = description
        self.gui.show_page("sensors.qml", override_idle=15)

    def handle_fallback(self, message: Message) -> bool:
        """
        Handler for direct fallback to Home Assistants
        conversation module.

        Returns:
            True/False state of fallback registration
        """
        if not self.enable_fallback:
            return False
        self._setup()
        if self.ha_client is None:
            self.speak_dialog('homeassistant.error.setup')
            return False
        # pass message to HA-server
        response = self._handle_client_exception(
            self.ha_client.engage_conversation,
            message.data.get('utterance'))
        if not response:
            return False
        # default non-parsing answer: "Sorry, I didn't understand that"
        answer = response.get('speech')
        if not answer or answer == "Sorry, I didn't understand that":
            return False

        asked_question = False
        # TODO: maybe enable conversation here if server asks sth like
        # "In which room?" => answer should be directly passed to this skill
        if answer.endswith("?"):
            asked_question = True
        self.speak(answer, expect_response=asked_question)
        return True

    def shutdown(self) -> None:
        """Remove fallback on exit."""
        self.remove_fallback(self.handle_fallback)
        super().shutdown()


def create_skill():
    """Create skill from main class."""
    return HomeAssistantSkill()
