Feature: increase brightness
  Scenario: increase light brightness
    Given an English speaking user
    When the user says "increase the brightness of Mycroft light please"
	  Then "homeassistant" should reply with dialog from "homeassistant.brightness.increased"