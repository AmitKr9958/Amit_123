"""Playwright persistent browser context with manual auth support."""

from __future__ import annotations

import asyncio
import os
import random
from pathlib import Path

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright
from rich.console import Console

from .config import DATA_DIR, ensure_data_dirs
from .selectors import LOGGED_IN_SELECTORS, LOGIN_CTA_SELECTORS

console = Console()
NAUKRI_HOME = "https://www.naukri.com/"
NAUKRI_LOGIN_HINTS = ("login", "nlogin", "mnjuser/login")


class BrowserSession:
    """Owns a persistent Microsoft Edge context so the user can log in once."""

    def __init__(
        self,
        user_data_dir: Path | None = None,
        headless: bool | None = None,
        channel: str | None = None,
    ) -> None:
        ensure_data_dirs()
        self.channel = channel or os.getenv("BROWSER_CHANNEL", "msedge")
        configured_profile = os.getenv("BROWSER_USER_DATA_DIR")
        if user_data_dir is not None:
            self.user_data_dir = user_data_dir
        elif configured_profile:
            self.user_data_dir = Path(configured_profile).expanduser()
        else:
            # Keep Edge's profile separate from any older Playwright Chromium profile.
            profile_name = "browser_profile" if self.channel == "chromium" else "edge_profile"
            self.user_data_dir = DATA_DIR / profile_name
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.headless = (
            headless
            if headless is not None
            else os.getenv("HEADLESS", "false").lower() in ("1", "true", "yes")
        )
        self._playwright: Playwright | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def start(self) -> Page:
        self._playwright = await async_playwright().start()
        launch_args = {
            "user_data_dir": str(self.user_data_dir),
            "headless": self.headless,
            "viewport": {"width": 1366, "height": 900},
            "locale": "en-IN",
            "timezone_id": "Asia/Kolkata",
        }
        if self.channel and self.channel != "chromium":
            launch_args["channel"] = self.channel

        self.context = await self._playwright.chromium.launch_persistent_context(**launch_args)
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
        return True

    async def ensure_authenticated(self, timeout_seconds: int = 300) -> None:
        """
        Reuse an authenticated session or wait for the user to complete login.
        Credentials are never stored or typed; OTP / CAPTCHA / MFA remain manual.
        """
        assert self.page
        if await self.is_logged_in():
            console.print("[green]Session appears authenticated.[/green]")
            return

        console.print(
            "[yellow]Not logged in. Opening Naukri login page.\n"
            "Complete password / OTP / CAPTCHA / MFA in the Edge window.\n"
            "Do not close the window. Waiting up to "
            f"{timeout_seconds}s...[/yellow]"
        )
        await self.goto("https://www.naukri.com/nlogin/login")
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds
        while loop.time() < deadline:
            await asyncio.sleep(5)
            if await self.is_logged_in():
                console.print("[green]Login detected. Continuing.[/green]")
                return
        raise TimeoutError(
            "Authentication timed out. Re-run after completing login manually, "
            "or increase the wait window."
        )

    async def human_delay(self, min_s: float = 2.0, max_s: float = 6.0) -> None:
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def screenshot(self, name: str) -> Path:
        assert self.page
        path = DATA_DIR / "screenshots" / f"{name}.png"
        await self.page.screenshot(path=str(path), full_page=False)
        return path
