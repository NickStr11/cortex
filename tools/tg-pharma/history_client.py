from __future__ import annotations

import base64
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import paramiko
from beartype import beartype

ALLOWED_PERIODS = {"last_month", "this_month", "last_90_days", "last_180_days", "all_time"}


@beartype
def period_days(period: str) -> int | None:
    match = re.fullmatch(r"last_(\d+)_days", (period or "").strip().lower())
    if not match:
        return None
    days = int(match.group(1))
    return days if 1 <= days <= 3650 else None


@dataclass(slots=True)
class HistoryProductSummary:
    ean: str
    name: str
    maker: str
    qty_sum: float
    purchase_count: int
    last_date: str
    top_supplier: str
    top_supplier_qty: float


@dataclass(slots=True)
class CatalogProduct:
    ean: str
    name: str
    maker: str
    id_name: int | None
    offer_count: int
    best_priority: int


@dataclass(slots=True)
class SupplierBreakdown:
    supplier: str
    qty_sum: float
    purchase_count: int
    last_date: str


@dataclass(slots=True)
class RefIdentity:
    key: str
    id_name: int | None
    id_mak: int | None
    name: str
    maker: str
    alias_eans: tuple[str, ...]
    matched_via: str = ""


@beartype
def normalize_period(period: str) -> str:
    normalized = (period or "last_month").strip().lower()
    if normalized in ALLOWED_PERIODS:
        return normalized
    if period_days(normalized) is not None:
        return normalized
    return "last_month"


@beartype
def normalize_search_text(text: str) -> str:
    lowered = text.casefold()
    lowered = lowered.replace("ё", "е")
    lowered = lowered.replace("№", " ")
    lowered = lowered.replace(",", " ")
    lowered = lowered.replace(".", " ")
    lowered = lowered.replace("/", " ")
    lowered = lowered.replace("\\", " ")
    lowered = lowered.replace("-", " ")
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


@beartype
def build_query_variants(query: str) -> list[str]:
    cleaned = " ".join(query.strip().split())
    if not cleaned:
        return []

    variants: list[str] = [cleaned]

    def push(value: str) -> None:
        normalized = " ".join(value.strip().split())
        if normalized and normalized not in variants:
            variants.append(normalized)

    def token_fallbacks(token: str) -> list[str]:
        token = token.strip()
        if len(token) < 4:
            return []
        options: set[str] = set()
        endings = {
            "у": "а",
            "ю": "я",
            "ы": "а",
            "и": "а",
            "ой": "а",
            "ей": "я",
        }
        for old, new in endings.items():
            if token.endswith(old) and len(token) - len(old) >= 3:
                options.add(token[: -len(old)] + new)
        return [item for item in options if item != token]

    push(cleaned[:1].upper() + cleaned[1:])

    base_tokens = cleaned.split()
    for idx, token in enumerate(base_tokens):
        for alt in token_fallbacks(token):
            mutated = list(base_tokens)
            mutated[idx] = alt
            push(" ".join(mutated))

    replacements = {
        " 125 ": [" 0.125 ", " 0,125 "],
        " 250 ": [" 0.25 ", " 0,25 "],
        " 500 ": [" 0.5 ", " 0,5 "],
        " 750 ": [" 0.75 ", " 0,75 "],
        " 875 ": [" 0.875 ", " 0,875 "],
        " 1000 ": [" 1.0 ", " 1,0 "],
    }
    padded = f" {cleaned} "
    for needle, options in replacements.items():
        if needle in padded:
            for option in options:
                push(padded.replace(needle, option).strip())

    for variant in list(variants):
        push(variant.replace(" 0.5", ",0.5"))
        push(variant.replace(" 0,5", ",0.5"))
        push(variant.replace(" 0.25", ",0.25"))
        push(variant.replace(" 0,25", ",0.25"))

    for variant in list(variants):
        if variant:
            push(variant[:1].upper() + variant[1:])

    return variants


@beartype
def build_variant_tokens(query: str) -> list[list[str]]:
    variants = build_query_variants(query)
    token_groups: list[list[str]] = []
    for variant in variants:
        prepared = normalize_search_text(variant).replace("mg", " ")
        tokens = [token.strip() for token in prepared.split() if token.strip()]
        if tokens and tokens not in token_groups:
            token_groups.append(tokens)
    return token_groups


