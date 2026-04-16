// Lightweight event bus for cross-module communication
const listeners = {};

export const events = {
  on(event, fn) {
    if (!listeners[event]) listeners[event] = [];
    listeners[event].push(fn);
  },
  off(event, fn) {
    if (!listeners[event]) return;
    listeners[event] = listeners[event].filter(f => f !== fn);
  },
  emit(event, data) {
    if (!listeners[event]) return;
    listeners[event].forEach(fn => fn(data));
  },
};
