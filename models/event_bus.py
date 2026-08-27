import queue
import threading
from uuid import uuid4


class EventBus:
    def __init__(self):
        self.queues: dict[str, dict[str, queue.Queue]] = {}
        self.lock = threading.Lock()

    def subscribe(self, session_id: str) -> tuple[str, queue.Queue]:
        with self.lock:
            subscriber_id = str(uuid4())
            subscriber_queue = queue.Queue(maxsize=256)
            self.queues.setdefault(session_id, {})[subscriber_id] = subscriber_queue
            return subscriber_id, subscriber_queue

    def unsubscribe(self, session_id: str, subscriber_id: str) -> None:
        with self.lock:
            subscribers = self.queues.get(session_id)
            if subscribers is None:
                return
            subscribers.pop(subscriber_id, None)
            if not subscribers:
                self.queues.pop(session_id, None)

    def publish(self, session_id: str, event: dict):
        with self.lock:
            subscribers = list(self.queues.get(session_id, {}).values())
        for subscriber_queue in subscribers:
            try:
                subscriber_queue.put_nowait(event)
            except queue.Full:
                try:
                    subscriber_queue.get_nowait()
                except queue.Empty:
                    pass
                subscriber_queue.put_nowait(event)

    def close(self, session_id: str):
        with self.lock:
            self.queues.pop(session_id, None)

    def subscriber_count(self, session_id: str) -> int:
        with self.lock:
            return len(self.queues.get(session_id, {}))


bus = EventBus()