@beartype
def build_like_clause(column: str, query: str) -> tuple[str, list[str]]:
    token_groups = build_variant_tokens(query)
    clauses: list[str] = []
    args: list[str] = []
    for tokens in token_groups:
        token_clauses: list[str] = []
        for token in tokens:
            token_clauses.append(f"{column} LIKE ?")
            args.append(f"%{normalize_search_text(token)}%")
        clauses.append("(" + " AND ".join(token_clauses) + ")")
    return (" OR ".join(clauses) if clauses else "1=0"), args


@beartype
def period_sql_clause(column: str, period: str) -> str:
    normalized = normalize_period(period)
    if normalized == "last_month":
        return (
            f"AND date({column}) >= date('now','start of month','-1 month') "
            f"AND date({column}) < date('now','start of month')"
        )
    if normalized == "this_month":
        return f"AND date({column}) >= date('now','start of month')"
    if normalized == "last_90_days":
        return f"AND date({column}) >= date('now','-90 days')"
    if normalized == "last_180_days":
        return f"AND date({column}) >= date('now','-180 days')"
    days = period_days(normalized)
    if days is not None:
        return f"AND date({column}) >= date('now','-{days} days')"
    return ""


@beartype
def make_identity_key(id_name: int | None, name: str, maker: str) -> str:
    normalized_name = normalize_search_text(name)
    normalized_maker = normalize_search_text(maker)
    if id_name is not None and normalized_maker:
        return f"id:{id_name}|maker:{normalized_maker}"
    if id_name is not None:
        return f"id:{id_name}"
    return f"name:{normalized_name}|maker:{normalized_maker}"


