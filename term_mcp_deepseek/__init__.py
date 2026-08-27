"""Term MCP DeepSeek package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("term-mcp-deepseek")
except PackageNotFoundError:
    __version__ = "0.9.0"

__all__ = ["__version__"]
