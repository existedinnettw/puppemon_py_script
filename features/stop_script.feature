Feature: Stop script gracefully

  Background:
    Given a script started with an embedded gRPC control server

  Scenario: STOP from running shuts down gracefully
    Given the script state is "running"
    When the client sends the STOP command
    Then the script shuts down gracefully
    And resources are closed and no data loss or corruption is reported

  Scenario: STOP from paused shuts down gracefully
    Given the script state is "paused"
    When the client sends the STOP command
    Then the script shuts down gracefully
    And resources are closed and no data loss or corruption is reported

  Scenario: STOP is idempotent
    Given the script is already stopping or stopped
    When the client sends the STOP command
    Then the server acknowledges without error (no further action)
