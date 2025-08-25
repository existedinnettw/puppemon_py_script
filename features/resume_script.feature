Feature: Resume script execution

  Background:
    Given a script started with an embedded gRPC control server
    And the script defines concurrent async tasks A and B with pausable points

  Scenario: Resume continues all paused tasks
    Given the script state is "paused"
    And tasks A and B are halted at pausable points
    When the client sends the RESUME command
    Then tasks A and B continue execution past the pause points
    And the script state is "running"

  Scenario: RESUME is a no-op when already running
    Given the script state is "running"
    When the client sends the RESUME command
    Then the server acknowledges with "already running" (no state change)
    And the script state remains "running"
