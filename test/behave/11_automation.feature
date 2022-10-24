@allure.suite:behave
Feature: automation
  Scenario: triger automation
    Given an English speaking user
    When the user says "activate the automation mycroft tracker automation"
	  Then "homeassistant" should reply with dialog from "homeassistant.automation.trigger.dialog"

  # #####################
  # try to trigger a script, then read a state of light that script handles
  # Can fail if sensor reading is malfunction
  @xfail
  Scenario: triger script
    Given an English speaking user
    When the user says "activate the script roof"
	  Then "homeassistant" should reply with dialog from "homeassistant.automation.trigger.dialog"

  @xfail
  Scenario: read light state
    Given an English speaking user
    When the user says "give me the value of roof light"
    Then mycroft reply should contain "255"
  # #####################