class LocalAnalyticsClient:
    @beartype
    def __init__(self, db_path: str = "") -> None:
        self.db_path = Path(db_path).expanduser() if db_path else Path()

    @property
    def enabled(self) -> bool:
        return self.db_path.exists() and self.db_path.is_file()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    @beartype
    def search_catalog(self, query: str, limit: int = 5) -> list[CatalogProduct]:
        if not self.enabled:
            return []
        cleaned = " ".join(query.strip().split())
        if not cleaned:
            return []
        where_sql, args = build_like_clause("search_text", cleaned)
        query_like = f"%{normalize_search_text(cleaned)}%"
        sql = f"""
SELECT
    canonical_ean AS ean,
    name,
    COALESCE(maker, '') AS maker,
    id_name,
    offer_count,
    best_priority
FROM catalog_products
WHERE {where_sql}
ORDER BY
    CASE WHEN search_text LIKE ? THEN 1 ELSE 0 END DESC,
    offer_count DESC,
    best_priority ASC,
    name ASC
LIMIT ?
""".strip()
        with self._connect() as conn:
            rows = conn.execute(sql, [*args, query_like, int(limit)]).fetchall()
        return [
            CatalogProduct(
                ean=str(item["ean"]).strip(),
                name=str(item["name"]).strip(),
                maker=str(item["maker"]).strip(),
                id_name=int(item["id_name"]) if item["id_name"] is not None else None,
                offer_count=int(item["offer_count"] or 0),
                best_priority=int(item["best_priority"] or 999),
            )
            for item in rows
            if item["ean"]
        ]

    @beartype
    def get_purchase_summary(self, query: str, period: str = "last_month", limit: int = 5) -> list[HistoryProductSummary]:
        if not self.enabled:
            return []
        cleaned = " ".join(query.strip().split())
        if not cleaned:
            return []
        where_sql, args = build_like_clause("search_text", cleaned)
        period_clause = period_sql_clause("nakl_date", period)
        sql = f"""
WITH filtered AS (
    SELECT product_key, canonical_ean AS ean, canonical_name AS name, canonical_maker AS maker,
           supplier, nakl_date, qty, search_text
    FROM purchase_lines
    WHERE ({where_sql})
    {period_clause}
),
product_totals AS (
    SELECT product_key, ean, name, maker,
           SUM(qty) AS qty_sum,
           COUNT(*) AS purchase_count,
           MAX(nakl_date) AS last_date
    FROM filtered
    GROUP BY product_key, ean, name, maker
),
supplier_totals AS (
    SELECT product_key, supplier, SUM(qty) AS supplier_qty
    FROM filtered
    GROUP BY product_key, supplier
),
ranked_suppliers AS (
    SELECT product_key, supplier, supplier_qty,
           ROW_NUMBER() OVER (PARTITION BY product_key ORDER BY supplier_qty DESC, supplier ASC) AS rn
    FROM supplier_totals
)
SELECT
    p.ean,
    p.name,
    COALESCE(p.maker, '') AS maker,
    COALESCE(p.qty_sum, 0) AS qty_sum,
    COALESCE(p.purchase_count, 0) AS purchase_count,
    COALESCE(p.last_date, '') AS last_date,
    COALESCE(r.supplier, '') AS top_supplier,
    COALESCE(r.supplier_qty, 0) AS top_supplier_qty
FROM product_totals p
LEFT JOIN ranked_suppliers r ON r.product_key = p.product_key AND r.rn = 1
ORDER BY p.qty_sum DESC, p.purchase_count DESC, p.last_date DESC
LIMIT ?
""".strip()
        with self._connect() as conn:
            rows = conn.execute(sql, [*args, int(limit)]).fetchall()
        return [
            HistoryProductSummary(
                ean=str(item["ean"]).strip(),
                name=str(item["name"]).strip(),
                maker=str(item["maker"]).strip(),
                qty_sum=float(item["qty_sum"] or 0),
                purchase_count=int(item["purchase_count"] or 0),
                last_date=str(item["last_date"]).strip(),
                top_supplier=str(item["top_supplier"]).strip(),
                top_supplier_qty=float(item["top_supplier_qty"] or 0),
            )
            for item in rows
            if item["ean"]
        ]

    @beartype
    def get_supplier_breakdown(self, query: str, period: str = "last_month", limit: int = 6) -> list[SupplierBreakdown]:
        if not self.enabled:
            return []
        cleaned = " ".join(query.strip().split())
        if not cleaned:
            return []
        where_sql, args = build_like_clause("search_text", cleaned)
        period_clause = period_sql_clause("nakl_date", period)
        sql = f"""
SELECT
    COALESCE(supplier, '') AS supplier,
    COALESCE(SUM(qty), 0) AS qty_sum,
    COUNT(*) AS purchase_count,
    COALESCE(MAX(nakl_date), '') AS last_date
FROM purchase_lines
WHERE ({where_sql})
{period_clause}
GROUP BY supplier
ORDER BY qty_sum DESC, purchase_count DESC, supplier ASC
LIMIT ?
""".strip()
        with self._connect() as conn:
            rows = conn.execute(sql, [*args, int(limit)]).fetchall()
        return [
            SupplierBreakdown(
                supplier=str(item["supplier"]).strip(),
                qty_sum=float(item["qty_sum"] or 0),
                purchase_count=int(item["purchase_count"] or 0),
                last_date=str(item["last_date"]).strip(),
            )
            for item in rows
            if str(item["supplier"]).strip()
        ]


