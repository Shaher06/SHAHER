"""Small platform helpers. Everything is wrapped so a failure never crashes the app.
The Android parts use pyjnius and are NOT verified on a device yet."""
import logging
import sys

from app import config

log = logging.getLogger("shaher.platform")


def system_theme() -> str:
    """'dark' or 'light' according to the OS setting (falls back to 'light')."""
    try:
        if config.is_android():
            from jnius import autoclass
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            ui_mode = activity.getResources().getConfiguration().uiMode
            return "dark" if (ui_mode & 0x30) == 0x20 else "light"
        if sys.platform.startswith("win"):
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            return "light" if winreg.QueryValueEx(key, "AppsUseLightTheme")[0] else "dark"
    except Exception:
        log.debug("could not read system theme", exc_info=True)
    return "light"


def haptics_supported() -> bool:
    return config.is_android()


def vibrate(ms: int = 20) -> None:
    if not config.is_android():
        return
    try:
        from jnius import autoclass
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        vib = activity.getSystemService(autoclass("android.content.Context").VIBRATOR_SERVICE)
        vib.vibrate(int(ms))
    except Exception:
        log.debug("vibrate failed", exc_info=True)


def open_android_settings(kind: str) -> bool:
    """kind: 'notifications' | 'battery'. Returns False when not on Android or on failure."""
    if not config.is_android():
        return False
    try:
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        if kind == "notifications":
            intent = Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
            intent.putExtra(Settings.EXTRA_APP_PACKAGE, activity.getPackageName())
        else:
            intent = Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)
        activity.startActivity(intent)
        return True
    except Exception:
        log.exception("could not open settings")
        return False
