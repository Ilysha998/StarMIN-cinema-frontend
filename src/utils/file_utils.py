import os
import tempfile


ANDROID_PATHS = [
    "/data/media/0/Download",
    "/storage/emulated/0/Download",
]


def get_save_dir(subdir: str = "starmin") -> str:
    for base in ANDROID_PATHS:
        d = os.path.join(base, subdir)
        if _try_dir(d):
            return d

    try:
        import android.storage
        d = os.path.join(android.storage.get_documents_directory(), subdir)
        if _try_dir(d):
            return d
    except Exception:
        pass

    d = os.path.join(os.path.expanduser("~"), "Documents", subdir)
    if _try_dir(d):
        return d

    d = os.path.join(tempfile.gettempdir(), subdir)
    os.makedirs(d, exist_ok=True)
    return d


def _try_dir(d: str) -> bool:
    try:
        if not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
        test = os.path.join(d, ".w")
        with open(test, "w") as f:
            f.write("1")
        os.remove(test)
        return True
    except (OSError, PermissionError):
        return False
