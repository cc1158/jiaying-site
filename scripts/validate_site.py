#!/usr/bin/env python3
"""Validate the static Jiaying compliance site with only the Python standard library."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    Path("index.html"): "zh-CN",
    Path("download/index.html"): "zh-CN",
    Path("privacy/index.html"): "zh-CN",
    Path("support/index.html"): "zh-CN",
    Path("en/index.html"): "en",
    Path("en/download/index.html"): "en",
    Path("en/privacy/index.html"): "en",
    Path("en/support/index.html"): "en",
}
PUBLIC_URLS = (
    "https://cc1158.github.io/jiaying-site/",
    "https://cc1158.github.io/jiaying-site/download/",
    "https://cc1158.github.io/jiaying-site/privacy/",
    "https://cc1158.github.io/jiaying-site/support/",
    "https://cc1158.github.io/jiaying-site/en/",
    "https://cc1158.github.io/jiaying-site/en/download/",
    "https://cc1158.github.io/jiaying-site/en/privacy/",
    "https://cc1158.github.io/jiaying-site/en/support/",
)
ISSUE_URL_PREFIX = "https://github.com/cc1158/jiaying-site/issues/new"
RELEASE_URL_PREFIX = "https://github.com/cc1158/jiaying-releases/releases/"
RELEASE_URL = f"{RELEASE_URL_PREFIX}tag/v1.0.0"
RELEASE_API_URL = (
    "https://api.github.com/repos/cc1158/jiaying-releases/releases/tags/v1.0.0"
)
RELEASE_ASSET_BASE = f"{RELEASE_URL_PREFIX}download/v1.0.0/"
RELEASE_ASSETS = {
    "family-media-server-linux-amd64": (
        "sha256:cf230e48f7131a2ece9e2fea0787b555a402d887010fa846078d4b58b223494b"
    ),
    "family-media-server-linux-amd64.sha256": (
        "sha256:56120cf9a2eae39b4b814cea817e53f7147f2f6e2b31ec4a66b9e84c02fc2ea1"
    ),
    "family-media-server-1.0.0-linux-amd64.tar": (
        "sha256:feee5f346e7ede1697bf8e844f49dff75a9896ebb5000a17a33206b3c983b30e"
    ),
    "family-media-server-1.0.0-linux-amd64.tar.sha256": (
        "sha256:85495ec7be9e96c5e037e67c50a7ae057ae0fdf2c1e1c4cce0e44f00dd4143df"
    ),
    "config.nas.example.yaml": (
        "sha256:06f941e98065223fe5c632eeefaeeab58aa6ee3841b3df736e4028f386e9389d"
    ),
}
PENDING_MARKER = "SUPPORT_EMAIL_PENDING"
MAIL_RE = re.compile(r"^mailto:([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})$", re.IGNORECASE)
FORBIDDEN_HOSTS = {
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "www.googletagmanager.com",
    "www.google-analytics.com",
    "connect.facebook.net",
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang: str | None = None
        self.links: list[tuple[str, str, str, str]] = []
        self.h1_count = 0
        self.main_count = 0
        self.title_count = 0
        self.script_count = 0
        self.form_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html":
            self.lang = values.get("lang")
        elif tag == "a" and values.get("href"):
            self.links.append((tag, "href", values["href"] or "", ""))
        elif tag == "link" and values.get("href"):
            self.links.append((tag, "href", values["href"] or "", values.get("rel") or ""))
        elif tag == "img" and values.get("src"):
            self.links.append((tag, "src", values["src"] or "", ""))
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "main":
            self.main_count += 1
        elif tag == "title":
            self.title_count += 1
        elif tag == "script":
            self.script_count += 1
        elif tag == "form":
            self.form_count += 1


def resolve_local(page: Path, raw_link: str) -> Path | None:
    parsed = urlparse(raw_link)
    if parsed.scheme or raw_link.startswith("//") or raw_link.startswith("#"):
        return None

    path_text = unquote(parsed.path)
    if not path_text:
        return None

    candidate = (ROOT / page.parent / path_text).resolve()
    try:
        relative = candidate.relative_to(ROOT)
    except ValueError:
        return Path("__outside_site__")

    if path_text.endswith("/"):
        relative /= "index.html"
    return relative


def validate_pages(app_store_ready: bool) -> list[str]:
    errors: list[str] = []
    collected_mailboxes: dict[Path, set[str]] = {}

    for page, expected_lang in PAGES.items():
        full_path = ROOT / page
        if not full_path.is_file():
            errors.append(f"missing required page: {page}")
            continue

        source = full_path.read_text(encoding="utf-8")
        parser = PageParser()
        parser.feed(source)

        if parser.lang != expected_lang:
            errors.append(f"{page}: expected html lang={expected_lang!r}, found {parser.lang!r}")
        if parser.h1_count != 1:
            errors.append(f"{page}: expected exactly one h1, found {parser.h1_count}")
        if parser.main_count != 1:
            errors.append(f"{page}: expected exactly one main element, found {parser.main_count}")
        if parser.title_count != 1:
            errors.append(f"{page}: expected exactly one title element, found {parser.title_count}")
        if parser.script_count:
            errors.append(f"{page}: scripts are not allowed")
        if parser.form_count:
            errors.append(f"{page}: forms are not allowed")
        if "—" in source or "–" in source:
            errors.append(f"{page}: forbidden long dash character found")

        mailboxes: set[str] = set()
        for tag, attribute, link, relation in parser.links:
            parsed = urlparse(link)
            if parsed.netloc.lower() in FORBIDDEN_HOSTS:
                errors.append(f"{page}: forbidden remote host in {attribute}: {parsed.netloc}")
            if parsed.scheme == "mailto":
                match = MAIL_RE.fullmatch(link)
                if not match:
                    errors.append(f"{page}: invalid mailto link: {link}")
                else:
                    mailboxes.add(match.group(1).lower())
                continue
            if parsed.scheme in {"http", "https"}:
                if parsed.scheme != "https":
                    errors.append(f"{page}: external links must use HTTPS: {link}")
                elif tag == "a" and not link.startswith(
                    (ISSUE_URL_PREFIX, RELEASE_URL_PREFIX)
                ):
                    errors.append(f"{page}: unexpected external link: {link}")
                elif tag == "link" and (
                    relation not in {"canonical", "alternate"}
                    or parsed.netloc != "cc1158.github.io"
                ):
                    errors.append(f"{page}: unexpected remote link resource: {link}")
                elif tag not in {"a", "link"}:
                    errors.append(f"{page}: remote {tag} resources are not allowed: {link}")
                continue
            local = resolve_local(page, link)
            if local is not None and not (ROOT / local).is_file():
                errors.append(f"{page}: broken internal {attribute}: {link}")
        collected_mailboxes[page] = mailboxes

    required_files = (
        Path(".nojekyll"),
        Path("assets/styles.css"),
        Path("assets/app-icon.png"),
        Path(".github/ISSUE_TEMPLATE/support.yml"),
        Path(".github/workflows/validate.yml"),
    )
    for required in required_files:
        if not (ROOT / required).is_file():
            errors.append(f"missing required file: {required}")

    stylesheet = (ROOT / "assets/styles.css").read_text(encoding="utf-8")
    if re.search(r"@import\s|url\(\s*['\"]?https?://", stylesheet, re.IGNORECASE):
        errors.append("assets/styles.css: remote CSS resources are not allowed")

    zh_privacy = (ROOT / "privacy/index.html").read_text(encoding="utf-8")
    en_privacy = (ROOT / "en/privacy/index.html").read_text(encoding="utf-8")
    privacy_claims = {
        "privacy/index.html": (
            ("不跟踪", zh_privacy),
            ("不展示广告", zh_privacy),
            ("不会持久化保存", zh_privacy),
            ("系统 Keychain", zh_privacy),
            ("设备与你指定", zh_privacy),
            ("不使用 Cookie", zh_privacy),
        ),
        "en/privacy/index.html": (
            ("does not track", en_privacy),
            ("show ads", en_privacy),
            ("is not persisted", en_privacy),
            ("system Keychain", en_privacy),
            ("device running Jiaying", en_privacy),
            ("uses no cookies", en_privacy),
        ),
    }
    for page_name, claims in privacy_claims.items():
        for phrase, source in claims:
            if phrase not in source:
                errors.append(f"{page_name}: missing required privacy statement: {phrase!r}")

    support_pages = (Path("support/index.html"), Path("en/support/index.html"))
    for page in support_pages:
        source = (ROOT / page).read_text(encoding="utf-8")
        if source.count(ISSUE_URL_PREFIX) != 1:
            errors.append(f"{page}: expected exactly one GitHub Issues support link")

    download_pages = (Path("download/index.html"), Path("en/download/index.html"))
    for page in download_pages:
        source = (ROOT / page).read_text(encoding="utf-8")
        if RELEASE_URL not in source:
            errors.append(f"{page}: missing the public v1.0.0 release link")
        for asset in RELEASE_ASSETS:
            if f"{RELEASE_ASSET_BASE}{asset}" not in source:
                errors.append(f"{page}: missing release asset link: {asset}")
        for phrase in ("x86_64", "sha256", "/media/library", "/data"):
            if phrase not in source:
                errors.append(f"{page}: missing NAS installation detail: {phrase!r}")
    all_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in {".html", ".md", ".yml"}
    )
    if app_store_ready:
        if PENDING_MARKER in all_sources:
            errors.append(f"app-store-ready: remove every {PENDING_MARKER} marker")
        support_mailboxes = [collected_mailboxes.get(path, set()) for path in support_pages]
        if any(len(mailboxes) != 1 for mailboxes in support_mailboxes):
            errors.append("app-store-ready: each Chinese and English support page needs one valid mailto link")
        elif support_mailboxes[0] != support_mailboxes[1]:
            errors.append("app-store-ready: Chinese and English support pages must use the same mailbox")
        else:
            mailbox = next(iter(support_mailboxes[0]))
            if mailbox.endswith(("@example.com", "@example.org", "@example.net")):
                errors.append("app-store-ready: placeholder email domains are not allowed")
    else:
        support_sources = [(ROOT / page).read_text(encoding="utf-8") for page in support_pages]
        pending_states = [PENDING_MARKER in source for source in support_sources]
        support_mailboxes = [collected_mailboxes.get(path, set()) for path in support_pages]
        if any(pending_states) and not all(pending_states):
            errors.append("preview: Chinese and English support pages must use the same email state")
        elif all(pending_states):
            if any(support_mailboxes):
                errors.append("preview: mailto links must not be published while email is pending")
        elif any(len(mailboxes) != 1 for mailboxes in support_mailboxes):
            errors.append("preview: configured Chinese and English support pages each need one valid mailto link")
        elif support_mailboxes[0] != support_mailboxes[1]:
            errors.append("preview: Chinese and English support pages must use the same mailbox")

    return errors


def remote_status(url: str) -> int:
    request = urllib.request.Request(url, headers={"User-Agent": "jiaying-site-validator/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except urllib.error.URLError:
        return 0


def validate_release_assets() -> list[str]:
    errors: list[str] = []
    request = urllib.request.Request(
        RELEASE_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "jiaying-site-validator/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            release = json.load(response)
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as error:
        return [f"app-store-ready: cannot inspect public release assets: {error}"]

    assets = {asset.get("name"): asset for asset in release.get("assets", [])}
    for name, expected_digest in RELEASE_ASSETS.items():
        asset = assets.get(name)
        if asset is None:
            errors.append(f"app-store-ready: public release is missing asset: {name}")
            continue
        if asset.get("state") != "uploaded" or not asset.get("size"):
            errors.append(f"app-store-ready: public release asset is incomplete: {name}")
        if asset.get("digest") != expected_digest:
            errors.append(f"app-store-ready: public release asset digest changed: {name}")
    return errors


def validate_remote() -> list[str]:
    errors: list[str] = []
    for url in (
        *PUBLIC_URLS,
        f"{ISSUE_URL_PREFIX}?template=support.yml",
        RELEASE_URL,
    ):
        status = remote_status(url)
        if not 200 <= status < 400:
            errors.append(f"app-store-ready: public support resource unavailable ({status or 'network error'}): {url}")
    errors.extend(validate_release_assets())
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--app-store-ready",
        action="store_true",
        help="require a real support email and verify the deployed public URLs",
    )
    args = parser.parse_args()

    errors = validate_pages(args.app_store_ready)
    if args.app_store_ready and not errors:
        errors.extend(validate_remote())

    if errors:
        print("Site validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    mode = "App Store ready" if args.app_store_ready else "preview"
    print(f"Site validation passed in {mode} mode for {len(PAGES)} pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
