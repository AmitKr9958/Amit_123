"""Playwright persistent browser context with manual auth support."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright
from rich.console import Console

from .config import DATA_DIR, ensure_data_dirs
from .selectors import LOGGED_IN_SELECTORS, LOGIN_CTA_SELECTORS

console = Console()
NAUKRI_HOME = "https://www.naukri.com/"
NAUKRI_LOGIN_HINTS = ("login", "nlogin", "mnjuser/login")


class BrowserSession:
    """Owns a persistent Chromium context so the user can log in once."""

    def __init__(
        self,
        user_data_dir: Path | None = None,
        headless: bool | None = None,
        channel: str | None = None,
    ) -> None:
        ensure_data_dirs()
        self.user_data_dir = user_data_dir or (DATA_DIR / "browser_profile")
        self.headless = (
            headless
            if headless is not None
            else os.getenv("HEADLESS", "false").lower() in ("1", "true", "yes")
        )
        self.channel = channel or os.getenv("BROWSER_CHANNEL", "chromium")
        self._playwright: Optional[Playwright] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def start(self) -> Page:
        self._playwright = await async_playwright().start()
        launch_args = {
            "user_data_dir": str(self.user_data_dir),
            "headless": self.headless,
            "viewport": {"width": 1366, "height": 900},
            "locale": "en-IN",
            "timezone_id": "Asia/Kolkata",
            "args": [
                "--disable-blink-features=AutomationControlled",
            ],
        }
        if self.channel and self.channel != "chromium":
            launch_args["channel"] = self.channel

        self.context = await self._playwright.chromium.launch_persistent_context(**launch_args)
        # Prefer existing page or open a fresh one
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()
        return self.page

    async def close(self) -> None:
        if self.context:
            await self.context.close()
        if self._playwright:
            await self._playwright.stop()

    async def goto(self, url: str, wait: str = "domcontentloaded") -> None:
        assert self.page
        await self.page.goto(url, wait_until=wait, timeout=60_000)

    async def is_logged_in(self) -> bool:
        """Heuristic: presence of profile / logout elements after visiting home."""
        assert self.page
        await self.goto(NAUKRI_HOME)
        await asyncio.sleep(2)
        url = self.page.url.lower()
        if any(h in url for h in NAUKRI_LOGIN_HINTS):
            return False
        for sel in LOGGED_IN_SELECTORS:
            try:
                el = await self.page.query_selector(sel)
                if el:
                    return True
            except Exception:
                continue
        for sel in LOGIN_CTA_SELECTORS:
            try:
                el = await self.page.query_selector(sel)
                if el:
                    return False
            except Exception:
                continue
        # URL not on login path and no login CTA → assume session OK
        return True

    async def ensure_authenticated(self, timeout_seconds: int = 300) -> None:
        """
        If not logged in, open login page and wait for the user to complete
        OTP / CAPTCHA / password manually. Never stores or types credentials.
        """
        assert self.page
        if await self.is_logged_in():
            console.print("[green]Session appears authenticated.[/green]")
            return

        console.print(
            "[yellow]Not logged in. Opening Naukri login page.\n"
            "Please complete login (password / OTP / CAPTCHA) in the browser window.\n"
            "Do not close the window. Waiting up to "
            f"{timeout_seconds}s...[/yellow]"
        )
        await self.goto("https://www.naukri.com/nlogin/login")
        deadline = asyncio.get_event_loop().time() + timeout_seconds
        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(5)
            if await self.is_logged_in():
                console.print("[green]Login detected. Continuing.[/green]")
                return
        raise TimeoutError(
            "Authentication timed out. Re-run after logging in manually, "
            "or increase the wait window."
        )

    async def human_delay(self, min_s: float = 2.0, max_s: float = 6.0) -> None:
        import random

        await asyncio.sleep(random.uniform(min_s, max_s))

    async def screenshot(self, name: str) -> Path:
        assert self.page
        path = DATA_DIR / "screenshots" / f"{name}.png"
        await self.page.screenshot(path=str(path), full_page=False)
        return path
