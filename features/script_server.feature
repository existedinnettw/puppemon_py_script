Feature: Script control server (gRPC)

  Background:
    Given a script started with an embedded gRPC control server

  Scenario: Control server exposes standard commands
    When a client connects to the control server
    Then the client can call the PAUSE command
    And the client can call the RESUME command
    And the client can call the STOP command

  Scenario: Unknown command is rejected
    When a client sends an unknown command
    Then the server responds with an error indicating the command is unsupported