class BotRefsClient:
    @beartype
    def __init__(self, db_path: str = "") -> None:
        self.db_path = Path(db_path).expanduser() if db_path else Path()

    @property
    def enabled(self) -> bool:
        return self.db_path.exists() and self.db_path.is_file()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    @beartype
    def _load_alias_rows_by_ean(self, ean: str) -> list[sqlite3.Row]:
        if not self.enabled or not ean:
            return []
        with self._connect() as conn:
            return conn.execute(
                """
SELECT ean, id_name, id_mak, canonical_name, canonical_maker, source
FROM product_aliases
WHERE ean = ?
ORDER BY source ASC, canonical_name ASC, canonical_maker ASC
""".strip(),
                (ean,),
            ).fetchall()

    @beartype
    def _load_alias_rows_by_id_name(self, id_name: int) -> list[sqlite3.Row]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            return conn.execute(
                """
SELECT ean, id_name, id_mak, canonical_name, canonical_maker, source
FROM product_aliases
WHERE id_name = ?
ORDER BY source ASC, canonical_name ASC, canonical_maker ASC
""".strip(),
                (id_name,),
            ).fetchall()

    @beartype
    def _choose_identity(self, rows: list[sqlite3.Row], *, fallback_name: str = "", fallback_maker: str = "", matched_via: str = "") -> RefIdentity | None:
        if not rows:
            return None

        groups: dict[str, list[sqlite3.Row]] = {}
        for row in rows:
            key = make_identity_key(
                int(row["id_name"]) if row["id_name"] is not None else None,
                str(row["canonical_name"] or "").strip(),
                str(row["canonical_maker"] or "").strip(),
            )
            groups.setdefault(key, []).append(row)

        normalized_fallback_name = normalize_search_text(fallback_name)
        normalized_fallback_maker = normalize_search_text(fallback_maker)

        def score_group(group_rows: list[sqlite3.Row]) -> tuple[int, int, int, str]:
            sample = group_rows[0]
            name = str(sample["canonical_name"] or "").strip()
            maker = str(sample["canonical_maker"] or "").strip()
            normalized_name = normalize_search_text(name)
            normalized_maker = normalize_search_text(maker)
            maker_match = 1 if normalized_fallback_maker and normalized_fallback_maker == normalized_maker else 0
            name_match = 1 if normalized_fallback_name and normalized_fallback_name in normalized_name else 0
            alias_count = len({str(row["ean"]).strip() for row in group_rows if str(row["ean"]).strip()})
            return (maker_match, name_match, alias_count, f"{name}|{maker}")

        ordered_groups = sorted(groups.values(), key=score_group, reverse=True)
        chosen = ordered_groups[0]
        sample = chosen[0]
        alias_eans = tuple(sorted({str(row["ean"]).strip() for row in chosen if str(row["ean"]).strip()}))
        return RefIdentity(
            key=make_identity_key(
                int(sample["id_name"]) if sample["id_name"] is not None else None,
                str(sample["canonical_name"] or "").strip() or fallback_name,
                str(sample["canonical_maker"] or "").strip() or fallback_maker,
            ),
            id_name=int(sample["id_name"]) if sample["id_name"] is not None else None,
            id_mak=int(sample["id_mak"]) if sample["id_mak"] is not None else None,
            name=str(sample["canonical_name"] or "").strip() or fallback_name,
            maker=str(sample["canonical_maker"] or "").strip() or fallback_maker,
            alias_eans=alias_eans,
            matched_via=matched_via,
        )

    @beartype
    def resolve_identity(
        self,
        *,
        ean: str = "",
        id_name: int | None = None,
        name: str = "",
        maker: str = "",
    ) -> RefIdentity | None:
        if not self.enabled:
            fallback_name = name.strip()
            fallback_maker = maker.strip()
            if not fallback_name and id_name is None:
                return None
            return RefIdentity(
                key=make_identity_key(id_name, fallback_name, fallback_maker),
                id_name=id_name,
                id_mak=None,
                name=fallback_name,
                maker=fallback_maker,
                alias_eans=tuple([ean] if ean else []),
                matched_via="fallback",
            )

        alias_rows = self._load_alias_rows_by_ean(ean.strip()) if ean.strip() else []
        if alias_rows:
            chosen = self._choose_identity(alias_rows, fallback_name=name, fallback_maker=maker, matched_via="ean")
            if chosen and chosen.id_name is not None:
                rows_for_id_name = self._load_alias_rows_by_id_name(chosen.id_name)
                richer = self._choose_identity(rows_for_id_name, fallback_name=chosen.name, fallback_maker=chosen.maker, matched_via="ean_alias")
                if richer:
                    return richer
            if chosen:
                return chosen

        if id_name is not None:
            rows_for_id_name = self._load_alias_rows_by_id_name(id_name)
            chosen = self._choose_identity(rows_for_id_name, fallback_name=name, fallback_maker=maker, matched_via="id_name")
            if chosen:
                return chosen

        fallback_name = name.strip()
        fallback_maker = maker.strip()
        if not fallback_name and id_name is None:
            return None
        return RefIdentity(
            key=make_identity_key(id_name, fallback_name, fallback_maker),
            id_name=id_name,
            id_mak=None,
            name=fallback_name,
            maker=fallback_maker,
            alias_eans=tuple([ean] if ean else []),
            matched_via="fallback",
        )

    @beartype
    def search_catalog(self, query: str, limit: int = 5) -> list[CatalogProduct]:
        if not self.enabled:
            return []
        cleaned = " ".join(query.strip().split())
        if not cleaned:
            return []
        where_sql, args = build_like_clause("(search_name || ' ' || search_maker)", cleaned)
        sql = f"""
SELECT
    MIN(ean) AS ean,
    canonical_name AS name,
    COALESCE(canonical_maker, '') AS maker,
    id_name,
    COUNT(DISTINCT ean) AS alias_count
FROM product_aliases
WHERE {where_sql}
GROUP BY canonical_name, canonical_maker, id_name
ORDER BY alias_count DESC, canonical_name ASC
LIMIT ?
""".strip()
        with self._connect() as conn:
            rows = conn.execute(sql, [*args, int(limit)]).fetchall()
        return [
            CatalogProduct(
                ean=str(item["ean"]).strip(),
                name=str(item["name"]).strip(),
                maker=str(item["maker"]).strip(),
                id_name=int(item["id_name"]) if item["id_name"] is not None else None,
                offer_count=int(item["alias_count"] or 0),
                best_priority=999,
            )
            for item in rows
            if item["ean"]
        ]

    @beartype
    def aggregate_purchase_summaries(self, items: list[HistoryProductSummary]) -> list[HistoryProductSummary]:
        if not items:
            return []

        grouped: dict[str, dict[str, Any]] = {}
        for item in items:
            identity = self.resolve_identity(ean=item.ean, name=item.name, maker=item.maker)
            key = identity.key if identity else make_identity_key(None, item.name, item.maker)
            if key not in grouped:
                grouped[key] = {
                    "ean": item.ean,
                    "name": identity.name if identity and identity.name else item.name,
                    "maker": identity.maker if identity and identity.maker else item.maker,
                    "qty_sum": 0.0,
                    "purchase_count": 0,
                    "last_date": "",
                    "supplier_totals": {},
                }
            bucket = grouped[key]
            bucket["qty_sum"] += float(item.qty_sum or 0)
            bucket["purchase_count"] += int(item.purchase_count or 0)
            if str(item.last_date or "").strip() > str(bucket["last_date"] or "").strip():
                bucket["last_date"] = str(item.last_date or "").strip()
            supplier = str(item.top_supplier or "").strip()
            if supplier:
                bucket["supplier_totals"][supplier] = bucket["supplier_totals"].get(supplier, 0.0) + float(item.top_supplier_qty or item.qty_sum or 0)

        summaries: list[HistoryProductSummary] = []
        for bucket in grouped.values():
            top_supplier = ""
            top_supplier_qty = 0.0
            if bucket["supplier_totals"]:
                top_supplier, top_supplier_qty = max(
                    bucket["supplier_totals"].items(),
                    key=lambda item: (float(item[1]), str(item[0])),
                )
            summaries.append(
                HistoryProductSummary(
                    ean=str(bucket["ean"]).strip(),
                    name=str(bucket["name"]).strip(),
                    maker=str(bucket["maker"]).strip(),
                    qty_sum=float(bucket["qty_sum"] or 0),
                    purchase_count=int(bucket["purchase_count"] or 0),
                    last_date=str(bucket["last_date"]).strip(),
                    top_supplier=top_supplier,
                    top_supplier_qty=float(top_supplier_qty or 0),
                )
            )

        summaries.sort(
            key=lambda item: (item.qty_sum, item.purchase_count, item.last_date),
            reverse=True,
        )
        return summaries


