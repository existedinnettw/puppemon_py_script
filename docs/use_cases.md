# use cases

* When script start with a server along, server following accept `PAUSE`, `RESUME`, and `STOP` commands from client.
* When client send `PAUSE`, script is expected to pause at "pausible point" written in the script.
  * If script contain concurrent tasks (A, B), both A and B should pause at their respective "pausible points".
  * If script is already paused, subsequent `PAUSE` commands should be ignored.
  * Server may hold request for its reason(depend on implementation). Client can assign timeout parameter during `PAUSE` command. 
    * If timeout not reached and server responds, this imply `PAUSE` command success
    * If timeout is reached, server should abort the pause and throw an exception back to client.

