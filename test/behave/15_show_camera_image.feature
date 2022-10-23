@allure.suite:behave
Feature: camera
  @xfail
  Scenario: show image of missing entity
    Given an English speaking user
    When the user says "show me the latest picture of Albert Einstein"
    Then "homeassistant" should not reply

  @xfail
  Scenario: show image
    Given an English speaking user
    When the user says "show me the latest picture of Mycroft camera"
    Then "homeassistant" should reply with dialog from "homeassistant.error.no_gui"
