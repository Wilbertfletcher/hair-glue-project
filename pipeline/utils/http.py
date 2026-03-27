import time
import functools
import random

class RateLimiter:
    def __init__(self, max_calls, period):
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            self.calls = [t for t in self.calls if now - t < self.period]
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
            result = func(*args, **kwargs)
            self.calls.append(time.time())
            return result
        return wrapper

def retry_with_backoff(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        max_attempts = 5
        delay = 1.0
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                sleep = delay * (2 ** attempt) + random.uniform(0, 0.5)
                time.sleep(sleep)
    return wrapper
