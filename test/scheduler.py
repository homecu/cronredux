"""
Test scheduler logic.
"""

import time
from cronredux import scheduler


class TestTask(scheduler.Task):

    def __init__(self, *args, on_call=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_hist = []
        self.state_ts_hist = []
        self.set_state('init')
        self.on_call = on_call
        self.run_count = 0

    def set_state(self, value):
        self.state_hist.append(value)
        self.state_ts_hist.append(time.monotonic())

    def __call__(self):
        self.set_state('run')
        if self.on_call is not None:
            self.on_call()
        self.set_state('done')
