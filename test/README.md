# <img src='../home-assistant.png' card_color='#000000' width='50' height='50' style='vertical-align:bottom'/> Home Assistant
Awaken your home - Control Home Assistant

## About
[Home Assistant](https://www.home-assistant.io/) skill include [Voight Kampff tests](https://mycroft-ai.gitbook.io/docs/skill-development/voight-kampff).
To achieve a same development envinroment is needed to add a specific "dummy/testing" componens to your running HA instalation.
When test is run, then skill behave is tested along side with comunication between Mycroft <> HA and also HA actions to each utterance.

## HA Configuration - configuration.yaml
input_boolean:
  mycroft_vk_bool:
    name: "Mycroft bool"
    initial: off

input_number:
  mycroft_vk_num:
    min: 0
    max: 255

binary_sensor:
  - platform: template
    sensors:
      mycroft_vk_tracker_sensor:
        value_template: >-
          {{ is_state('input_boolean.mycroft_vk_bool','on') }}
        device_class: 'presence'
        attribute_templates:
          latitude: 48.864716
          longitude: 2.349014

sensor:
	- platform: template
    sensors:
      mycroft_vk_temp:
        friendly_name: "Mycroft sensor"
        unit_of_measurement: '°C'
        value_template: 12.00

switch:
 - platform: template
    switches:
      mycroft_vk_switch:
        friendly_name: "Mycroft switch"
        value_template: "{{ is_state('input_boolean.mycroft_vk_bool', 'on') }}"
        turn_on:
          service: input_boolean.turn_on
          data:
            entity_id: input_boolean.mycroft_vk_bool
        turn_off:
          service: input_boolean.turn_off
          data:
            entity_id: input_boolean.mycroft_vk_bool

light:
  - platform: template
    lights:
      mycroft_vk_light:
        friendly_name: "Mycroft light"
        turn_on:
          service: input_boolean.turn_on
          entity_id: input_boolean.mycroft_vk_bool
        turn_off:
          service: input_boolean.turn_off
          entity_id: input_boolean.mycroft_vk_bool
        set_level:
          service: input_number.set_value
          data_template:
            value: "{{ brightness }}"
            entity_id: input_number.mycroft_vk_num

climate:
  - platform: generic_thermostat
    name: "Mycroft climate"
    heater: switch.mycroft_vk_switch
    target_sensor: sensor.mycroft_vk_temp
	min_temp: 15
    max_temp: 21
    ac_mode: false
    target_temp: 17
    cold_tolerance: 0.3
    hot_tolerance: 0
    min_cycle_duration:
      seconds: 5
    keep_alive:
      minutes: 3
    initial_hvac_mode: "off"
    away_temp: 16
    precision: 0.1

shopping_list:

## HA Configuration - automation.yaml
- id: '123456789'
    alias: Mycroft Tracker Automation
    trigger:
    - event: start
    platform: homeassistant
    action:
    - data: {}
    entity_id: input_boolean.mycroft_vk_bool
    service: input_boolean.turn_on
    - data_template:
        dev_id: mycroft_vk_tracker
        location_name: "{% if is_state('binary_sensor.mycroft_vk_tracker_sensor', 'on')\
        \ -%}\n  home\n{%- else -%}\n  not_home\n{%- endif %}\n"
    service: device_tracker.see

Note: Put automation into automation.yaml only when your configuration.yaml contain "automation: !include automations.yaml" otherwise put it directly into configuration.yaml.


## Usage

mycroft-skill-testrunner vktest  clear
mycroft-skill-testrunner vktest -t homeassistant.mycroftai

Note: Before each run, is better to retart HA and check if all dummy/test values/states are in initial position.