try:
    import _winreg as winreg
    from .win32 import get_localzone, reload_localzone
except ImportError:
    try:
        import winreg
        from .win32 import get_localzone, reload_localzone
    except ImportError:
        from .unix import get_localzone, reload_localzone
