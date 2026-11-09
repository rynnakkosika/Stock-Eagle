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
        for key in ("FINNHUB_API_KEY", "INDERES_ENABLED"):
            if key in st.secrets and not os.environ.get(key):
                os.environ[key] = str(st.secrets[key])
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


def table_height(n_rows: int, max_px: int = 420) -> int:
    """Fixed table height: a long table scrolls inside its own box, so the header row
    stays visible (also on a phone, where the whole page would otherwise scroll)."""
    return min(35 * (n_rows + 1) + 3, max_px)


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
    df = pd.DataFrame([{
        "#": i + 1,
        "Osake": r.name,
        "Tunnus": r.ticker,
        "Toimiala": r.sector,
        "Konsensus": r.label,
        "Pisteet (1–5)": r.consensus,
        "Suosituksia": r.n_recommendations,
        "Keskitavoite": r.avg_target,
        "Kurssi": r.price,
        "Valuutta": r.currency,
        "Nousuvara %": None if r.upside is None else r.upside * 100,
        "Uusin suositus": fmt_date(r.latest_date),
        "Lähteet": ", ".join(src_name(s) for s in r.sources),
        "Kurssin lähde": src_name(r.quote_source) if r.quote_source else "–",
    } for i, r in enumerate(rows)])
    st.caption(f"{len(rows)} osaketta · lähteet: {', '.join(src_name(s) for s in sel_sources)}")
    if df.empty:
        st.warning("Suodattimilla ei löytynyt osakkeita.")
    else:
        st.dataframe(
            df, hide_index=True, use_container_width=True, height=table_height(len(df), 520),
            column_config={
                "#": st.column_config.NumberColumn(width="small", pinned=True),
                "Osake": st.column_config.TextColumn(pinned=True),
                "Pisteet (1–5)": st.column_config.ProgressColumn(
                    format="%.2f", min_value=1, max_value=5),
                "Keskitavoite": st.column_config.NumberColumn(format="%.2f"),
                "Kurssi": st.column_config.NumberColumn(format="%.2f"),
                "Nousuvara %": st.column_config.NumberColumn(format="%+.1f %%"),
            },
        )
    st.caption("Pisteet: 5 = Osta, 4 = Lisää, 3 = Pidä, 2 = Vähennä, 1 = Myy. Konsensus on "
               "analyytikkomäärillä painotettu keskiarvo. Nousuvara = keskitavoitehinta / kurssi − 1.")

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
    st.dataframe(pd.DataFrame([{
        "Lähde": src_name(r.source_id),
        "Analyytikko": r.analyst or f"Konsensus ({r.analyst_count} analyytikkoa)",
        "Alkuperäinen suositus": r.rating_raw,
        "Yhtenäistetty": f"{label(r.rating)} ({r.rating:.2f})",
        "Tavoitehinta": r.target_price,
        "Valuutta": r.currency,
        "Suosituksen pvm": fmt_date(r.rec_date),
        "Haettu": fmt_ts(r.last_seen_at),
        "Linkki": r.url,
    } for r in latest]), hide_index=True, use_container_width=True,
        height=table_height(len(latest)), column_config={
        "Lähde": st.column_config.TextColumn(pinned=True),
        "Linkki": st.column_config.LinkColumn(display_text="Avaa lähde"),
        "Tavoitehinta": st.column_config.NumberColumn(format="%.2f"),
    })

    st.subheader("Suositushistoria")
    changes = detect_changes(srecs, include_initial=True)
    if changes:
        arrows = {UPGRADE: "▲ Nosto", DOWNGRADE: "▼ Lasku", TARGET_ONLY: "◆ Tavoitehinta"}
        st.dataframe(pd.DataFrame([{
            "Pvm": fmt_date(c.date),
            "Lähde": src_name(c.source_id),
            "Analyytikko": c.analyst or "Konsensus",
            "Muutos": arrows.get(c.kind, "● Ensimmäinen havainto"),
            "Suositus": f"{c.old_label} → {c.new_label}" if c.old_rating is not None
            else c.new_label,
            "Tavoite": (f"{fmt_num(c.old_target)} → {fmt_num(c.new_target)}"
                        if c.old_rating is not None else fmt_num(c.new_target)),
            "Linkki": c.url,
        } for c in changes]), hide_index=True, use_container_width=True,
            height=table_height(len(changes)), column_config={
            "Pvm": st.column_config.TextColumn(pinned=True),
            "Linkki": st.column_config.LinkColumn(display_text="Avaa lähde")})
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
        st.dataframe(pd.DataFrame([{
            "Pvm": fmt_date(c.date),
            "Osake": meta_by.get(c.ticker, {}).get("name", c.ticker),
            "Lähde": src_name(c.source_id),
            "Analyytikko": c.analyst or "Konsensus",
            "Muutos": arrows[c.kind],
            "Suositus": f"{c.old_label} → {c.new_label}",
            "Vanha tavoite": c.old_target,
            "Uusi tavoite": c.new_target,
            "Tavoitteen muutos %": (None if c.target_change_pct is None
                                    else c.target_change_pct * 100),
            "Havaittu": fmt_ts(c.fetched_at),
            "Linkki": c.url,
        } for c in ch]), hide_index=True, use_container_width=True,
            height=table_height(len(ch), 520), column_config={
            "Osake": st.column_config.TextColumn(pinned=True),
            "Linkki": st.column_config.LinkColumn(display_text="Avaa lähde"),
            "Vanha tavoite": st.column_config.NumberColumn(format="%.2f"),
            "Uusi tavoite": st.column_config.NumberColumn(format="%.2f"),
            "Tavoitteen muutos %": st.column_config.NumberColumn(format="%+.1f %%"),
        })
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
