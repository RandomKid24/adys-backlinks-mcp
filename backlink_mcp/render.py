"""Optional JavaScript rendering for client-side apps (React/Vite, Vue, Angular, CRA...).

Install once to enable:  pip install "backlink-mcp[render]" && python -m playwright install chromium
Without it, everything still works - JS-only pages are just reported as client-rendered.
"""
from __future__ import annotations

import asyncio

_UNAVAILABLE_REASON: str | None = None


def available() -> bool:
    global _UNAVAILABLE_REASON
    try:
        import playwright.async_api  # noqa: F401
        return True
    except Exception as e:  # noqa: BLE001
        _UNAVAILABLE_REASON = f"{type(e).__name__}: {e}"
        return False


def install_hint() -> str:
    return ('JS rendering is off. To crawl React/Vite/Vue apps properly run: '
            'pip install "backlink-mcp[render]" && python -m playwright install chromium')


class Renderer:
    """One headless browser reused for a whole crawl."""

    def __init__(self, user_agent: str, timeout_ms: int = 20000):
        self.ua, self.timeout = user_agent, timeout_ms
        self._pw = self._browser = self._ctx = None
        self.error: str | None = None

    async def __aenter__(self):
        try:
            from playwright.async_api import async_playwright
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch()
            self._ctx = await self._browser.new_context(user_agent=self.ua, java_script_enabled=True)
        except Exception as e:  # noqa: BLE001 - browser missing, sandbox issues, etc.
            self.error = (f"{type(e).__name__}: {str(e).splitlines()[0][:200]}. "
                          "Run: python -m playwright install chromium")
            await self.__aexit__()
        return self

    async def __aexit__(self, *exc):
        for obj, meth in ((self._ctx, "close"), (self._browser, "close"), (self._pw, "stop")):
            if obj is not None:
                try:
                    await getattr(obj, meth)()
                except Exception:  # noqa: BLE001
                    pass
        self._ctx = self._browser = self._pw = None

    @property
    def ok(self) -> bool:
        return self._ctx is not None

    async def fetch(self, url: str) -> dict:
        """Returns {url, status, html} or {url, error}."""
        if not self.ok:
            return {"url": url, "error": self.error or "renderer not started"}
        page = await self._ctx.new_page()
        try:
            try:
                resp = await page.goto(url, wait_until="networkidle", timeout=self.timeout)
            except Exception:  # noqa: BLE001 - long-polling sites never go idle; take what loaded
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                await asyncio.sleep(1.5)
            html = await page.content()
            return {"url": page.url, "status": resp.status if resp else 200, "html": html}
        except Exception as e:  # noqa: BLE001
            return {"url": url, "error": f"{type(e).__name__}: {str(e).splitlines()[0][:160]}"}
        finally:
            await page.close()

    async def fetch_many(self, urls: list[str], concurrency: int = 4) -> list[dict]:
        sem = asyncio.Semaphore(concurrency)

        async def one(u):
            async with sem:
                return await self.fetch(u)
        return await asyncio.gather(*(one(u) for u in urls))
