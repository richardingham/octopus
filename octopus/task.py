from typing import Awaitable, Callable, Any
import asyncio
import functools

# From asyncio.tasks
def release_waiter(waiter, *args):
    if not waiter.done():
        waiter.set_result(None)

# From asyncio.tasks
async def cancel_and_wait(fut, loop):
    """Cancel the *fut* future or task and wait until it completes."""

    waiter = loop.create_future()
    cb = functools.partial(release_waiter, waiter)
    fut.add_done_callback(cb)

    try:
        fut.cancel()
        # We cannot wait on *fut* directly to make
        # sure cancel_and_wait itself is reliably cancellable.
        await waiter
    finally:
        fut.remove_done_callback(cb)

class PausableSleep():
    def __init__(self, delay, result=None):
        self._cancelled = False
        self._fut = None
        self._handle = None
        self._loop = asyncio.get_running_loop()
        self._paused = False
        self._remaining = delay
        self._result = result
        self._origin = 0

    def __await__(self):
        if self._fut is not None:
            raise asyncio.InvalidStateError("PausableSleep can only be awaited once")

        self._fut = self._loop.create_future()
        self._schedule()

        try:
            yield from self._fut
        finally:
            self._handle.cancel()

    def _schedule(self):
        self._origin = self._loop.time()
        self._handle = self._loop.call_later(
            self._remaining,
            asyncio.futures._set_result_unless_cancelled,
            self._fut,
            self._result,
        )

    def cancel(self, msg=None):
        if self._cancelled or (not self._handle) or self._fut.done():
            return

        self._cancelled = True
        self._handle.cancel()
        self._fut.cancel(msg=msg)

    def pause(self):
        if self._cancelled or self._paused or (not self._handle) or self._fut.done():
            return

        self._paused = True
        self._handle.cancel()
        self._remaining -= (self._loop.time() - self._origin)
        self._origin = self._loop.time()

    def resume(self):
        if self._cancelled or (not self._paused) or (not self._handle) or self._fut.done():
            return

        self._paused = False
        self._schedule()

    def __repr__(self):
        repr_info = []

        if not self._handle:
            repr_info.append("NOT STARTED")
            repr_info.append(f"delay={self._remaining:.1f}")

        elif self._fut.done():
            repr_info.append("COMPLETE")

        elif self._cancelled:
            repr_info.append("CANCELLED")

        elif self._paused:
            repr_info.append("PAUSED")
            repr_info.append(f"remaining={self._remaining:.1f}")
            repr_info.append(f"paused_at={self._origin:.1f}")

        else:
            repr_info.append("PENDING")
            remaining = self._origin + self._remaining - self._loop.time()
            repr_info.append(f"remaining={remaining:.1f}")

        return '<{} {}>'.format(self.__class__.__name__,
                                ' '.join(repr_info))


class LoopingCall():
    running: bool = False
    paused: bool = False
    interval: float = None
    _run_at_start: bool = False
    start_time: float = None

    def __init__(self, f, *a, **kw):
        self.f = f
        self.a = a
        self.kw = kw

        self._loop = asyncio.get_event_loop()
        self._waiter = None
        self._must_cancel = False

        self.resumed = asyncio.Event()

    def _next_wait_time(self, when: float) -> float:
        """
        Calculate the time to wait until the next iteration of this looping call.
        @param when: The present time from whence the call is scheduled.
        """

        # How long should it take until the next invocation of our
        # callable?  Split out into a function because there are multiple
        # places we want to 'return' out of this.
        if self.interval == 0:
            # If the interval is 0, just go as fast as possible, always
            # return zero, call ourselves ASAP.
            return 0

        # Compute the time until the next interval; how long has this call
        # been running for?
        running_for = when - self.start_time

        # And based on that start time, when does the current interval end?
        until_next_interval = self.interval - (running_for % self.interval)

        # Now that we know how long it would be, we have to tell if the
        # number is effectively zero.  However, we can't just test against
        # zero.  If a number with a small exponent is added to a number
        # with a large exponent, it may be so small that the digits just
        # fall off the end, which means that adding the increment makes no
        # difference; it's time to tick over into the next interval.
        if when == when + until_next_interval:
            # If it's effectively zero, then we need to add another
            # interval.
            return self.interval
    
        # Finally, if everything else is normal, we just return the
        # computed delay.
        return until_next_interval

    async def run(self, interval:float, now:bool = True):
        import inspect

        if interval < 0:
            raise ValueError("interval must be >= 0")

        if self.running == True:
            raise asyncio.InvalidStateError("LoopingCall is already running")

        self.running = True
        self.paused = False
        self.resumed.set()
        self._must_cancel = False

        # Loop might fail to start and then self._deferred will be cleared.
        # This why the local C{deferred} variable is used.

        self.start_time = self._loop.time()
        self.interval = interval
        self._run_at_start = now

        if not now:
            self._waiter = PausableSleep(self._next_wait_time(self.start_time))
            await self._waiter

        try:
            while True:
                if self.paused:
                    self._waiter = self.resumed.wait()
                    await self._waiter

                if not self.running or self._must_cancel:
                    break

                result = self.f(*self.a, **self.kw)
                if inspect.isawaitable(result):
                    self._waiter = result
                    result = await result

                if self.running:
                    self._waiter = PausableSleep(self._next_wait_time(self._loop.time()))
                    await self._waiter

        finally:
            self.running = False
            self._must_cancel = False

    def cancel(self):
        """Stop running function."""
        if self.running:
            self.running = False
            self._must_cancel = True

            if self._waiter is not None:
                self._waiter.cancel()
                self._waiter = None

    def pause(self):
        self.paused = True
        self.resumed.clear()

        try:
            self._waiter.pause()
        except AttributeError:
            pass

    def resume(self):
        self.paused = False
        self.resumed.set()

        try:
            self._waiter.pause()
        except AttributeError:
            pass

    def __repr__(self) -> str:
        import reflect 

        if hasattr(self.f, "__qualname__"):
            func = self.f.__qualname__
        elif hasattr(self.f, "__name__"):
            func = self.f.__name__
            if hasattr(self.f, "im_class"):
                func = self.f.im_class.__name__ + "." + func
        else:
            func = reflect.safe_repr(self.f)

        return "LoopingCall<{!r}>({}, *{}, **{})".format(
            self.interval,
            func,
            reflect.safe_repr(self.a),
            reflect.safe_repr(self.kw),
        )
