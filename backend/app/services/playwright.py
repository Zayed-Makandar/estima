import asyncio
import os
import re
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional
from urllib.parse import quote_plus, urljoin

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


class PlaywrightService:
    def __init__(self, headless: Optional[bool] = None, browser_type: Optional[str] = None):
        self.headless = _env_bool("PLAYWRIGHT_HEADLESS", False if headless is None else headless)
        self.browser_type = browser_type or os.getenv("PLAYWRIGHT_BROWSER", "chromium")
        self._browser: Optional[Browser] = None
        self._playwright: Any = None
        self._lock = asyncio.Lock()

    async def _ensure_browser(self) -> Browser:
        async with self._lock:
            if self._browser:
                return self._browser
            self._playwright = await async_playwright().start()
            # Launch persistent browser instance with Cloudflare bypass args
            self._browser = await getattr(self._playwright, self.browser_type).launch(
                headless=self.headless,
                args=[
                    "--no-sandbox", 
                    "--disable-setuid-sandbox", 
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            return self._browser

    async def _setup_page(self, page: Page):
        # Resource blocking removed as it causes timeouts on some sites (Robu)
        pass

    @asynccontextmanager
    async def page(self) -> AsyncIterator[Page]:
        browser = await self._ensure_browser()
        # Create a new page (tab) in the shared browser
        # Using a fresh context per page is safer for isolation but slightly heavier.
        # For pure scraping, a single context is usually fine, but let's do new_context per request
        # to ensure no cookie/session leak between searches.
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        await self._setup_page(page)
        try:
            yield page
        finally:
            await page.close()
            await context.close()

    async def search(self, adapter: Dict[str, Any], query: str, limit: int = 6, source_key: str = "") -> Dict[str, Any]:
        browser = await self._ensure_browser()
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await self._setup_page(page)
        
        try:
            search_url = adapter["base_url"] + adapter["search_path"].format(query=quote_plus(query))
            # DOMContentLoaded is much faster than load/networkidle
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

            name = adapter["name"].lower()

            # REMOVED: Unconditional networkidle wait. It's too slow.
            # We now rely on specific selector waits below.
            
            # Robu: Electro theme might be fast but needs selector wait. 
            # Networkidle was timing out, so we use standard selector wait below.
            if name.startswith("robu"):
                pass 


            wait_after_ms = adapter.get("wait_after_ms", 0)
            if wait_after_ms:
                await page.wait_for_timeout(wait_after_ms)

            # ThinkRobotics: Skip data layer extraction as wi_colbrowse_data contains
            # browsing history, not search results. Search results are only in DOM.
            # The DOM extraction below (with .ws-pd-price targeting) will handle it.
            if name.startswith("thinkrobotics"):
                pass  # Fall through to DOM extraction

            # Evelta: window.productsOnPage is undefined, use DOM extraction directly
            if name.startswith("evelta"):
                # Wait for Searchanise to load products (they appear dynamically after networkidle)
                try:
                    await page.wait_for_selector("li.snize-product", timeout=8000, state="attached")
                    # Give Searchanise a moment to populate text/prices after attached
                    await page.wait_for_timeout(2000)
                except PlaywrightTimeoutError:
                    pass  # Continue anyway, might still have products
                
                # Extract directly from DOM using correct Searchanise selectors
                dom_items = await page.evaluate(
                    """(args) => {
                        const { lim, baseUrl } = args;
                        const seen = new Set();
                        const nodes = Array.from(document.querySelectorAll("li.snize-product"));
                        return nodes.slice(0, lim * 2).map((el) => {
                            // Title: use .snize-title for clean product name
                            const titleEl = el.querySelector(".snize-title");
                            const title = titleEl?.textContent?.trim() || "";
                            
                            // Price: use .snize-price.money or .snize-price
                            const priceEl = el.querySelector(".snize-price.money, .snize-price");
                            let priceText = priceEl?.textContent?.trim() || "";
                            // Clean up price text - remove any "View product" or extra text
                            if (priceText) {
                                priceText = priceText.replace(/view product/gi, "").trim();
                                priceText = priceText.replace(/add to cart/gi, "").trim();
                                priceText = priceText.replace(/read more/gi, "").trim();
                                // Extract just the price amount
                                const priceMatch = priceText.match(/₹[\\d,]+\\.?\\d*/);
                                if (priceMatch) {
                                    priceText = priceMatch[0];
                                }
                            }
                            
                            // Link: find the product link (don't include li.snize-product since we're already inside it)
                            const linkEl = el.querySelector(".snize-item-title a, a.snize-view-link, a[href*='/']");
                            let href = linkEl?.getAttribute("href") || "";
                            if (href && !href.startsWith("http")) {
                                href = new URL(href, baseUrl).toString();
                            }
                            
                            // Image: Handle BigCommerce resizing logic
                            const imgEl = el.querySelector(".snize-thumbnail img, img");
                            let imgUrl = imgEl?.getAttribute("src") || imgEl?.getAttribute("data-src") || "";
                            if (imgUrl && !imgUrl.startsWith("http")) {
                                imgUrl = new URL(imgUrl, baseUrl).toString();
                            }
                            // Upscale BigCommerce images: replace .220.290.jpg with .1280.1280.jpg
                            // Matches pattern: .<width>.<height>.jpg/png
                            if (imgUrl) {
                                imgUrl = imgUrl.replace(/\.\d+\.\d+\.(jpg|png|jpeg)/gi, ".1280.1280.$1");
                            }
                            
                            // Availability - Evelta doesn't show stock status prominently, default to In stock
                            const availEl = el.querySelector(".snize-stock-status, .stock, .availability");
                            let availability = availEl?.textContent?.trim() || "";
                            if (!availability) {
                                availability = "In stock"; // Default for Evelta
                            } else {
                                const low = availability.toLowerCase();
                                if (low.includes("out of stock") || low.includes("sold")) {
                                    availability = "Out of stock";
                                } else {
                                    availability = "In stock";
                                }
                            }
                            
                            return {
                                title,
                                price_text: priceText,
                                url: href,
                                image_url: imgUrl,
                                availability,
                            };
                        }).filter(i => i.title && i.url && !seen.has(i.url) && (seen.add(i.url), true));
                    }""",
                    {"lim": limit, "baseUrl": adapter["base_url"]},
                )
                
                if dom_items:
                    cleaned = []
                    for item in dom_items[:limit]:
                        price_text = item.get("price_text", "").strip()
                        if price_text and "(Incl. GST)" not in price_text and "GST" not in price_text:
                            price_text = f"{price_text} (Incl. GST)"
                        cleaned.append({
                            "title": item.get("title", "").strip(),
                            "price_text": price_text,
                            "availability": item.get("availability", "In stock"),
                            "url": item.get("url", ""),
                            "source": source_key or adapter["name"].lower().replace(".", ""),
                            "image_url": item.get("image_url", ""),
                        })
                    if cleaned:
                        fetched_at = await page.evaluate("() => new Date().toISOString()")
                        return {"items": cleaned[:limit], "fetched_at": fetched_at, "note": "Evelta DOM extraction"}

            selectors = adapter["selectors"]
            # Wait for at least one item to appear
            try:
                if name.startswith("thinkrobotics"):
                    timeout = 9000
                elif name.startswith("evelta"):
                    timeout = 8000
                elif name.startswith("robu"):
                    timeout = 12000
                else:
                    timeout = 7000
                if name.startswith("thinkrobotics"):
                    frame = None
                    for f in page.frames:
                        if "search-result" in (f.url or ""):
                            frame = f
                            break
                    if frame:
                        try:
                            await frame.wait_for_selector(selectors["list_item"], timeout=timeout, state="attached")
                        except PlaywrightTimeoutError:
                            await frame.wait_for_selector("a[href*='/products/']", timeout=timeout, state="attached")
                    else:
                        await page.wait_for_selector(selectors["list_item"], timeout=timeout, state="attached")
                else:
                    await page.wait_for_selector(selectors["list_item"], timeout=timeout, state="attached")
            except PlaywrightTimeoutError:
                # Timeout waiting for results - return empty
                try:
                    await page.screenshot(path=f"debug_{name}.png")
                    print(f"Saved debug screenshot to debug_{name}.png")
                except:
                    pass
                fetched_at = await page.evaluate("() => new Date().toISOString()")
                return {
                    "items": [],
                    "fetched_at": fetched_at,
                    "note": "Timed out waiting for results; site may be slow.",
                }
            
            results = []

            async def safe_text(item: Any, selector: str, timeout: int = 2000) -> str:
                if not selector:
                    return ""
                loc = item.locator(selector).first
                try:
                    return (await loc.text_content(timeout=timeout) or "").strip()
                except PlaywrightTimeoutError:
                    return ""
                except Exception:
                    return ""

            async def safe_attr(item: Any, selector: str, attr: str, timeout: int = 2000) -> str:
                if not selector:
                    return ""
                loc = item.locator(selector).first
                try:
                    return await loc.get_attribute(attr, timeout=timeout) or ""
                except PlaywrightTimeoutError:
                    return ""
                except Exception:
                    return ""

            def normalize_image_url(raw: str) -> str:
                if not raw:
                    return ""
                # If srcset provided, take the last (often highest-res) URL
                if "," in raw:
                    last = raw.split(",")[-1].strip()
                    raw = last.split(" ")[0].strip() or raw
                elif " " in raw:
                    raw = raw.split(" ")[0].strip()
                return re.sub(r"-\d+x\d+", "", raw)

            def clean_price_text(text: str) -> str:
                cleaned = text or ""
                for bad in ("Add to cart", "Read more", "read more", "READ MORE", "Sale"):
                    cleaned = cleaned.replace(bad, "")
                cleaned = cleaned.replace("Rs.", "₹").replace("Rs", "₹")
                cleaned = cleaned.replace("You save", "")
                cleaned = re.sub(r"(?i)\bfrom\b", "", cleaned)  # Strip "from" / "From"
                return cleaned.strip()

            # Extract items, scrolling as needed until we have enough
            tr_frame = None
            if name.startswith("thinkrobotics"):
                for f in page.frames:
                    if "search-result" in (f.url or ""):
                        tr_frame = f
                        break
            locator_context = tr_frame if tr_frame else page
            items_locator = locator_context.locator(selectors["list_item"])
            seen_urls = set()
            scroll_attempts = 0
            max_scroll_attempts = 0 if name.startswith("evelta") else 2
            
            while len(results) < limit and scroll_attempts < max_scroll_attempts:
                count = await items_locator.count()
                if count == 0:
                    break
                
                # Extract items we haven't seen yet
                for i in range(count):
                    if len(results) >= limit:
                        break
                    item = items_locator.nth(i)
                    title = await safe_text(item, selectors["title"])
                    if not title:
                        continue

                    link_href = await safe_attr(item, selectors["link"], "href")
                    url = urljoin(adapter["base_url"], link_href or "")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)

                    # ThinkRobotics: prioritize sale price elements with correct Wiser AI classes
                    if adapter["name"].lower().startswith("thinkrobotics"):
                        # Wiser AI uses specific CSS classes:
                        # - .ws-pd-price = actual/sale price (has font-weight-bold)
                        # - .ws-pdcmp-price = compare/original price (struck-through)
                        # We want .ws-pd-price, NOT .ws-pdcmp-price
                        try:
                            sale_price_data = await item.evaluate(
                                """() => {
                                    // First priority: .ws-pd-price is the sale/actual price
                                    const salePriceEl = this.querySelector('.ws-pd-price');
                                    if (salePriceEl) {
                                        const text = salePriceEl.textContent?.trim() || '';
                                        const match = text.match(/₹?\\s*([\\d,]+(?:\\.\\d+)?)/);
                                        if (match) {
                                            return parseFloat(match[1].replace(/,/g, ''));
                                        }
                                    }
                                    
                                    // Second priority: any .ws-src-price that's NOT .ws-pdcmp-price
                                    const priceEls = this.querySelectorAll('.ws-src-price');
                                    for (const el of priceEls) {
                                        if (el.classList.contains('ws-pdcmp-price')) continue; // skip compare price
                                        const text = el.textContent?.trim() || '';
                                        const match = text.match(/₹?\\s*([\\d,]+(?:\\.\\d+)?)/);
                                        if (match) {
                                            return parseFloat(match[1].replace(/,/g, ''));
                                        }
                                    }
                                    
                                    // Third priority: look for price with font-weight-bold (sale indicator)
                                    const allPriceEls = this.querySelectorAll('[class*="price"]');
                                    for (const el of allPriceEls) {
                                        const style = window.getComputedStyle(el);
                                        const isBold = style.fontWeight === 'bold' || parseInt(style.fontWeight) >= 700;
                                        const isNotCompare = !el.classList.contains('ws-pdcmp-price');
                                        if (isBold && isNotCompare) {
                                            const text = el.textContent?.trim() || '';
                                            const match = text.match(/₹?\\s*([\\d,]+(?:\\.\\d+)?)/);
                                            if (match) {
                                                return parseFloat(match[1].replace(/,/g, ''));
                                            }
                                        }
                                    }
                                    
                                    return null;
                                }"""
                            )
                            if sale_price_data and sale_price_data > 0:
                                price_text = f"₹ {sale_price_data:.2f}"
                            else:
                                price_text = await safe_text(item, selectors["price"])
                        except Exception:
                            price_text = await safe_text(item, selectors["price"])
                    else:
                        price_text = await safe_text(item, selectors["price"])
                    
                    if not price_text:
                        # Some sites expose numeric price in data-last
                        price_attr = await safe_attr(item, selectors["price"], "data-last")
                        if price_attr and price_attr.isdigit():
                            price_value = int(price_attr) / 100
                            price_text = f"₹ {price_value:.2f}"
                    price_text = clean_price_text(price_text)
                    # Adapter-specific price tweaks
                    if adapter["name"].lower().startswith("robocraze") and price_text:
                        if "(Incl. GST)" not in price_text:
                            price_text = f"{price_text} (Incl. GST)"
                    if adapter["name"].lower().startswith("thinkrobotics") and price_text:
                        if "(Incl. GST)" not in price_text:
                            price_text = f"{price_text} (Incl. GST)"
                    if adapter["name"].lower().startswith("robu") and price_text:
                        # Keep first amount and append GST note if present
                        gst_note = " (Incl. GST)" if "gst" in price_text.lower() else ""
                        m = re.search(r"₹\s?[\d,]+(?:\.\d+)?", price_text)
                        if m:
                            price_text = m.group(0) + gst_note

                    availability = await safe_text(item, selectors.get("availability", ""))
                    if not availability:
                        # Some buttons expose data-available flags
                        avail_attr = await safe_attr(item, selectors.get("availability", ""), "data-available")
                        if avail_attr:
                            availability = "In stock" if avail_attr.lower() == "true" else "Out of stock"
                    if not availability:
                        # Some buttons expose value in text (e.g., Add to cart / Sold out)
                        avail_text = await safe_text(item, selectors.get("availability", ""))
                        if avail_text:
                            if "sold" in avail_text.lower():
                                availability = "Out of stock"
                            elif "notify" in avail_text.lower():
                                availability = "Out of stock"
                            elif "add to cart" in avail_text.lower():
                                availability = "In stock"
                    # Site-specific availability tweaks
                    if adapter["name"].lower().startswith("robocraze"):
                        if availability.strip() == "—" or availability.strip() == "-":
                            availability = "Out of stock"
                        elif availability.lower().strip() == "add to cart" or "add to cart" in availability.lower():
                            availability = "In stock"
                    if not availability:
                        cls = (await item.get_attribute("class")) or ""
                        # Try the nearest li.product ancestor for stock classes
                        try:
                            ancestor_cls = await item.evaluate(
                                "(el) => { const li = el.closest('li.product'); return li ? li.className : ''; }"
                            )
                            cls = f"{cls} {ancestor_cls}"
                        except Exception:
                            pass
                        lc = cls.lower()
                        availability = "Out of stock" if "outofstock" in lc else ("In stock" if "instock" in lc else "")

                    image_sel = selectors.get("image") or "img"
                    # Robust image extraction: check all matching images, not just first
                    # ThinkRobotics often has a placeholder or hidden image first
                    try:
                        image_data = await item.evaluate(
                            """(el, selector) => {
                                // Priority 1: Check for explicit .primary-image class (ThinkRobotics specific)
                                const primary = el.querySelector("img.primary-image");
                                if (primary) {
                                    let src = primary.getAttribute('src') || primary.getAttribute('data-src') || "";
                                    if (src && !src.includes('base64')) return src;
                                }

                                // Priority 2: Loop through other matches
                                const imgs = el.querySelectorAll(selector);
                                for (const img of imgs) {
                                    let src = img.getAttribute('src') || img.getAttribute('data-src') || img.getAttribute('data-srcset') || '';
                                    if (src && !src.includes('base64') && !src.includes('svg') && !src.includes('icon')) {
                                        return src;
                                    }
                                }
                                return '';
                            }""",
                            image_sel
                        )
                    except Exception:
                        image_data = ""
                    
                    image_url = normalize_image_url(image_data)
                    image_url = urljoin(adapter["base_url"], image_url)

                    results.append(
                        {
                            "title": title,
                            "price_text": price_text,
                            "availability": availability,
                            "url": url,
                            "source": source_key or adapter["name"].lower().replace(".", ""),
                            "image_url": image_url,
                        }
                    )
                
                # If we still need more items, scroll and try again
                if len(results) < limit:
                    await page.evaluate("window.scrollBy(0, 1000);")
                    await page.wait_for_timeout(400)  # Brief wait for new content
                    scroll_attempts += 1

            # If nothing parsed, attempt a generic JS-side extraction as a fallback
            if not results and name.startswith("thinkrobotics") and tr_frame:
                js_items = await tr_frame.evaluate(
                    """(args) => {
                        const { baseUrl, lim } = args || {};
                        const nodes = Array.from(document.querySelectorAll(".ws_search_product-card-grid, .wssearchproduct-card-grid, .wssearchproduct-card, [data-product-id], a[href*='/products/']"));
                        const seen = new Set();
                        return nodes.slice(0, lim * 4).map((el) => {
                            // find link
                            let linkEl = el.querySelector("a[href*='/products/']") || (el.matches("a[href*='/products/']") ? el : null);
                            let href = linkEl?.getAttribute("href") || "";
                            if (href && !href.startsWith("http")) href = new URL(href, baseUrl).toString();
                            // title
                            const titleEl = el.querySelector(".ws_search_card-title, .wssearchproduct-title, .wssearchproduct-title a, a[data-product-title]") || linkEl;
                            const title = (titleEl?.textContent || "").trim();
                            // price - prioritize sale price elements (.ws-pd-price), avoid compare prices (.ws-pdcmp-price)
                            // .ws-pd-price = sale/actual price (bold)
                            // .ws-pdcmp-price = compare/original price (should be skipped)
                            let priceEl = el.querySelector(".ws-pd-price");
                            if (!priceEl) {
                                // Fallback: any .ws-src-price that's NOT .ws-pdcmp-price
                                const allSrcPrices = el.querySelectorAll(".ws-src-price");
                                for (const p of allSrcPrices) {
                                    if (!p.classList.contains("ws-pdcmp-price")) {
                                        priceEl = p;
                                        break;
                                    }
                                }
                            }
                            if (!priceEl) {
                                priceEl = el.querySelector(".wssearchproduct-price-final, .wssearchproduct-price, .glc-money, [data-last]");
                            }
                            let priceText = priceEl?.textContent?.trim() || "";
                            const dl = priceEl?.getAttribute?.("data-last");
                            const numbers = [];
                            if (dl && /^\\d+$/.test(dl)) numbers.push(parseInt(dl, 10) / 100);
                            if (priceText) {
                                const found = priceText.match(/\\d[\\d,]*(?:\\.\\d+)?/g);
                                if (found) {
                                    for (const f of found) {
                                        const v = parseFloat(f.replace(/,/g, ""));
                                        if (!isNaN(v)) numbers.push(v);
                                    }
                                }
                            }
                            // If still no price, scan card but exclude struck-through text
                            if (numbers.length === 0) {
                                const cardText = (el.textContent || "").replace(/\\s+/g, " ").trim();
                                // Find all price-like numbers, but prioritize those NOT in struck-through context
                                const allMatches = cardText.match(/₹?\\s*\\d[\\d,]*(?:\\.\\d+)?/g) || [];
                                for (const m of allMatches) {
                                    const v = parseFloat(m.replace(/[₹,\\s]/g, ""));
                                    if (!isNaN(v) && v > 0) {
                                        // Check if this number appears in struck-through context
                                        const textBefore = cardText.substring(0, cardText.indexOf(m));
                                        const delCount = (textBefore.match(/<del[^>]*>/gi) || []).length;
                                        const delCloseCount = (textBefore.match(/<\\/del>/gi) || []).length;
                                        const isStruckThrough = delCount > delCloseCount;
                                        if (!isStruckThrough) {
                                            numbers.push(v);
                                        }
                                    }
                                }
                            }
                            // Take minimum of valid numbers (sale price should be lowest)
                            const best = numbers.length ? Math.min(...numbers) : NaN;
                            priceText = isNaN(best) ? (priceText || "") : `₹ ${best.toFixed(2)}`;
                            if (priceText && !priceText.includes("Incl. GST")) {
                                priceText = `${priceText} (Incl. GST)`;
                            }
                            // image
                            const imgEl = el.querySelector("img.ws_card-img-top, img.primary-image, img.wssearchproduct-image, img[data-src], img[src], img.wssearchimage, img[data-srcset]");
                            let imgUrl = imgEl?.getAttribute("src") || imgEl?.getAttribute("data-src") || imgEl?.getAttribute("data-srcset") || "";
                            if (imgUrl && imgUrl.includes(",")) {
                                const last = imgUrl.split(",").pop().trim();
                                imgUrl = last.split(" ")[0];
                            }
                            if (imgUrl) {
                                imgUrl = imgUrl.replace(/-\\d+x\\d+/g, "");
                                if (!imgUrl.startsWith("http")) imgUrl = new URL(imgUrl, baseUrl).toString();
                            }
                            // availability
                            const availEl = el.querySelector(".price__badge--sold-out, .wssearchproduct-inventory, .wssearchproduct-badge, .badge, .stock");
                            let availability = availEl?.textContent?.trim() || "";
                            if (!availability) {
                                const cardText = (el.textContent || "").toLowerCase();
                                if (cardText.includes("out of stock") || cardText.includes("sold out")) {
                                    availability = "Out of stock";
                                } else if (cardText.includes("in stock") || cardText.includes("available")) {
                                    availability = "In stock";
                                }
                            }
                            if (!availability) {
                                // Default to in-stock if nothing negative found
                                availability = "In stock";
                            }
                            return {
                                title,
                                price_text: priceText,
                                url: href,
                                image_url: imgUrl,
                                availability,
                            };
                        }).filter(i => i.title && i.url && !seen.has(i.url) && (seen.add(i.url), true));
                    }""",
                    {"baseUrl": adapter["base_url"], "lim": limit},
                )
                results = [
                    {
                        **item,
                        "source": source_key or adapter["name"].lower().replace(".", ""),
                    }
                    for item in js_items[:limit]
                ]

            # Default availability for thinkrobotics if still missing
            if name.startswith("thinkrobotics") and results:
                for itm in results:
                    if not itm.get("availability"):
                        itm["availability"] = "In stock"

            if not results:
                js_items = await page.evaluate(
                    """(args) => {
                        const { sel, lim } = args;
                        const nodes = Array.from(document.querySelectorAll(sel));
                        const seen = new Set();
                        return nodes.slice(0, lim * 3).map((el) => {
                            const titleEl = el.querySelector("a[href], h2 a, h3 a, .card-title a, .product-title a");
                            const priceEl = el.querySelector(".price, .price-item--sale, .price-item--regular, .woocommerce-Price-amount, [data-last]");
                            const linkEl = el.querySelector("a[href]");
                            const imgEl = el.querySelector("img");
                            const availEl = el.querySelector(".stock, .availability, .product-stock, button[data-btn-addToCart], .badge, .wssearchproduct-inventory");
                            const cls = (el.getAttribute("class") || "").toLowerCase();
                            const availabilityRaw = availEl?.textContent?.trim() || "";
                            let availability = availabilityRaw;
                            if (!availability) {
                                availability = cls.includes("outofstock") ? "Out of stock" : (cls.includes("instock") ? "In stock" : "");
                            }
                            if (!availability && availabilityRaw) {
                                const low = availabilityRaw.toLowerCase();
                                if (low.includes("sold") || low.includes("notify")) availability = "Out of stock";
                                else if (low.includes("add to cart")) availability = "In stock";
                            }
                            let href = linkEl?.getAttribute("href") || "";
                            let imgUrl = imgEl?.getAttribute("src") || imgEl?.getAttribute("data-src") || imgEl?.getAttribute("data-srcset") || "";
                            if (imgUrl && imgUrl.includes(",")) {
                                const last = imgUrl.split(",").pop().trim();
                                imgUrl = last.split(" ")[0];
                            }
                            if (imgUrl) {
                                imgUrl = imgUrl.replace(/-\\d+x\\d+/g, "");
                            }
                            let priceText = priceEl?.textContent?.trim() || "";
                            const dataLast = priceEl?.getAttribute?.("data-last");
                            if (!priceText && dataLast && /^\\d+$/.test(dataLast)) {
                                priceText = `₹ ${(parseInt(dataLast, 10) / 100).toFixed(2)}`;
                            }
                            if (priceText.toLowerCase().includes("read more")) {
                                priceText = priceText.replace(/read more/gi, "").trim();
                            }
                            if (priceText.includes("Add to cart")) {
                                priceText = priceText.replace("Add to cart", "").trim();
                            }
                            const title = titleEl?.textContent?.trim() || "";
                            return {
                                title,
                                price_text: priceText,
                                url: href,
                                image_url: imgUrl,
                                availability,
                            };
                        }).filter(i => i.title && i.url && !seen.has(i.url) && (seen.add(i.url), true));
                    }""",
                    {"sel": selectors["list_item"], "lim": limit},
                )
                results = [
                    {
                        **item,
                        "url": urljoin(adapter["base_url"], item["url"]),
                        "image_url": urljoin(adapter["base_url"], item["image_url"]),
                        "source": source_key or adapter["name"].lower().replace(".", ""),
                    }
                    for item in js_items[:limit]
                ]

            # Adapter-specific JS fallbacks for highly dynamic sites
            # Adapter-specific JS fallbacks for highly dynamic sites
            if not results and name.startswith("thinkrobotics"):
                js_items = await page.evaluate(
                    """(lim) => {
                        const cards = Array.from(document.querySelectorAll(".wssearchproduct-card-grid, .wssearchproduct-card, div[data-product-id], .product-card"));
                        const seen = new Set();
                        return cards.slice(0, lim * 3).map(el => {
                            // Title
                            const titleEl = el.querySelector(".wssearchproduct-title, .wssearchproduct-title a, a[data-product-title], .card__heading a");
                            const title = (titleEl?.textContent || "").trim();
                            
                            // Link
                            let linkEl = el.querySelector("a[data-product-handle], a[href*='/products/']");
                            let href = linkEl?.getAttribute("href") || "";
                            
                            // Image - use user provided class .product-featured-media and generic fallbacks
                            const imgEl = el.querySelector("img.product-featured-media, img.wssearchproduct-image, img.product-card__image, img.list-view-item__image, img[data-src], img[src]");
                            let imgUrl = imgEl?.getAttribute("src") || imgEl?.getAttribute("data-src") || imgEl?.getAttribute("srcset") || "";
                            if (imgUrl && imgUrl.startsWith("//")) imgUrl = "https:" + imgUrl;
                            
                            // Price
                            // Priority 1: .glc-money (User Provided)
                            // Priority 2: .ws-pd-price (Sale)
                            let priceEl = el.querySelector(".glc-money");
                            if (!priceEl) priceEl = el.querySelector(".ws-pd-price");
                            if (!priceEl) priceEl = el.querySelector(".price-item--sale, .price-item--regular, .wssearchproduct-price, .wssearchproduct-price-final, [data-last]");
                            
                            let priceText = priceEl?.textContent?.trim() || "";
                            priceText = priceText.replace(/from/i, "").trim();
                            
                            // Availability
                            // Priority 1: .price__badge--sold-out (User Provided)
                            const soldOutBadge = el.querySelector(".price__badge--sold-out, .product-label--sold-out");
                            let availability = soldOutBadge ? "Out of stock" : "";
                            
                            if (!availability) {
                                const availEl = el.querySelector(".wssearchproduct-inventory, .badge, .wssearchproduct-badge");
                                const text = (availEl?.textContent || "").toLowerCase();
                                if (text.includes("sold")) availability = "Out of stock";
                            }
                            if (!availability) {
                                // Check "Add to Cart" button text
                                const btn = el.querySelector("button[type='submit'], .product-form__cart-submit");
                                if (btn) {
                                    const btnText = (btn.textContent || "").toLowerCase();
                                    if (btnText.includes("sold out") || btn.disabled && btnText.includes("unavailable")) {
                                        availability = "Out of stock";
                                    } else if (btnText.includes("add to cart") || btnText.includes("choose options")) {
                                        availability = "In stock";
                                    }
                                }
                            }
                            if (!availability) {
                                // Fallback: check text content of card
                                const text = el.textContent?.toLowerCase() || "";
                                if (text.includes("sold out")) availability = "Out of stock";
                                else availability = "In stock";
                            }

                            return {
                                title,
                                price_text: priceText,
                                url: href,
                                image_url: imgUrl,
                                availability,
                            };
                        }).filter(i => i.title && i.url && !seen.has(i.url) && (seen.add(i.url), true));
                    }""",
                    limit,
                )
                results = [
                    {
                        **item,
                        "url": urljoin(adapter["base_url"], item["url"]),
                        "image_url": urljoin(adapter["base_url"], item["image_url"]),
                        "source": source_key or adapter["name"].lower().replace(".", ""),
                    }
                    for item in js_items[:limit]
                ]

            if not results and name.startswith("evelta"):
                js_items = await page.evaluate(
                    """(lim) => {
                        // Prefer Searchanise data layer if available
                        const dl = (window.productsOnPage || []).slice(0, lim * 2).map(p => ({
                            title: p.name || "",
                            price_text: (p.price?.with_tax?.formatted || p.price?.without_tax?.formatted || p.price?.with_tax?.value || p.price?.without_tax?.value || "").toString(),
                            url: p.url || "",
                            image_url: p.image?.data || p.image || "",
                            availability: (p.quantity && Number(p.quantity) > 0) ? "In stock" : "Out of stock",
                        }));
                        const cards = Array.from(document.querySelectorAll("li.snize-product, .snize-product"));
                        const dom = cards.slice(0, lim * 3).map(el => {
                            const titleEl = el.querySelector("a[href]");
                            const priceEl = el.querySelector(".snize-price, .price, [data-last]");
                            const imgEl = el.querySelector("img");
                            let href = titleEl?.getAttribute("href") || "";
                            let imgUrl = imgEl?.getAttribute("src") || imgEl?.getAttribute("data-src") || imgEl?.getAttribute("data-srcset") || "";
                            if (imgUrl && imgUrl.includes(",")) {
                                const last = imgUrl.split(",").pop().trim();
                                imgUrl = last.split(" ")[0];
                            }
                            if (imgUrl) imgUrl = imgUrl.replace(/-\\d+x\\d+/g, "");
                            let priceText = priceEl?.textContent?.trim() || "";
                            const dl = priceEl?.getAttribute?.("data-last");
                            if (!priceText && dl && /^\\d+$/.test(dl)) {
                                priceText = `₹ ${(parseInt(dl, 10) / 100).toFixed(2)}`;
                            }
                            let availability = "";
                            const title = titleEl?.textContent?.trim() || "";
                            return {
                                title,
                                price_text: priceText,
                                url: href,
                                image_url: imgUrl,
                                availability,
                            };
                        });
                        const merged = [...dl, ...dom];
                        const seen = new Set();
                        return merged.filter(i => i.title && i.url && !seen.has(i.url) && (seen.add(i.url), true)).slice(0, lim * 2);
                    }""",
                    limit,
                )
                results = [
                    {
                        **item,
                        "url": urljoin(adapter["base_url"], item["url"]),
                        "image_url": urljoin(adapter["base_url"], item["image_url"]),
                        "source": source_key or adapter["name"].lower().replace(".", ""),
                    }
                    for item in js_items[:limit]
                ]

            # Trim to limit (already deduplicated in extraction loop)
            results = results[:limit]

            fetched_at = await page.evaluate("() => new Date().toISOString()")
            return {"items": results, "fetched_at": fetched_at}
        finally:
            await page.close()

    async def refresh_single_item(self, url: str, source: str) -> Dict[str, Any]:
        """Fetch current data for a single item from its product page."""
        browser = await self._ensure_browser()
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)  # Let JS render - increased for Robu
            
            # Source-specific extraction
            if source == "robu":
                item_data = await page.evaluate("""() => {
                    const result = {
                        title: '',
                        price_text: '',
                        availability: '',
                        image_url: ''
                    };
                    
                    // Robu.in specific title
                    const titleEl = document.querySelector('h1.product_title') || document.querySelector('h1');
                    if (titleEl) result.title = titleEl.textContent.trim();
                    
                    // Robu.in specific price - look for WooCommerce price structure
                    const priceEl = document.querySelector('.price ins .woocommerce-Price-amount bdi') ||
                                   document.querySelector('.price .woocommerce-Price-amount bdi') ||
                                   document.querySelector('.price ins .amount') ||
                                   document.querySelector('.price .amount') ||
                                   document.querySelector('.woocommerce-Price-amount bdi') ||
                                   document.querySelector('.summary .price');
                    if (priceEl) {
                        let priceText = priceEl.textContent.trim();
                        // Clean up the price text
                        priceText = priceText.replace(/[^0-9.,₹]/g, '');
                        if (priceText && !priceText.startsWith('₹')) {
                            priceText = '₹' + priceText;
                        }
                        result.price_text = priceText;
                    }
                    
                    // Robu.in availability
                    const stockEl = document.querySelector('.stock');
                    if (stockEl) {
                        const text = stockEl.textContent.toLowerCase();
                        if (text.includes('out of stock')) {
                            result.availability = 'Out of stock';
                        } else if (text.includes('in stock')) {
                            result.availability = 'In stock';
                        } else {
                            result.availability = stockEl.textContent.trim();
                        }
                    }
                    
                    // Robu.in image
                    const imgEl = document.querySelector('.woocommerce-product-gallery__image img') ||
                                 document.querySelector('.wp-post-image');
                    if (imgEl) {
                        result.image_url = imgEl.src || imgEl.dataset.src || '';
                    }

                    // Robu.in SKU
                    const skuEl = document.querySelector('.robu_sku') || 
                                 document.querySelector('.sku_wrapper .sku') || 
                                 document.querySelector('.sku');
                    if (skuEl) {
                        let sku = skuEl.textContent.trim();
                        // Remove "SKU:" prefix if present (common in Robu)
                        sku = sku.replace(/^SKU:\s*/i, '').trim();
                        result.sku = sku;
                    }
                    
                    return result;
                }""")
            else:
                # Generic extraction for other sources
                item_data = await page.evaluate("""() => {
                    const result = {
                        title: '',
                        price_text: '',
                        availability: '',
                        image_url: ''
                    };
                    
                    // Title extraction
                    const titleSelectors = [
                        'h1.product-title', 'h1.product_title', 'h1.product-single__title',
                        'h1[itemprop="name"]', '.product-name h1', 'h1', 
                        '.product__title h1', '[data-product-title]'
                    ];
                    for (const sel of titleSelectors) {
                        const el = document.querySelector(sel);
                        if (el && el.textContent.trim()) {
                            result.title = el.textContent.trim();
                            break;
                        }
                    }
                    
                    // Price extraction
                    const priceSelectors = [
                        '.price-item--sale', '.price-item--regular', '.price .money',
                        '.product-price', '.woocommerce-Price-amount bdi', '.price ins .amount',
                        '.product-single__price', '[data-product-price]', '.current-price',
                        '.ws-pd-price', '.glc-money', '.price__current', '.price .amount'
                    ];
                    for (const sel of priceSelectors) {
                        const el = document.querySelector(sel);
                        if (el && el.textContent.trim()) {
                            let price = el.textContent.trim();
                            price = price.replace(/from/gi, '').trim();
                            result.price_text = price;
                            break;
                        }
                    }
                    
                    // Availability extraction
                    const availSelectors = [
                        '.product-inventory', '.stock', '.availability', '.product-stock',
                        '[data-availability]', '.in-stock', '.out-of-stock',
                        '.product-form__inventory', '.stock-message'
                    ];
                    for (const sel of availSelectors) {
                        const el = document.querySelector(sel);
                        if (el && el.textContent.trim()) {
                            const text = el.textContent.toLowerCase();
                            if (text.includes('out of stock') || text.includes('sold out')) {
                                result.availability = 'Out of stock';
                            } else if (text.includes('in stock') || text.includes('available')) {
                                result.availability = 'In stock';
                            } else {
                                result.availability = el.textContent.trim();
                            }
                            break;
                        }
                    }
                    
                    // Check add to cart button as availability fallback
                    if (!result.availability) {
                        const btn = document.querySelector('button[type="submit"][name="add"], .add-to-cart-button, .single_add_to_cart_button');
                        if (btn) {
                            if (btn.disabled) {
                                result.availability = 'Out of stock';
                            } else {
                                result.availability = 'In stock';
                            }
                        }
                    }
                    
                    // Image extraction
                    const imgSelectors = [
                        '.product-single__photo img', '.product-featured-media img',
                        '.woocommerce-product-gallery__image img', '.product-image img',
                        '[data-product-image]', '.product-single__media img'
                    ];
                    for (const sel of imgSelectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                                 result.image_url = el.src || el.dataset.src || '';
                            if (result.image_url) break;
                        }
                    }

                    // Ultimate Robust SKU Extraction
                    let extracted_sku = "";

                    // Strategy 1: Specific User-Verified Selectors
                    const specific_selectors = [
                        '.robu_sku',                          // Robu (<b class="robu_sku">SKU: R255497</b>)
                        '.variant-sku',                       // ThinkRobotics (<span class="variant-sku">)
                        '.productView-info-value--sku',       // Evelta (<div class="productView-info-value--sku">)
                        '[data-product-sku]',                 // Generic structured data
                        '.sku', '[itemprop="sku"]'
                    ];

                    for (const sel of specific_selectors) {
                        const el = document.querySelector(sel);
                        if (el && el.textContent && el.textContent.trim().length > 0) {
                            extracted_sku = el.textContent.trim().replace(/^SKU[:\s]*/i, '').trim();
                            if (extracted_sku) break;
                        }
                    }

                    // Strategy 2: Robocraze & Label-Value Pairs (Siblings)
                    // Matches: <span class="...name">SKU:</span> <span class="...value">CODE</span>
                    if (!extracted_sku) {
                        const allLabels = Array.from(document.querySelectorAll('.productView-info-name, .label, dt, strong, b, span'));
                        const skuLabel = allLabels.find(el => el.textContent && el.textContent.trim().match(/^SKU[:]?$/i));
                        
                        if (skuLabel) {
                            // Try Next Sibling
                            let next = skuLabel.nextElementSibling;
                            if (next && next.textContent) {
                                extracted_sku = next.textContent.trim();
                            }
                            // Try Parent's text if no sibling (e.g. <b>SKU: CODE</b>)
                            else if (skuLabel.parentElement) { 
                                extracted_sku = skuLabel.parentElement.textContent.replace(skuLabel.textContent, '').trim();
                            }
                        }
                    }

                    result.sku = extracted_sku ? extracted_sku.replace(/^SKU[:\s]*/i, '').trim() : "";
                    
                    return result;
                }""")
            
            return item_data
            
        finally:
            await page.close()
            await context.close()

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None


# Helper for scripts/tests
@asynccontextmanager
async def quick_page(headless: bool = True, browser_type: str = "chromium") -> AsyncIterator[Page]:
    service = PlaywrightService(headless=headless, browser_type=browser_type)
    async with service.page() as page:
        yield page
    await service.close()

