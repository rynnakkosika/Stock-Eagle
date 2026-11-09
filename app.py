"""Stock Eagle – Streamlit UI. Run: streamlit run app.py"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from stock_eagle.changes import DOWNGRADE, TARGET_ONLY, UPGRADE, detect_changes, recent
from stock_eagle.config import load_settings, load_watchlist
from stock_eagle.consensus import SORT_KEYS, build_rows, filter_rows, latest_per_key, sort_rows
from stock_eagle.db import Database
from stock_eagle.refresh import refresh_all
from stock_eagle.scale import LABEL_ORDER, label
from stock_eagle.sources import discover

DISCLAIMER = (
    "**Ei sijoitusneuvontaa.** Stock Eagle vain kokoaa ja esittää kolmansien osapuolten "
    "julkaisemia tietoja. Järjestys on pelkkä lajittelu lähteiden datasta. Tarkista tiedot aina "
    "alkuperäisestä lähteestä."
)

st.set_page_config(page_title="Stock Eagle", page_icon="🦅", layout="wide")


# ---------------------------------------------------------------- setup -------------------
@st.cache_resource
def get_db(path: str) -> Database:
    return Database(path)


def _secrets_to_env() -> None:
    """Streamlit Cloud: copy secrets (Settings → Secrets) into the environment.

    Locally there is usually no secrets.toml, and .env is used instead.
    """
    import os

    try:
        # every top-level secret, so a new source's key needs no change here
        for key, value in st.secrets.items():
            if isinstance(value, (str, int, float, bool)) and not os.environ.get(key):
                os.environ[key] = str(value)
    except Exception:  # no secrets file → nothing to copy
        pass


_secrets_to_env()
settings = load_settings()
try:
    stocks = load_watchlist(settings.watchlist_path)
except Exception as exc:  # pragma: no cover - UI path
    st.error(f"Seurantalistan luku epäonnistui ({settings.watchlist_path}): {exc}")
    st.stop()
db = get_db(str(settings.db_path))
db.sync_stocks(stocks)
adapters = discover()
source_names = {a.id: a.name for a in adapters}
enabled_ids = [a.id for a in adapters if a.availability(settings)[0]]


def fmt_ts(value: str | None) -> str:
    """UTC ISO timestamp → local 'dd.mm.yyyy HH:MM'."""
    if not value:
        return "–"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone()
        return dt.strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return value


def fmt_date(value: str | None) -> str:
    if not value:
        return "–"
    try:
        return datetime.fromisoformat(value[:10]).strftime("%d.%m.%Y")
    except ValueError:
        return value


def _table_css() -> str:
    dark = False
    try:
        dark = st.context.theme.type == "dark"
    except Exception:
        pass
    bg, head, line, stripe, link = (
        ("#0e1117", "#262730", "#3a3b45", "#16181f", "#7cb8ff") if dark
        else ("#ffffff", "#f0f2f6", "#e1e4ea", "#fafbfc", "#1a5fb4"))
    return f"""<style>
.se-wrap {{max-height: calc(100vh - 9rem); max-height: calc(100dvh - 9rem); overflow: auto;
  overscroll-behavior: contain; -webkit-overflow-scrolling: touch;
  border: 1px solid {line}; border-radius: 8px; background: {bg};}}
.se-table {{border-collapse: separate; border-spacing: 0; width: 100%; font-size: 14px;}}
.se-table th, .se-table td {{padding: 6px 10px; white-space: nowrap; text-align: left;
  border-bottom: 1px solid {line}; background: {bg};}}
.se-table tbody tr:nth-child(even) td {{background: {stripe};}}
.se-table th {{position: sticky; top: 0; z-index: 2; background: {head}; font-weight: 600;}}
.se-table td.num, .se-table th.num {{text-align: right; font-variant-numeric: tabular-nums;}}
.se-table .pin {{position: sticky; left: 0; z-index: 1; border-right: 1px solid {line};}}
.se-table th.pin {{z-index: 3;}}
.se-table a {{color: {link};}}
/* Phone (portrait): no inner scroll box, so the header row sticks below Streamlit's top
   bar while the whole page scrolls; only the key columns are shown so nothing needs
   horizontal scrolling. */
