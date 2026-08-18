"""Single source of truth for the package version.

The version is declared once in ``pyproject.toml`` and read back from the
installed distribution metadata, so ``tappay.__version__`` and the
``User-Agent`` header can never drift from the published package.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("tappay")
except PackageNotFoundError:  # pragma: no cover - running from an uninstalled checkout
    __version__ = "0.0.0.dev0"

__all__ = ["__version__"]
