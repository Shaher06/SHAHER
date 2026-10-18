"""Platform-specific reminder delivery, hidden behind one small interface.

* InAppBackend       - Windows/desktop fallback. It can NOT notify while the app is closed.
                       ReminderService.due_in_app() is polled by the UI while the app is open.
* AndroidWorkManagerBackend - schedules real Android notifications through AndroidX WorkManager
                       (see android/src/org/shaher/reminders). WorkManager keeps scheduled work
                       across app restarts and device reboots. NOT yet verified on a device.
"""
import logging
from datetime import datetime

from app import config

log = logging.getLogger("shaher.reminders")


class ReminderBackend:
    name = "base"
    background = False          # True if reminders can fire while the app is closed

    def is_supported(self) -> bool:
        return False

    def notifications_allowed(self) -> bool:
        return True

    def request_permission(self) -> None:
        pass

    def schedule(self, key: str, title: str, body: str, fire_at: datetime) -> bool:
        raise NotImplementedError

    def schedule_daily(self, key: str, title: str, body: str, hhmm: str) -> bool:
        raise NotImplementedError

    def cancel(self, key: str) -> None:
        raise NotImplementedError


class InAppBackend(ReminderBackend):
    """Desktop fallback: nothing is scheduled with the OS."""
    name = "in_app"
    background = False

    def is_supported(self) -> bool:
        return True

    def schedule(self, key, title, body, fire_at) -> bool:
        return True     # the UI polls the database while the app is open

    def schedule_daily(self, key, title, body, hhmm) -> bool:
        return True

    def cancel(self, key) -> None:
        pass


class AndroidWorkManagerBackend(ReminderBackend):
    name = "android_workmanager"
    background = True
    JAVA_CLASS = "org.shaher.reminders.ReminderScheduler"
    NOTIF_PERMISSION = "android.permission.POST_NOTIFICATIONS"

    def __init__(self):
        self._scheduler = None
        self._context = None
        try:
            from jnius import autoclass   # only exists on Android
            self._scheduler = autoclass(self.JAVA_CLASS)
            self._context = autoclass("org.kivy.android.PythonActivity").mActivity
            self._sdk_int = autoclass("android.os.Build$VERSION").SDK_INT
        except Exception:
            log.exception("Android reminder classes are not available")

    def is_supported(self) -> bool:
        return self._scheduler is not None

    def _needs_runtime_permission(self) -> bool:
        return self._sdk_int >= 33

    def notifications_allowed(self) -> bool:
        if not self.is_supported():
            return False
        if not self._needs_runtime_permission():
            return True
        try:
            from android.permissions import check_permission
            return bool(check_permission(self.NOTIF_PERMISSION))
        except Exception:
            log.exception("permission check failed")
            return False

    def request_permission(self) -> None:
        if self.is_supported() and self._needs_runtime_permission():
            try:
                from android.permissions import request_permissions
                request_permissions([self.NOTIF_PERMISSION])
            except Exception:
                log.exception("permission request failed")

    def schedule(self, key, title, body, fire_at) -> bool:
        if not self.is_supported():
            return False
        millis = int(fire_at.timestamp() * 1000)     # naive local time -> epoch millis
        self._scheduler.schedule(self._context, key, title, body, millis)
        return True

    def schedule_daily(self, key, title, body, hhmm) -> bool:
        if not self.is_supported():
            return False
        hour, minute = (int(x) for x in hhmm.split(":"))
        self._scheduler.scheduleDaily(self._context, key, title, body, hour, minute)
        return True

    def cancel(self, key) -> None:
        if self.is_supported():
            self._scheduler.cancel(self._context, key)


def default_backend() -> ReminderBackend:
    if config.is_android():
        backend = AndroidWorkManagerBackend()
        if backend.is_supported():
            return backend
        log.warning("Falling back to in-app reminders")
    return InAppBackend()
