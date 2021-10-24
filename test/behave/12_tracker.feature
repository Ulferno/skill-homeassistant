@allure.suite:behave
Feature: tracker
  Scenario: tracker
    Given an English speaking user
    When the user says "give me location of the mark"
	  Then mycroft reply should contain "home"

  Scenario: tracker - where skill conflict #1
    Given an English speaking user
    When the user says "give me location of the Czech Republic"
	  Then "skill-homeassistant" should not reply

  Scenario: tracker - where skill conflict #2
    Given an English speaking user
    When the user says "where is France"
	  Then "skill-homeassistant" should not reply

  Scenario: tracker - where skill conflict #3
    Given an English speaking user
    When the user says "where is the golden gate bridge"
	  Then "skill-homeassistant" should not reply