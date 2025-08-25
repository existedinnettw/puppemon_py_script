Feature: Pause script execution

	Background:
		Given a script started with an embedded gRPC control server
		And the script defines concurrent async tasks A and B with pausable points

	Scenario: Pause halts all tasks at their next pausable points
		Given tasks A and B are executing
		When the client sends the PAUSE command
		Then each task halts at its next pausable point
		And the script state is "paused"

	Scenario: PAUSE is idempotent when already paused
		Given the script state is "paused"
		When the client sends the PAUSE command
		Then the server acknowledges with "already paused" (no state change)
		And the script state remains "paused"

	Scenario: PAUSE succeeds before timeout when all tasks can pause in time
		Given tasks A and B are executing and both can reach a pausable point promptly
		When the client sends the PAUSE command with a timeout of 5 seconds
		Then the server responds with success before the timeout elapses
		And each task halts at its next pausable point
		And the script state is "paused"

	Scenario: PAUSE times out when not all tasks can pause in time
		Given task A is executing and cannot reach a pausable point within 1 second
		And task B is executing and can reach a pausable point within 1 second
		When the client sends the PAUSE command with a timeout of 1 second
		Then the server responds with a timeout error
		And no global pause is applied (tasks continue running)
