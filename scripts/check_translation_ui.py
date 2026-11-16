"""Check translation audit interactions and exports, using an isolated static server."""

import asyncio
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.async_api import async_playwright

from browser_support import browser_target


async def export_selection(page, out, name):
    async with page.expect_download() as pending:
        await page.locator("#export-selection").click()
    download = await pending.value
    assert download.suggested_filename == "crosswalk-translation-review.json"
    await download.save_as(out / name)
    return json.loads((out / name).read_text())


def check_selection(export, report, factor, framework):
    """Compare the downloaded record to the committed source, including provenance."""
    assert export["source"] == report["source"]
    assert export["scope"] == report["scope"]
    assert export["interpretation"] == report["interpretation"]
    assert export["factor"]["id"] == factor
    assert export["framework"]["id"] == framework
    matches = lambda row: row["localFactor"] == factor and row["framework"] == framework
    assert export["cell"] == next(row for row in report["cells"] if matches(row))
    for key in ("alignments", "absences"):
        assert export[key] == [row for row in report[key] if matches(row)]


async def main(base, out):
    report = json.loads(
        (Path(__file__).resolve().parents[1] / "docs/skos/translation-loss-report.json").read_text()
    )
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        await page.goto(base, wait_until="networkidle")
        await page.locator("#audit").wait_for(state="visible")
        assert await page.locator("#mapping-count").inner_text() == "90 / 90"
        assert await page.locator("#absence-count").inner_text() == "6 / 6"
        assert await page.locator("#gap-count").inner_text() == "7 / 7"
        assert await page.locator("#roundtrip").inner_text() == "600 / 600 scoped triples recovered"
        assert await page.locator("#source-hash").inner_text() == report["source"]["sha256"]
        await page.locator("#factor").select_option("ehs:WorkplaceVisibility")
        await page.locator("#framework").select_option("xw:fw-SPARH")
        assert await page.locator("#source-status").inner_text() == "No counterpart asserted"
        assert await page.locator("#skos-status").inner_text() == "No mapping statement"
        assert await page.locator("#sidecar-status").inner_text() == "Explicit absence restored"
        absence = await export_selection(page, out, "absence-review.json")
        check_selection(absence, report, "ehs:WorkplaceVisibility", "xw:fw-SPARH")
        assert len(absence["absences"]) == 1 and not absence["alignments"]
        await page.locator("details.raw summary").click()
        assert absence["absences"][0]["sourceTriple"] in await page.locator("#raw-source").inner_text()

        await page.locator("#factor").select_option("ehs:EquipmentAndTools")
        mapped = await export_selection(page, out, "mapped-review.json")
        check_selection(mapped, report, "ehs:EquipmentAndTools", "xw:fw-SPARH")
        assert mapped["alignments"] and not mapped["absences"]
        assert await page.locator("#sidecar-status").inner_text() == "Assertion context restored"
        for row in mapped["alignments"]:
            assert row["id"] in await page.locator("#source-content").inner_text()

        # Choose a nondefault gap so reloading actually tests query restoration.
        gap = next(row for row in report["coverageGaps"] if row["id"] != "xw:gap-cream-TimeOfDay")
        await page.locator("#gap").select_option(gap["id"])
        text = await page.locator("#gap-view").inner_text()
        assert gap["id"] in text and gap["comment"] in text
        for source in gap["sourceRefs"]:
            assert source in text
        expected_query = {
            "factor": ["ehs:EquipmentAndTools"], "framework": ["xw:fw-SPARH"], "gap": [gap["id"]]
        }
        assert parse_qs(urlparse(page.url).query) == expected_query
        await page.reload(wait_until="networkidle")
        await page.locator("#audit").wait_for(state="visible")
        for key, values in expected_query.items():
            assert await page.locator(f"#{key}").input_value() == values[0]
        restored = await export_selection(page, out, "restored-review.json")
        assert restored == mapped
        await page.locator("#gap").select_option("xw:gap-cream-TimeOfDay")
        assert "partial correspondence does not remove this gap" in await page.locator("#gap-view").inner_text()
        for width in (1440, 390):
            await page.set_viewport_size({"width": width, "height": 1000})
            assert not await page.evaluate("document.documentElement.scrollWidth > innerWidth")
            await page.screenshot(path=str(out / f"translation-{width}.png"), full_page=True)
        assert not errors, errors
        print("PASS: absence/mapped/gap views, exact source exports, deep links, mobile layout, no errors")
        await browser.close()


if __name__ == "__main__":
    with browser_target("translation-audit.html") as target:
        asyncio.run(main(*target))
