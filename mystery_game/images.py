from pathlib import Path

from PIL import Image, ImageOps, ImageTk


class ImageAssets:
    """Loads optional images from assets/images without allowing paths outside it."""

    ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

    def __init__(self, assets_dir):
        self.root = (Path(assets_dir) / "images").resolve()
        self._cache = {}

    def resolve(self, relative_path):
        if not isinstance(relative_path, str) or not relative_path.strip():
            return None
        candidate = Path(relative_path.strip())
        if candidate.is_absolute() or candidate.suffix.lower() not in self.ALLOWED_SUFFIXES:
            return None
        resolved = (self.root / candidate).resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError:
            return None
        return resolved if resolved.is_file() else None

    def load_fit(self, relative_path, size, centering=(0.5, 0.28)):
        path = self.resolve(relative_path)
        if path is None:
            return None
        key = (str(path), tuple(size), "fit", tuple(centering))
        if key in self._cache:
            return self._cache[key]
        try:
            with Image.open(path) as source:
                image = ImageOps.fit(source.convert("RGBA"), size, method=Image.Resampling.LANCZOS, centering=centering)
                photo = ImageTk.PhotoImage(image)
            self._cache[key] = photo
            return photo
        except (OSError, ValueError):
            return None

    def load(self, relative_path, size=None):
        path = self.resolve(relative_path)
        if path is None:
            return None
        key = (str(path), tuple(size) if size else None)
        if key in self._cache:
            return self._cache[key]
        try:
            with Image.open(path) as source:
                image = source.convert("RGBA")
                if size:
                    image.thumbnail(size, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
            self._cache[key] = photo
            return photo
        except (OSError, ValueError):
            return None
