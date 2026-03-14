"""
scrapers/page_watcher.py — Generic HTML hash-diff watcher.

Watches any URL for content changes. Used for Nashville and Denver pages.
"""

import logging
import config
from scrapers.austin_web import watch_page  # Reuse the same implementation

log = logging.getLogger(__name__)


def run():
    """Watch all configured pages except Austin (handled by austin_web.py)."""
    log.info("=== Page watcher starting (%d pages) ===", len(config.WATCHED_PAGES))

    changes = 0
    skipped = 0

    for page in config.WATCHED_PAGES:
        if page["city"] == "Austin":
            skipped += 1
            continue  # Austin handled separately with deadline logic
        try:
            changed = watch_page(
                name=page["name"],
                url=page["url"],
                city=page["city"],
                priority=page.get("priority", "medium"),
            )
            if changed:
                changes += 1
        except Exception as e:
            log.error("Error watching %s: %s", page["name"], e)

    log.info("Page watcher done — checked: %d | changed: %d | skipped (Austin): %d",
             len(config.WATCHED_PAGES) - skipped, changes, skipped)

    return {
        "checked": len(config.WATCHED_PAGES) - skipped,
        "changes": changes,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    result = run()
    print(f"\nResult: {result}")
