"""Contextual, respectful messages based on REAL local data. Returns (key, params) or None.

Principles: no shaming, no streak pressure, no fake numbers, never a popup - callers show
the result as a short banner/toast. 'off' and quiet mode silence everything.
"""
from datetime import datetime, timedelta
from typing import Callable, Optional, Tuple

from app.services.commitment_service import CommitmentService
from app.services.preferences import Preferences
from app.utils import dates

Message = Optional[Tuple[str, dict]]
BUSY_THRESHOLD = 4


class Encourager:
    def __init__(self, prefs: Preferences, commitments: CommitmentService,
                 now_fn: Callable[[], datetime] = dates.now):
        self.prefs, self.commitments, self.now = prefs, commitments, now_fn

    def enabled(self) -> bool:
        return self.prefs.get("encouragement") != "off" and not self.prefs.flag("quiet_mode")

    # ---- after the user completes something ----
    def on_completed(self) -> Message:
        if not self.enabled():
            return None
        done_today = self.commitments.completed_today()
        remaining = self.commitments.remaining_today()
        gentle = self.prefs.get("encouragement") == "gentle"
        if gentle:                        # at most once per 3 completions and 60 minutes
            count = self.prefs.int("enc_completed_count") + 1
            self.prefs.set("enc_completed_count", count)
            last = self.prefs.get("enc_last_ts")
            recent = bool(last) and self.now() - dates.parse_dt(last) < timedelta(minutes=60)
            if count % 3 != 0 or recent:
                return None
        if remaining == 0 and done_today >= 1:
            key = "enc.all_done"
        elif done_today >= 3:
            key = "enc.many_done"
        else:
            key = "enc.done_a" if self.prefs.get("enc_last_key") != "enc.done_a" else "enc.done_b"
        if key in ("enc.all_done", "enc.many_done") and key == self.prefs.get("enc_last_key"):
            return None                   # a milestone message is never repeated back to back
        self._remember(key)
        return key, {"n": done_today}

    # ---- calm line shown on the dashboard ----
    def home_message(self) -> Message:
        if not self.enabled():
            return None
        today = self.now().date()
        last = self.prefs.get("last_open_date")
        if last:
            gap = (today - dates.parse_date(last)).days
            if gap >= 3:
                return "enc.welcome_back", {}
        c = self.commitments.counts()
        busy = c["today"] + c["overdue"]
        if busy >= BUSY_THRESHOLD:
            return "enc.busy", {"n": busy}
        if c["overdue"] > 0:
            return "enc.overdue_soft", {"n": c["overdue"]}
        if c["today"] == 0:
            if self.commitments.completed_today() > 0:
                return "enc.all_done", {"n": self.commitments.completed_today()}
            return "enc.calm", {}
        return None

    def mark_opened(self) -> None:
        self.prefs.set("last_open_date", self.now().date().strftime(dates.DATE_FMT))

    def _remember(self, key: str) -> None:
        self.prefs.set("enc_last_key", key)
        self.prefs.set("enc_last_ts", dates.to_ts(self.now()))
