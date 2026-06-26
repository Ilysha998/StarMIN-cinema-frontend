import os
import sys
import tempfile


def get_save_dir(subdir: str = "starmin") -> str:
    if sys.platform == "android":
        d = _android_save_dir(subdir)
    else:
        d = os.path.join(os.path.expanduser("~"), "Documents", subdir)
    os.makedirs(d, exist_ok=True)
    return d


def _android_save_dir(subdir: str) -> str:
    candidates = [
        f"/data/media/0/Download/{subdir}",
    ]

    try:
        import android.storage
        candidates.insert(0, os.path.join(android.storage.get_documents_directory(), subdir))
    except Exception:
        pass

    candidates.append(os.path.join(tempfile.gettempdir(), subdir))

    for path in candidates:
        try:
            os.makedirs(path, exist_ok=True)
            test_file = os.path.join(path, ".write_test")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            return path
        except (OSError, PermissionError):
            continue

    fallback = os.path.join(tempfile.mkdtemp(), subdir)
    os.makedirs(fallback, exist_ok=True)
    return fallback
