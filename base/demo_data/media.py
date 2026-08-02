"""Copy bundled demo media into MEDIA_ROOT."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


def _copy_glob(src_dir: Path, dest_dir: Path, pattern: str) -> int:
    if not src_dir.exists():
        return 0
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src in src_dir.glob(pattern):
        if not src.is_file():
            continue
        dest = dest_dir / src.name
        shutil.copy2(src, dest)
        copied += 1
    return copied


def copy_demo_media(load_dir: Path | None = None) -> dict[str, int]:
    """
    Copy company icons and employee avatars into MEDIA_ROOT.

    Fixture image fields point at ``base/icon/*.png`` and
    ``employee/profile/avatar_*.jpg`` — without this step those URLs 404.
    """
    root = Path(load_dir) if load_dir else Path(settings.BASE_DIR) / "load_data"
    media = Path(settings.MEDIA_ROOT)

    icons = _copy_glob(root / "icons", media / "base" / "icon", "*.png")
    # Also accept legacy Horilla_*.png already under media if icons/ was empty
    if icons == 0:
        legacy = media / "base" / "icon"
        if legacy.exists():
            icons = len(list(legacy.glob("Horilla_*.png")))

    avatars = _copy_glob(
        root / "avatars", media / "employee" / "profile", "avatar_*.jpg"
    )
    if avatars == 0:
        avatars = _copy_glob(root / "avatars", media / "employee" / "profile", "*.jpg")

    logger.info("Demo media copied: icons=%s avatars=%s", icons, avatars)
    return {"icons": icons, "avatars": avatars}
