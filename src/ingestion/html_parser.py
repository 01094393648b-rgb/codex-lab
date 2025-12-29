"""HTML parsing utilities for extracting page metadata and body content.

This module fetches and parses HTML from either raw strings or remote URLs.
It returns the page title, meta description, and cleaned body text while
stripping script and style content.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from config.settings import get_settings


DEFAULT_TIMEOUT = 10


@dataclass
class ParsedPage:
    """Structured representation of parsed HTML content."""

    title: Optional[str]
    meta_description: Optional[str]
    body_text: str


def _is_url(source: str) -> bool:
    """Return True if the given source string resembles an absolute URL."""

    parsed = urlparse(source)
    return bool(parsed.scheme and parsed.netloc)


def _fetch_html(url: str, settings: Any) -> str:
    """Fetch HTML content from a URL using requests with sane defaults.

    Args:
        url: The URL to fetch.
        settings: Configuration object returned by ``get_settings``.

    Returns:
        Raw HTML string.

    Raises:
        requests.HTTPError: If the response contains an HTTP error status.
        requests.RequestException: For any network-related issues.
    """

    headers = {
        "User-Agent": getattr(
            settings,
            "user_agent",
            "Mozilla/5.0 (compatible; HTMLParserBot/1.0; +https://example.com/bot)",
        )
    }
    timeout = getattr(settings, "request_timeout", DEFAULT_TIMEOUT)
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return response.text


def _extract_meta_description(soup: BeautifulSoup) -> Optional[str]:
    """Extract the meta description tag content if available."""

    description_tag = soup.find("meta", attrs={"name": "description"})
    if description_tag:
        content = description_tag.get("content")
        if content:
            return content.strip()
    return None


def _clean_body_text(soup: BeautifulSoup) -> str:
    """Return visible body text with scripts, styles, and noisy elements removed."""

    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()

    body = soup.body or soup
    text = body.get_text(separator="\n", strip=True)
    lines = [line for line in text.splitlines() if line]
    return "\n".join(lines)


def parse_html(source: str) -> ParsedPage:
    """Parse HTML from a raw string or URL into structured content.

    The function determines whether the input is a URL or raw HTML. When
    fetching remote content, it uses configuration from ``config.settings``
    to set sensible defaults such as request timeout and User-Agent.

    Args:
        source: Raw HTML string or an absolute URL.

    Returns:
        ParsedPage containing the title, meta description, and cleaned body text.

    Raises:
        ValueError: If the source is empty.
        requests.RequestException: If fetching remote content fails.
    """

    if not source or not source.strip():
        raise ValueError("Source HTML or URL must be a non-empty string.")

    settings = get_settings()

    if _is_url(source):
        html = _fetch_html(source, settings)
    else:
        html = source

    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.string.strip() if soup.title and soup.title.string else None
    meta_description = _extract_meta_description(soup)
    body_text = _clean_body_text(soup)

    return ParsedPage(title=title, meta_description=meta_description, body_text=body_text)


__all__ = ["ParsedPage", "parse_html"]
