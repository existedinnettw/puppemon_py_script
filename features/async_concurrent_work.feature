Feature: Async concurrent work

  Background:
    Given a script started with an embedded gRPC control server
    And the script defines concurrent async tasks A and B with pausable points

  Scenario: Multiple async tasks run concurrently
    When the script starts execution
    Then tasks A and B execute concurrently
    And each task can declare pausable points that cooperate with control commands

  Scenario: Pause and resume across concurrent tasks
    Given tasks A and B are executing
    When the client sends the PAUSE command
    Then both tasks pause at their next pausable points
    When the client sends the RESUME command
    Then both tasks continue and complete their work
