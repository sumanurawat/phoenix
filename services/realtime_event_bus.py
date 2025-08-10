"""Simple in-process pub/sub event bus for realtime updates via SSE.
Not production-grade; for single-process dev usage.
"""
from __future__ import annotations
import threading
from collections import defaultdict
from typing import Callable, Dict, List, Any

class RealtimeEventBus:
	def __init__(self):
		self._lock = threading.Lock()
		self._subscribers: Dict[str, List[Callable[[str, Any], None]]] = defaultdict(list)

	def subscribe(self, topic: str, callback: Callable[[str, Any], None]):
		with self._lock:
			self._subscribers[topic].append(callback)

	def unsubscribe(self, topic: str, callback: Callable[[str, Any], None]):
		with self._lock:
			self._subscribers[topic] = [c for c in self._subscribers[topic] if c != callback]

	def publish(self, topic: str, event: str, data: Any):
		with self._lock:
			subs = list(self._subscribers.get(topic, []))
		for cb in subs:
			try:
				cb(event, data)
			except Exception:
				pass

realtime_event_bus = RealtimeEventBus()
