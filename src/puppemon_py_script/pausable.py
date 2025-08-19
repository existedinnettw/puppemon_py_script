from __future__ import annotations  # Add this at the top of your file

import asyncio


class Pausable:
    """
    A non-singleton class that represents a point in the code that can be paused.
    Each instance can have its own pause and resume callbacks.
    It relies on a central PausableController to manage the global pause/resume state.
    """

    _controller: PausableController

    @classmethod
    def set_controller(cls, controller):
        """Sets the central controller for all Pausable instances."""
        cls._controller = controller

    def __init__(self, pause_cb=None, resume_cb=None):
        """
        Initializes a new Pausable instance.

        Args:
            pause_cb: An async function to be called when pausing.
            resume_cb: An async function to be called when resuming.
        """
        self.pause_cb = pause_cb
        self.resume_cb = resume_cb
        if Pausable._controller is None:
            raise RuntimeError(
                "PausableController has not been set. Please initialize it in your main entry point."
            )

    async def maybe_pause(self):
        """
        Checks if a pause has been requested by the controller and, if so,
        executes the pause/resume logic for this specific instance.
        """
        await Pausable._controller.handle_pause(self)


class PausableController:
    """
    A central controller that manages the global pause and resume state.
    This object is intended to be a singleton, managed by the main script entrypoint.
    """

    def __init__(self):
        self._pause_requested = asyncio.Event()
        self._resume_requested = asyncio.Event()
        self._is_paused = False

    def pause(self):
        """Called by an external entity (like a gRPC server) to request a pause."""
        if not self._is_paused:
            self._pause_requested.set()

    def resume(self):
        """Called by an external entity to request a resume."""
        if self._is_paused:
            self._resume_requested.set()

    async def handle_pause(self, pausable_instance: Pausable):
        """
        The core logic that checks for a pause request and manages the state.
        This is called by `Pausable.maybe_pause()`.
        """
        if self._pause_requested.is_set():
            self._is_paused = True
            self._pause_requested.clear()

            # Execute the specific instance's pause callback
            if pausable_instance.pause_cb:
                await pausable_instance.pause_cb()

            # Wait for the global resume signal
            await self._resume_requested.wait()
            self._resume_requested.clear()

            # Execute the specific instance's resume callback
            if pausable_instance.resume_cb:
                await pausable_instance.resume_cb()

            self._is_paused = False
