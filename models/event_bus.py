import time, queue, threading
from typing import Dict

class EventBus:
    def __init__(self):
        self.queues: Dict[str, queue.Queue] = {}
        self.lock = threading.Lock()

    def get(self, session_id: str) -> queue.Queue:
        with self.lock:
            q = self.queues.get(session_id)
            if q is None:
                q = queue.Queue(maxsize=1024)
                self.queues[session_id] = q
            return q

    def publish(self, session_id: str, event: dict):
        q = self.get(session_id)
        try:
            q.put_nowait(event)
        except queue.Full:
            # drop oldest to keep stream live
            try: q.get_nowait()
            except Exception: pass
            q.put_nowait(event)

    def close(self, session_id: str):
        with self.lock:
            self.queues.pop(session_id, None)

bus = EventBus()