class HistoryAnalyticsClient:
    @beartype
    def __init__(
        self,
        host: str = "",
        username: str = "",
        password: str = "",
        db_path: str = "/opt/pharmorder/src/data/order_history.db",
        timeout: float = 20.0,
    ) -> None:
        self.host = host.strip()
        self.username = username.strip()
        self.password = password
        self.db_path = db_path.strip() or "/opt/pharmorder/src/data/order_history.db"
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.host and self.username and self.password and self.db_path)

    @beartype
    def _exec_remote_json(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        if not self.enabled:
            return []

        safe_payload = dict(payload)
        safe_payload["period"] = normalize_period(str(payload.get("period", "last_month")))
        payload_b64 = base64.b64encode(json.dumps(safe_payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
        script = f"""
import base64
import json
import re
import sqlite3

payload = json.loads(base64.b64decode("{payload_b64}").decode("utf-8"))
query = payload["query"].strip()
variants = [v for v in payload.get("variants", []) if v]
if not variants and query:
    variants = [query]
period = payload.get("period", "last_month")
match = re.fullmatch(r"last_(\\d+)_days", period)
dynamic_days = int(match.group(1)) if match else None
if period not in {{"last_month", "this_month", "last_90_days", "last_180_days", "all_time"}} and not (dynamic_days and 1 <= dynamic_days <= 3650):
    period = "last_month"
    dynamic_days = None
limit = int(payload.get("limit", 5))
db_path = payload["db_path"]

period_clause = ""
period_args = []
if period == "last_month":
    period_clause = "AND date(nakl_date) >= date('now','start of month','-1 month') AND date(nakl_date) < date('now','start of month')"
elif period == "this_month":
    period_clause = "AND date(nakl_date) >= date('now','start of month')"
elif period == "last_90_days":
    period_clause = "AND date(nakl_date) >= date('now','-90 days')"
elif period == "last_180_days":
    period_clause = "AND date(nakl_date) >= date('now','-180 days')"
elif dynamic_days:
    period_clause = "AND date(nakl_date) >= date('now','-%s days')" % dynamic_days

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
variant_tokens = []
for variant in variants:
    prepared = variant.replace(",", " ").replace("š", " ").replace("mg", " ").replace("ěă", " ")
    tokens = [token.strip() for token in prepared.split() if token.strip()]
    if tokens:
        variant_tokens.append(tokens)

query_clauses = []
query_args = []
for tokens in variant_tokens:
    token_clauses = []
    for token in tokens:
        token_clauses.append("tovar LIKE ?")
        query_args.append(f"%{{token}}%")
    query_clauses.append("(" + " AND ".join(token_clauses) + ")")

query_clause = " OR ".join(query_clauses) if query_clauses else "1=0"

sql = f'''
WITH filtered AS (
    SELECT ean, tovar, maker, post, date(nakl_date) AS nakl_day, COALESCE(kol, 0) AS qty
    FROM orders
    WHERE ({{query_clause}})
    {{period_clause}}
),
product_totals AS (
    SELECT ean, tovar, maker, SUM(qty) AS qty_sum, COUNT(*) AS purchase_count, MAX(nakl_day) AS last_date
    FROM filtered
    GROUP BY ean, tovar, maker
),
supplier_totals AS (
    SELECT ean, post, SUM(qty) AS supplier_qty
    FROM filtered
    GROUP BY ean, post
),
ranked_suppliers AS (
    SELECT ean, post, supplier_qty,
           ROW_NUMBER() OVER (PARTITION BY ean ORDER BY supplier_qty DESC, post ASC) AS rn
    FROM supplier_totals
)
SELECT
    p.ean,
    p.tovar AS name,
    COALESCE(p.maker, '') AS maker,
    COALESCE(p.qty_sum, 0) AS qty_sum,
    COALESCE(p.purchase_count, 0) AS purchase_count,
    COALESCE(p.last_date, '') AS last_date,
    COALESCE(r.post, '') AS top_supplier,
    COALESCE(r.supplier_qty, 0) AS top_supplier_qty
FROM product_totals p
LEFT JOIN ranked_suppliers r ON r.ean = p.ean AND r.rn = 1
ORDER BY p.qty_sum DESC, p.purchase_count DESC, p.last_date DESC
LIMIT ?
'''

rows = cur.execute(sql, [*query_args, *period_args, limit]).fetchall()
print(json.dumps([dict(row) for row in rows], ensure_ascii=False))
""".strip()
        command = "python3 - <<'PY'\n" + script + "\nPY"

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self.host,
            username=self.username,
            password=self.password,
            timeout=self.timeout,
        )
        try:
            _stdin, stdout, stderr = client.exec_command(command, timeout=self.timeout)
            out = stdout.read().decode("utf-8", errors="replace").strip()
            err = stderr.read().decode("utf-8", errors="replace").strip()
        finally:
            client.close()

        if err:
            raise RuntimeError(f"SSH history query failed: {err}")
        if not out:
            return []
        payload_out = json.loads(out)
        if not isinstance(payload_out, list):
            raise RuntimeError(f"Unexpected SSH history payload: {payload_out!r}")
        return payload_out

    @beartype
    def get_purchase_summary(self, query: str, period: str = "last_month", limit: int = 5) -> list[HistoryProductSummary]:
        cleaned = " ".join(query.strip().split())
        variants = build_query_variants(cleaned)
        raw_items = self._exec_remote_json({
            "query": cleaned,
            "variants": variants,
            "period": period,
            "limit": limit,
            "db_path": self.db_path,
        })
        return [
            HistoryProductSummary(
                ean=str(item.get("ean", "")).strip(),
                name=str(item.get("name", "")).strip(),
                maker=str(item.get("maker", "")).strip(),
                qty_sum=float(item.get("qty_sum", 0) or 0),
                purchase_count=int(item.get("purchase_count", 0) or 0),
                last_date=str(item.get("last_date", "")).strip(),
                top_supplier=str(item.get("top_supplier", "")).strip(),
                top_supplier_qty=float(item.get("top_supplier_qty", 0) or 0),
            )
            for item in raw_items
        ]

    @beartype
    def get_supplier_breakdown(self, query: str, period: str = "last_month", limit: int = 6) -> list[SupplierBreakdown]:
        cleaned = " ".join(query.strip().split())
        variants = build_query_variants(cleaned)
        payload = {
            "query": cleaned,
            "variants": variants,
            "period": period,
            "limit": limit,
            "db_path": self.db_path,
        }
        payload_b64 = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
        script = f"""
import base64
import json
import re
import sqlite3

payload = json.loads(base64.b64decode("{payload_b64}").decode("utf-8"))
query = payload["query"].strip()
variants = [v for v in payload.get("variants", []) if v]
if not variants and query:
    variants = [query]
period = payload.get("period", "last_month")
match = re.fullmatch(r"last_(\\d+)_days", period)
dynamic_days = int(match.group(1)) if match else None
if period not in {{"last_month", "this_month", "last_90_days", "last_180_days", "all_time"}} and not (dynamic_days and 1 <= dynamic_days <= 3650):
    period = "last_month"
    dynamic_days = None
limit = int(payload.get("limit", 6))
db_path = payload["db_path"]

period_clause = ""
if period == "last_month":
    period_clause = "AND date(nakl_date) >= date('now','start of month','-1 month') AND date(nakl_date) < date('now','start of month')"
elif period == "this_month":
    period_clause = "AND date(nakl_date) >= date('now','start of month')"
elif period == "last_90_days":
    period_clause = "AND date(nakl_date) >= date('now','-90 days')"
elif period == "last_180_days":
    period_clause = "AND date(nakl_date) >= date('now','-180 days')"
elif dynamic_days:
    period_clause = "AND date(nakl_date) >= date('now','-%s days')" % dynamic_days

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
variant_tokens = []
for variant in variants:
    prepared = variant.replace(",", " ").replace("ЕЎ", " ").replace("mg", " ").replace("Д›Дѓ", " ")
    tokens = [token.strip() for token in prepared.split() if token.strip()]
    if tokens:
        variant_tokens.append(tokens)

query_clauses = []
query_args = []
for tokens in variant_tokens:
    token_clauses = []
    for token in tokens:
        token_clauses.append("tovar LIKE ?")
        query_args.append(f"%{{token}}%")
    query_clauses.append("(" + " AND ".join(token_clauses) + ")")

query_clause = " OR ".join(query_clauses) if query_clauses else "1=0"
sql = f'''
SELECT
    COALESCE(post, '') AS supplier,
    COALESCE(SUM(COALESCE(kol, 0)), 0) AS qty_sum,
    COUNT(*) AS purchase_count,
    COALESCE(MAX(date(nakl_date)), '') AS last_date
FROM orders
WHERE ({{query_clause}})
{{period_clause}}
GROUP BY post
ORDER BY qty_sum DESC, purchase_count DESC, supplier ASC
LIMIT ?
'''

rows = cur.execute(sql, [*query_args, limit]).fetchall()
print(json.dumps([dict(row) for row in rows], ensure_ascii=False))
""".strip()
        command = "python3 - <<'PY'\n" + script + "\nPY"

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self.host,
            username=self.username,
            password=self.password,
            timeout=self.timeout,
        )
        try:
            _stdin, stdout, stderr = client.exec_command(command, timeout=self.timeout)
            out = stdout.read().decode("utf-8", errors="replace").strip()
            err = stderr.read().decode("utf-8", errors="replace").strip()
        finally:
            client.close()

        if err:
            raise RuntimeError(f"SSH supplier breakdown failed: {err}")
        if not out:
            return []
        payload_out = json.loads(out)
        return [
            SupplierBreakdown(
                supplier=str(item.get("supplier", "")).strip(),
                qty_sum=float(item.get("qty_sum", 0) or 0),
                purchase_count=int(item.get("purchase_count", 0) or 0),
                last_date=str(item.get("last_date", "")).strip(),
            )
            for item in payload_out
            if str(item.get("supplier", "")).strip()
        ]

    @beartype
    def search_catalog(
        self,
        query: str,
        limit: int = 5,
        catalog_db_path: str = "/opt/pharmorder/src/data/sklit_cache.db",
    ) -> list[CatalogProduct]:
        if not self.enabled:
            return []

        cleaned = " ".join(query.strip().split())
        if not cleaned:
            return []

        variants = build_query_variants(cleaned)

        payload = {
            "variants": variants,
            "limit": limit,
            "db_path": catalog_db_path,
        }
        payload_b64 = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
        script = f"""
import base64
import json
import sqlite3

payload = json.loads(base64.b64decode("{payload_b64}").decode("utf-8"))
variants = [v for v in payload.get("variants", []) if v]
limit = int(payload.get("limit", 5))
db_path = payload["db_path"]

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

variant_tokens = []
for variant in variants:
    prepared = variant.replace(",", " ").replace("š", " ").replace("mg", " ").replace("ěă", " ")
    tokens = [token.strip() for token in prepared.split() if token.strip()]
    if tokens:
        variant_tokens.append(tokens)

clauses = []
args = []
for tokens in variant_tokens:
    token_clauses = []
    for token in tokens:
        token_clauses.append("(name LIKE ? OR maker LIKE ?)")
        args.extend([f"%{{token}}%", f"%{{token}}%"])
    clauses.append("(" + " AND ".join(token_clauses) + ")")

where_sql = " OR ".join(clauses) if clauses else "1=0"
sql = f'''
SELECT
    ean,
    name,
    COALESCE(maker, '') AS maker,
    id_name,
    COUNT(*) AS offer_count,
    MIN(COALESCE(supplier_priority, 999)) AS best_priority
FROM products
WHERE {{where_sql}}
GROUP BY ean, name, maker, id_name
ORDER BY best_priority ASC, offer_count DESC, name ASC
LIMIT ?
'''.replace("{{where_sql}}", where_sql)

rows = cur.execute(sql, [*args, limit]).fetchall()
print(json.dumps([dict(row) for row in rows], ensure_ascii=False))
""".strip()
        command = "python3 - <<'PY'\n" + script + "\nPY"

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self.host,
            username=self.username,
            password=self.password,
            timeout=self.timeout,
        )
        try:
            _stdin, stdout, stderr = client.exec_command(command, timeout=self.timeout)
            out = stdout.read().decode("utf-8", errors="replace").strip()
            err = stderr.read().decode("utf-8", errors="replace").strip()
        finally:
            client.close()

        if err:
            raise RuntimeError(f"SSH catalog search failed: {err}")
        if not out:
            return []
        payload_out = json.loads(out)
        return [
            CatalogProduct(
                ean=str(item.get("ean", "")).strip(),
                name=str(item.get("name", "")).strip(),
                maker=str(item.get("maker", "")).strip(),
                id_name=int(item["id_name"]) if item.get("id_name") is not None else None,
                offer_count=int(item.get("offer_count", 0) or 0),
                best_priority=int(item.get("best_priority", 999) or 999),
            )
            for item in payload_out
            if item.get("ean")
        ]
