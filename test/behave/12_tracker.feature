Feature: tracker
  Scenario: tracker
    Given an English speaking user
    When the user says "give me location of the Mycroft tracker sensor"
	  Then mycroft reply should contain " home"