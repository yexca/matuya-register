import atexit
import logging
import threading
from concurrent.futures import ThreadPoolExecutor


logger = logging.getLogger(__name__)


class TaskRunner:
    def __init__(self, max_workers):
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="registration"
        )
        self._stop_event = threading.Event()
        self._periodic_threads = []

    def submit(self, fn, *args, **kwargs):
        future = self.executor.submit(fn, *args, **kwargs)
        future.add_done_callback(self._log_uncaught_exception)
        return future

    def shutdown(self):
        self._stop_event.set()
        self.executor.shutdown(wait=False, cancel_futures=False)

    def start_periodic(self, interval_seconds, fn):
        def loop():
            while not self._stop_event.wait(interval_seconds):
                try:
                    fn()
                except Exception:
                    logger.exception("uncaught periodic task exception")

        thread = threading.Thread(
            target=loop,
            name="registration-auto-refill",
            daemon=True,
        )
        thread.start()
        self._periodic_threads.append(thread)
        return thread

    def _log_uncaught_exception(self, future):
        try:
            future.result()
        except Exception:
            logger.exception("uncaught registration task exception")


def get_task_runner(app):
    runner = app.extensions.get("task_runner")
    if runner is None:
        runner = TaskRunner(app.config["APP_CONFIG"].batch_max_workers)
        app.extensions["task_runner"] = runner
        atexit.register(runner.shutdown)
    return runner