@media (max-width: 640px) {{
  .se-wrap {{max-height: none; overflow: visible; border-radius: 0;}}
  .se-table {{font-size: 13px;}}
  .se-table th, .se-table td {{padding: 6px 6px;}}
  .se-table th {{top: 3.75rem;}}
  .se-table .pin {{position: static; border-right: none;}}
  .se-table th.pin {{position: sticky;}}
  .se-table .wide {{display: none;}}
  .se-table td.pin {{white-space: normal;}}
}}
</style>"""


def sticky_table(rows: list[dict], numeric: tuple[str, ...] = (),
                 links: tuple[str, ...] = (), phone_cols: int = 4) -> None:
    """Table whose header row stays visible while scrolling.

    Wide screens: own scroll box, header on top and first column on the left.
    Phones: the header sticks to the top of the screen while the page scrolls, and only the
    first `phone_cols` columns are shown (turn the phone sideways to see all of them).
    `rows` hold display values; columns in `links` are URLs shown as "Avaa lähde".
    """
    import html

    if not rows:
        return
    cols = list(rows[0])

    def cell(tag: str, col: str, value, i: int) -> str:
        classes = " ".join(c for c in ("pin" if i == 0 else "",
                                       "num" if col in numeric else "",
                                       "wide" if i >= phone_cols else "") if c)
        attr = f' class="{classes}"' if classes else ""
        if tag == "td" and col in links:
            body = (f'<a href="{html.escape(str(value), quote=True)}" target="_blank" '
                    f'rel="noopener">Avaa lähde</a>' if value else "–")
        else:
            body = html.escape("–" if value is None or value == "" else str(value))
        return f"<{tag}{attr}>{body}</{tag}>"

    head = "".join(cell("th", c, c, i) for i, c in enumerate(cols))
    body = "".join("<tr>" + "".join(cell("td", c, r[c], i) for i, c in enumerate(cols))
                   + "</tr>" for r in rows)
    st.html(f'{_table_css()}<div class="se-wrap"><table class="se-table"><thead><tr>{head}'
            f"</tr></thead><tbody>{body}</tbody></table></div>")


def fmt_pct(value: float | None) -> str:
    return "–" if value is None else f"{value * 100:+.1f} %"


def fmt_num(value: float | None) -> str:
    return "–" if value is None else f"{value:.2f}"


def src_name(source_id: str) -> str:
    return source_names.get(source_id, source_id)


# ---------------------------------------------------------------- sidebar -----------------
with st.sidebar:
    st.title("🦅 Stock Eagle")
    st.caption("Analyytikkosuositusten koonti – Helsingin pörssi")
    if settings.demo_mode:
        st.warning("**Demotila** – Finnhub-avainta ei löytynyt. Finnhubin tilalla näytetään "
                   "keksittyä esimerkkidataa (lähde *DEMO*). Lisää `FINNHUB_API_KEY` "
                   "`.env`-tiedostoon ja käynnistä sovellus uudelleen.")

    if st.button("🔄 Päivitä data", type="primary", use_container_width=True):
        with st.status("Haetaan dataa lähteistä …", expanded=True) as status:
            reports = refresh_all(db, stocks, settings, adapters=adapters,
                                  progress=lambda m: st.write(m))
            failed = [r for r in reports if r.status == "error"]
            status.update(label="Päivitys valmis" + (" (virheitä)" if failed else ""),
                          state="error" if failed else "complete")
        st.rerun()

    st.subheader("Lähteet")
    runs = db.last_runs()
    for a in adapters:
        enabled, reason = a.availability(settings)
        run = runs.get(a.id)
        icon = {"ok": "🟢", "partial": "🟡", "error": "🔴"}.get(run["status"] if run else "", "⚪")
        if not enabled:
            icon = "⚫"
        st.markdown(f"{icon} **[{a.name}]({a.homepage})**")
        if not enabled:
            st.caption(f"Ei käytössä: {reason}")
        elif run:
            st.caption(f"Haettu {fmt_ts(run['finished_at'])} · {run['n_records']} suositusta")
            if run["message"]:
                with st.expander("Viestit"):
                    st.write(run["message"])
        else:
            st.caption("Ei vielä haettu – paina Päivitä data.")
    st.divider()
    st.info(DISCLAIMER)

# ---------------------------------------------------------------- data --------------------
all_recs = db.recommendations(sources=enabled_ids)
all_quotes = db.quotes(sources=enabled_ids)
stock_meta = db.stocks()
meta_by = {s["ticker"]: s for s in stock_meta}

if not all_recs:
    st.info("Ei vielä dataa. Paina vasemmalta **🔄 Päivitä data**.")
    st.caption(DISCLAIMER)
    st.stop()

tab_rank, tab_stock, tab_changes, tab_sources = st.tabs(
    ["📊 Paremmuusjärjestys", "🔎 Osake", "🔔 Muutokset", "ℹ️ Lähteet ja asteikko"])

# ---------------------------------------------------------------- ranking -----------------
with tab_rank:
    c1, c2, c3, c4 = st.columns([1, 2, 2, 2])
    sort_key = c1.selectbox("Järjestys", list(SORT_KEYS), format_func=SORT_KEYS.get)
    sel_sources = c2.multiselect("Lähde", enabled_ids, default=enabled_ids, format_func=src_name)
    sel_labels = c3.multiselect("Suositus (konsensus)", LABEL_ORDER)
    sectors = sorted({s["sector"] for s in stock_meta if s["sector"]})
    sel_sectors = c4.multiselect("Toimiala", sectors)

    recs = [r for r in all_recs if r.source_id in set(sel_sources)]
    rows = sort_rows(filter_rows(build_rows(recs, all_quotes, stock_meta), sel_labels,
                                 sel_sectors), sort_key)
    table = [{
        "Osake": f"{i + 1}. {r.name}",
        "Konsensus": r.label,
        "Nousuvara": fmt_pct(r.upside),
        "Kpl": r.n_recommendations,
        "Pisteet": fmt_num(r.consensus),
        "Keskitavoite": fmt_num(r.avg_target),
        "Kurssi": fmt_num(r.price),
        "Valuutta": r.currency,
        "Tunnus": r.ticker,
        "Toimiala": r.sector,
        "Uusin suositus": fmt_date(r.latest_date),
        "Lähteet": ", ".join(src_name(s) for s in r.sources),
        "Kurssin lähde": src_name(r.quote_source) if r.quote_source else "–",
    } for i, r in enumerate(rows)]
    st.caption(f"{len(rows)} osaketta · lähteet: {', '.join(src_name(s) for s in sel_sources)}")
    if not table:
        st.warning("Suodattimilla ei löytynyt osakkeita.")
    else:
        sticky_table(table, numeric=("Pisteet", "Nousuvara", "Kpl", "Keskitavoite", "Kurssi"))
    st.caption("Pisteet: 5 = Osta, 4 = Lisää, 3 = Pidä, 2 = Vähennä, 1 = Myy. Konsensus on "
               "analyytikkomäärillä painotettu keskiarvo. Nousuvara = keskitavoitehinta / kurssi − 1. "
               "Puhelimella näkyvät pääsarakkeet – käännä puhelin vaakaan nähdäksesi kaikki.")

# ---------------------------------------------------------------- stock view --------------
with tab_stock:
    tickers = sorted({r.ticker for r in all_recs}, key=lambda t: meta_by.get(t, {}).get("name", t))
    ticker = st.selectbox(
        "Valitse osake", tickers,
        format_func=lambda t: f"{meta_by.get(t, {}).get('name', t)} ({t})")
    srecs = [r for r in all_recs if r.ticker == ticker]
    row = build_rows(srecs, [q for q in all_quotes if q.ticker == ticker], stock_meta)[0]
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Konsensus", row.label, help=f"Pisteet {row.consensus:.2f} / 5")
    m2.metric("Suosituksia", row.n_recommendations)
    m3.metric("Keskitavoite", f"{row.avg_target:.2f} {row.currency}" if row.avg_target else "–")
    m4.metric("Kurssi", f"{row.price:.2f} {row.currency}" if row.price else "–",
              help=f"Lähde: {src_name(row.quote_source)} · haettu {fmt_ts(row.quote_fetched_at)}"
              if row.quote_source else None)
    m5.metric("Nousuvara", f"{row.upside * 100:+.1f} %" if row.upside is not None else "–")

    st.subheader("Suositukset lähteittäin")
    latest = sorted(latest_per_key(srecs), key=lambda r: (r.source_id, r.analyst))
    sticky_table([{
        "Lähde": src_name(r.source_id),
        "Yhtenäistetty": f"{label(r.rating)} ({r.rating:.2f})",
        "Tavoitehinta": fmt_num(r.target_price),
        "Linkki": r.url,
        "Valuutta": r.currency,
        "Suosituksen pvm": fmt_date(r.rec_date),
        "Analyytikko": r.analyst or f"Konsensus ({r.analyst_count} analyytikkoa)",
        "Alkuperäinen suositus": r.rating_raw,
        "Haettu": fmt_ts(r.last_seen_at),
    } for r in latest], numeric=("Tavoitehinta",), links=("Linkki",))

    st.subheader("Suositushistoria")
    changes = detect_changes(srecs, include_initial=True)
    if changes:
        arrows = {UPGRADE: "▲ Nosto", DOWNGRADE: "▼ Lasku", TARGET_ONLY: "◆ Tavoitehinta"}
        sticky_table([{
            "Pvm": fmt_date(c.date),
            "Lähde": src_name(c.source_id),
            "Muutos": arrows.get(c.kind, "● Ensimmäinen havainto"),
            "Suositus": f"{c.old_label} → {c.new_label}" if c.old_rating is not None
            else c.new_label,
            "Tavoite": (f"{fmt_num(c.old_target)} → {fmt_num(c.new_target)}"
                        if c.old_rating is not None else fmt_num(c.new_target)),
            "Analyytikko": c.analyst or "Konsensus",
            "Linkki": c.url,
        } for c in changes], links=("Linkki",))
        hist = pd.DataFrame([{"Pvm": r.rec_date, "Lähde": src_name(r.source_id)
                              + (f" / {r.analyst}" if r.analyst else ""), "Pisteet": r.rating}
                             for r in srecs])
        if hist["Pvm"].nunique() > 1:
            pivot = hist.pivot_table(index="Pvm", columns="Lähde", values="Pisteet",
                                     aggfunc="last").sort_index()
            st.line_chart(pivot, y_label="Pisteet (1–5)")
    st.caption("Historia kertyy lähteiden ilmoittamista ajankohdista ja sovelluksen "
               "omista hakukerroista.")

# ---------------------------------------------------------------- changes -----------------
with tab_changes:
    c1, c2, c3 = st.columns([2, 2, 2])
    days = c1.select_slider("Aikaikkuna (päivää)", [7, 14, 30, 60, 90, 180, 365], value=30)
    ch_sources = c2.multiselect("Lähde ", enabled_ids, default=enabled_ids, format_func=src_name)
    kinds = c3.multiselect("Tyyppi", [UPGRADE, DOWNGRADE, TARGET_ONLY],
                           default=[UPGRADE, DOWNGRADE, TARGET_ONLY])
    ch = [c for c in recent(detect_changes([r for r in all_recs if r.source_id in ch_sources]),
                            days) if c.kind in kinds]
    st.caption(f"{len(ch)} muutosta viimeisen {days} päivän aikana")
    if ch:
        arrows = {UPGRADE: "▲ Nosto", DOWNGRADE: "▼ Lasku", TARGET_ONLY: "◆ Tavoitehinta"}
        sticky_table([{
            "Osake": meta_by.get(c.ticker, {}).get("name", c.ticker),
            "Pvm": fmt_date(c.date),
            "Muutos": arrows[c.kind],
            "Suositus": f"{c.old_label} → {c.new_label}",
            "Vanha tavoite": fmt_num(c.old_target),
            "Uusi tavoite": fmt_num(c.new_target),
            "Tavoitteen muutos": fmt_pct(c.target_change_pct),
            "Lähde": src_name(c.source_id),
            "Analyytikko": c.analyst or "Konsensus",
            "Havaittu": fmt_ts(c.fetched_at),
            "Linkki": c.url,
        } for c in ch], numeric=("Vanha tavoite", "Uusi tavoite", "Tavoitteen muutos"),
            links=("Linkki",))
    else:
        st.info("Ei muutoksia valitulla aikavälillä. Muutoksia syntyy, kun lähteen suositus tai "
                "tavoitehinta muuttuu hakukertojen välillä.")

# ---------------------------------------------------------------- sources -----------------
with tab_sources:
    st.subheader("Datalähteet")
    for a in adapters:
        enabled, reason = a.availability(settings)
        st.markdown(f"**[{a.name}]({a.homepage})** – {'käytössä' if enabled else 'ei käytössä'}"
                    f"{': ' + reason if reason and not enabled else ''}  \n{a.description}")
    st.subheader("Yhtenäistetty asteikko")
    st.table(pd.DataFrame({
        "Pisteet": [5, 4, 3, 2, 1],
        "Suositus": ["Osta", "Lisää", "Pidä", "Vähennä", "Myy"],
        "Finnhub": ["strongBuy", "buy", "hold", "sell", "strongSell"],
        "Inderes": ["Osta", "Lisää", "Pidä", "Vähennä", "Myy"],
    }))
    st.caption("Kolmiportaiset asteikot (buy/hold/sell) kuvataan arvoihin 5/3/1. Koostetuilla "
               "lähteillä (Finnhub) pisteet ovat analyytikkomäärillä painotettu keskiarvo.")
    st.info(DISCLAIMER)
