from __future__ import annotations  # Add this at the top of your file

import asyncio
from typing import Optional


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

    def __init__(self, pause_cb=None, resume_cb=None, name: Optional[str] = None):
        """
        Initializes a new Pausable instance.

        Args:
            pause_cb: An async function to be called when pausing.
            resume_cb: An async function to be called when resuming.
        """
        self.pause_cb = pause_cb
        self.resume_cb = resume_cb
        self.name: str = name if name is not None else str(id(self))
        if Pausable._controller is None:
            raise RuntimeError(
                "PausableController has not been set. Please initialize it in your main entry point."
            )

    async def maybe_pause(self) -> None:
        """Cooperate with the controller to pause/resume when requested."""
        await type(self)._controller.handle_pause(self)


class PausableController:
    """
    A central controller that manages the global pause and resume state.
    This object is intended to be a singleton, managed by the main script entrypoint.
    """

    def __init__(self):
        self._pause_requested = asyncio.Event()
        self._resume_requested = asyncio.Event()
        self._is_paused = False
        # Tracking for pause "generations" and coordinated multi-task pause
        self._pause_generation = 0
        self._expected_tasks = 0
        self._paused_tasks: set[str] = set()
        self._all_paused_event = asyncio.Event()

    def pause(self):
        """Called by an external entity (like a gRPC server) to request a pause."""
        if not self._is_paused:
            self._pause_generation += 1
            self._paused_tasks.clear()
            self._all_paused_event.clear()
            self._pause_requested.set()

    def resume(self):
        """Called by an external entity to request a resume."""
        if self._is_paused:
            # Allow paused tasks to proceed and ensure new calls won't re-enter pause immediately
            self._resume_requested.set()
            self._pause_requested.clear()

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    def set_expected_tasks(self, count: int) -> None:
        """Sets the expected number of cooperating tasks for coordinated pause.

        If set to 0, coordinated waiting is effectively disabled.
        """
        self._expected_tasks = max(0, int(count))

    async def wait_all_paused(self, timeout: Optional[float]) -> bool:
        """Wait until all expected tasks report paused for the current generation.

        Args:
            timeout: seconds to wait; None means indefinitely.

        Returns:
            True if all paused within timeout; False if timed out or coordination disabled.
        """
        # If coordination not requested, treat as immediately satisfied
        if self._expected_tasks <= 0:
            return True
        try:
            if timeout is None:
                await self._all_paused_event.wait()
                return True
            else:
                await asyncio.wait_for(self._all_paused_event.wait(), timeout=timeout)
                return True
        except asyncio.TimeoutError:
            return False

    async def handle_pause(self, pausable_instance: Pausable):
        """
        The core logic that checks for a pause request and manages the state.
        This is called by `Pausable.maybe_pause()`.
        """
        if self._pause_requested.is_set():
            self._is_paused = True

            # Mark this Pausable's task as paused for current generation 
            self._paused_tasks.add(pausable_instance.name)
            # print("paused tasks set:", self._paused_tasks)
            if self._expected_tasks > 0 and len(self._paused_tasks) >= self._expected_tasks:
                self._all_paused_event.set()

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
