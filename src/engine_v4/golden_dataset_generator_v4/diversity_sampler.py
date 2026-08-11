import logging
import sqlite3
from contextlib import closing
from typing import Any, Dict, List, Sequence

logger = logging.getLogger("DiversitySamplerV4")

# Diversification phase: never feed the Engine more micro goldens.
NON_MICRO_CATEGORIES: Sequence[str] = ("short", "medium", "long", "massive")


class DiversitySampler:
    """
    Samples Phase-1-enriched raw emails for Engine V4, biased to under-represented
    size categories in golden_dataset.

    By default micro is excluded entirely (diversification mode). Fallback fills
    only from other non-micro categories ordered by golden scarcity — never micro.
    """

    def __init__(self, db_path: str, *, exclude_micro: bool = True):
        self.db_path = db_path
        self.exclude_micro = exclude_micro

    def _eligible_categories(self) -> List[str]:
        if self.exclude_micro:
            return list(NON_MICRO_CATEGORIES)
        return list(NON_MICRO_CATEGORIES) + ["micro"]

    def _get_current_distribution(self, cursor) -> Dict[str, int]:
        cursor.execute(
            """
            SELECT r.size_category, count(*)
            FROM golden_dataset g
            JOIN raw_emails r ON g.raw_email_id = r.id
            GROUP BY r.size_category
            """
        )
        return dict(cursor.fetchall())

    def _fetch_category(self, cursor, category: str, limit: int) -> List[sqlite3.Row]:
        if limit <= 0:
            return []
        cursor.execute(
            """
            SELECT id, raw_text, target_persona, dpbc_targets, size_category
            FROM raw_emails
            WHERE status = 'backtranslated'
              AND dpbc_targets IS NOT NULL
              AND target_persona IS NOT NULL
              AND size_category = ?
            LIMIT ?
            """,
            (category, limit),
        )
        return list(cursor.fetchall())

    def get_next_batch(self, batch_size: int) -> List[Dict[str, Any]]:
        with closing(sqlite3.connect(self.db_path, timeout=60.0)) as conn:
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
            except sqlite3.OperationalError:
                pass
            conn.row_factory = sqlite3.Row

            with conn:
                cursor = conn.cursor()
                distribution = self._get_current_distribution(cursor)
                categories = self._eligible_categories()
                counts = {cat: int(distribution.get(cat, 0) or 0) for cat in categories}

                # Scarcest golden sizes first
                ordered = sorted(categories, key=lambda c: counts[c])
                logger.info(
                    "Golden size counts (eligible)=%s; claim order=%s; batch_size=%s",
                    counts,
                    ordered,
                    batch_size,
                )

                rows: List[sqlite3.Row] = []
                seen_ids = set()
                remaining = batch_size

                for cat in ordered:
                    if remaining <= 0:
                        break
                    chunk = self._fetch_category(cursor, cat, remaining)
                    for row in chunk:
                        rid = row["id"]
                        if rid in seen_ids:
                            continue
                        seen_ids.add(rid)
                        rows.append(row)
                        remaining -= 1
                        if remaining <= 0:
                            break
                    if chunk:
                        logger.info(
                            "Claimed %s from size_category=%s (golden_count=%s)",
                            len(chunk),
                            cat,
                            counts[cat],
                        )

                if remaining > 0:
                    logger.warning(
                        "Only %s/%s non-micro enriched emails available "
                        "(need more Phase-1 diversity harvest / sync)",
                        len(rows),
                        batch_size,
                    )

                results: List[Dict[str, Any]] = []
                for row in rows:
                    cursor.execute(
                        "UPDATE raw_emails SET status = 'locked_v4' WHERE id = ?",
                        (row["id"],),
                    )
                    results.append(dict(row))

            return results
