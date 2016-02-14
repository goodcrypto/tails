@product
Feature: Using dogtail

  Scenario: dogtail works
    Given I have started Tails from DVD without network and logged in
    When I enable the accessibility toolkit in GNOME
    And I start gedit
    Then dogtail works
