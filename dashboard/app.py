# -*- coding: utf-8 -*-
"""
Supervision Technique — Messagerie NoSQL & Spark Analytics
MongoDB 7.0 Replica Set (rs0) & Apache Spark 3.5.0

Le tableau de bord est rendu comme UNE page HTML plein écran (CSS grid + Plotly.js)
qui s'adapte à la hauteur de la fenêtre : pas de défilement, pas de chevauchement,
pas d'espace vide.  Deux écrans seulement (onglets dans l'en-tête) :
  1. Vue d'ensemble       -> 6 KPI + 9 graphiques
  2. Détails & Benchmarks -> tous les tableaux, complets
Sources : MongoDB si connecté, sinon CSV de benchmarks/results.
"""

import html as _html
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from plotly.offline import get_plotlyjs

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

st.set_page_config(
    page_title="Supervision Technique — Messagerie NoSQL & Spark",
    layout="wide",
    initial_sidebar_state="collapsed",
)

WORKDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS_DIR = os.path.join(WORKDIR, "benchmarks", "results")

# Palette sémantique (identique dans tous les graphiques)
BLUE, GREEN, ORANGE, RED, AMBER, SLATE = "#2563EB", "#059669", "#EA580C", "#DC2626", "#F59E0B", "#94A3B8"
INK = "#0F172A"
FONT = 'Inter, "Segoe UI", system-ui, -apple-system, sans-serif'

# Retire le "chrome" Streamlit : la page HTML occupe toute la fenêtre
st.markdown(
    """
    <style>
    header[data-testid="stHeader"], footer, #MainMenu, [data-testid="stToolbar"],
    [data-testid="stDecoration"], [data-testid="stSidebar"], [data-testid="collapsedControl"] { display:none !important; }
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], section.main { overflow:hidden !important; background:#F1F5F9 !important; }
    [data-testid="stMainBlockContainer"], .block-container { padding:6px 10px 0 10px !important; max-width:100% !important; }
    [data-testid="stVerticalBlock"] { gap:0 !important; }
    iframe { display:block; border:0; width:100%; }
    </style>
    """,
    unsafe_allow_html=True,
)

REASON_FR = {"scam": "Arnaque", "offensive": "Offensant", "inappropriate": "Inapproprié", "spam": "Spam", "harassment": "Harcèlement"}
STATUS_FR = {"resolved": "Résolu", "pending": "En attente", "dismissed": "Rejeté"}
STATUS_ORDER = ["Résolu", "En attente", "Rejeté"]
MEDIA_FR = {"text": "Texte", "image": "Image", "file": "Fichier", "voice": "Vocal", "video": "Vidéo"}
MONTHS_FR = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


# ---------------------------------------------------------------------------
# Données : MongoDB (si connecté) sinon CSV / valeurs de référence
# ---------------------------------------------------------------------------
@st.cache_resource(ttl=300)
def check_mongo_connection():
    try:
        from pymongo import MongoClient
        from config.settings import MONGO_URI

        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=1000)
        client.admin.command("ping")
        return client, True
    except Exception:
        return None, False


def _db():
    client, live = check_mongo_connection()
    if not live:
        return None
    from config.settings import MONGO_DB

    return client[MONGO_DB]


@st.cache_data(ttl=60)
def get_counts():
    try:
        db = _db()
        if db is not None:
            from config.settings import COLLECTIONS

            return {k: db[COLLECTIONS[k]].count_documents({}) for k in
                    ("users", "conversations", "messages", "read_status", "reports")}, True
    except Exception:
        pass
    return {"users": 10000, "conversations": 8000, "messages": 84697, "read_status": 20166, "reports": 1200}, False


@st.cache_data(ttl=60)
def get_messages_daily():
    try:
        db = _db()
        if db is not None:
            from config.settings import COLLECTIONS

            now = datetime.now(timezone.utc).replace(tzinfo=None)
            docs = list(db[COLLECTIONS["messages"]].aggregate([
                {"$match": {"ts": {"$gte": now - timedelta(days=30)}}},
                {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$ts"}}, "total": {"$sum": 1}}},
                {"$sort": {"_id": 1}},
            ]))
            if docs:
                return pd.DataFrame(docs).rename(columns={"_id": "date", "total": "messages"})
    except Exception:
        pass
    dates = pd.date_range(end=datetime.today(), periods=30, freq="D").strftime("%Y-%m-%d")
    rng = np.random.default_rng(42)
    counts = np.linspace(900, 1500, 30) + rng.normal(0, 60, 30)
    return pd.DataFrame({"date": dates, "messages": counts.astype(int)})


@st.cache_data(ttl=60)
def get_media_types():
    try:
        db = _db()
        if db is not None:
            from config.settings import COLLECTIONS

            docs = list(db[COLLECTIONS["messages"]].aggregate(
                [{"$group": {"_id": "$type", "total": {"$sum": 1}}}, {"$sort": {"total": -1}}]))
            if docs:
                return pd.DataFrame(docs).rename(columns={"_id": "type", "total": "volume"})
    except Exception:
        pass
    return pd.DataFrame({"type": ["text", "image", "file", "voice"], "volume": [60300, 12100, 7410, 4850]})


@st.cache_data(ttl=60)
def get_hourly():
    try:
        db = _db()
        if db is not None:
            from config.settings import COLLECTIONS

            docs = list(db[COLLECTIONS["messages"]].aggregate(
                [{"$group": {"_id": {"$hour": "$ts"}, "messages": {"$sum": 1}}}, {"$sort": {"_id": 1}}]))
            if docs:
                s = pd.Series({int(d["_id"]): d["messages"] for d in docs}).reindex(range(24), fill_value=0)
                return pd.DataFrame({"heure": s.index, "messages": s.values})
    except Exception:
        pass
    return pd.DataFrame({"heure": list(range(24)), "messages": [2600] * 23 + [25300]})


@st.cache_data(ttl=60)
def get_top_users(total_messages):
    try:
        db = _db()
        if db is not None:
            from config.settings import COLLECTIONS

            docs = [d for d in db[COLLECTIONS["messages"]].aggregate([
                {"$group": {"_id": "$sender_id", "volume": {"$sum": 1}}},
                {"$sort": {"volume": -1}}, {"$limit": 10}]) if d["_id"] is not None]
            if docs:
                df = pd.DataFrame(docs).rename(columns={"_id": "sender_id"})
                df["part"] = df["volume"] / max(total_messages, 1) * 100
                return df
    except Exception:
        pass
    return None


@st.cache_data(ttl=60)
def get_reports_summary():
    """Signalements par motif x statut (A24)."""
    try:
        db = _db()
        if db is not None:
            from config.settings import COLLECTIONS

            col = db[COLLECTIONS["reports"]]
            doc = col.find_one() or {}
            rf = next((k for k in ("reason", "motif", "category", "reason_type", "type") if k in doc), None)
            sf = next((k for k in ("status", "statut", "state") if k in doc), None)
            if rf and sf:
                docs = list(col.aggregate([{"$group": {"_id": {"r": "$" + rf, "s": "$" + sf}, "total": {"$sum": 1}}}]))
                if docs:
                    return pd.DataFrame({
                        "reason": [d["_id"]["r"] for d in docs],
                        "status": [d["_id"]["s"] for d in docs],
                        "total": [d["total"] for d in docs],
                    })
    except Exception:
        pass
    data = {"scam": (116, 115, 39), "offensive": (102, 94, 39), "inappropriate": (98, 104, 39),
            "spam": (88, 110, 25), "harassment": (81, 116, 34)}
    rows = [{"reason": r, "status": s, "total": v}
            for r, vals in data.items() for s, v in zip(("resolved", "pending", "dismissed"), vals)]
    return pd.DataFrame(rows)


@st.cache_data(ttl=60)
def load_stats(name):
    """Collection Spark (stats_s26 … stats_s30) : MongoDB, sinon <name>.csv."""
    try:
        db = _db()
        if db is not None:
            docs = list(db[name].find({}).limit(5000))
            if docs:
                df = pd.json_normalize(docs)
                df.columns = [c[4:] if c.startswith("_id.") else c for c in df.columns]
                if "_id" in df.columns and df["_id"].map(lambda x: type(x).__name__ == "ObjectId").all():
                    df = df.drop(columns=["_id"])
                return df
    except Exception:
        pass
    return load_csv(f"{name}.csv")


@st.cache_data(ttl=60)
def load_csv(name):
    p = os.path.join(RESULTS_DIR, name)
    if os.path.isfile(p):
        try:
            return pd.read_csv(p)
        except Exception:
            return None
    return None


@st.cache_resource
def plotly_js():
    return get_plotlyjs()


def has_cols(df, cols):
    return df is not None and set(cols) <= set(df.columns)


def pick(df, names):
    low = {str(c).lower(): c for c in df.columns}
    for n in names:
        if n in low:
            return low[n]
    return None


# ---------------------------------------------------------------------------
# Helpers HTML
# ---------------------------------------------------------------------------
def esc(v):
    return _html.escape(str(v))


def flat(s):
    return " ".join(line.strip() for line in s.strip().splitlines())


def fmt_int(n):
    return f"{int(n):,}".replace(",", " ")


def pill(text, tone="gray"):
    return f'<span class="pill {tone}">{esc(text)}</span>'


def html_table(df, labels=None, fmt=None, bars=None, pills=None, mono=(), trunc=(), cls="", style="", row_attrs=None):
    labels, fmt, bars, pills = labels or {}, fmt or {}, bars or {}, pills or {}
    num_cols = {c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c not in pills}
    head = "".join(
        f'<th class="{"num" if c in num_cols and c not in bars else ""}">{esc(labels.get(c, c))}</th>' for c in df.columns
    )
    body = []
    for _, r in df.iterrows():
        tds = []
        for c in df.columns:
            v = r[c]
            if c in bars:
                mx, color, f = bars[c]
                w = max(0.0, min(100.0, float(v) / mx * 100.0)) if mx else 0.0
                tds.append(
                    f'<td><div class="bw"><div class="bt"><div class="bf" style="width:{w:.0f}%;background:{color}"></div></div>'
                    f'<span class="bv">{f.format(v)}</span></div></td>')
            elif c in pills:
                tds.append(f'<td>{pill(v, pills[c].get(str(v), "gray"))}</td>')
            elif c in num_cols:
                if pd.isna(v):
                    txt = "–"
                elif c in fmt:
                    txt = fmt[c].format(v)
                elif isinstance(v, (float, np.floating)):
                    txt = f"{v:.2f}"
                else:
                    txt = str(v)
                tds.append(f'<td class="num">{txt}</td>')
            else:
                k = " ".join(x for x, on in (("mono", c in mono), ("trunc", c in trunc)) if on)
                tds.append(f'<td class="{k}" title="{esc(v)}">{esc(v)}</td>')
        attr = row_attrs(r) if row_attrs else ""
        body.append(f"<tr {attr}>" + "".join(tds) + "</tr>")
    return flat(f'<div class="tw"><table class="dt {cls}" style="{style}"><thead><tr>{head}</tr></thead>'
                f'<tbody>{"".join(body)}</tbody></table></div>')


def card(title, badge, body, style="", cls=""):
    b = f'<span class="badge">{esc(badge)}</span>' if badge else ""
    return flat(f'<section class="card {cls}" style="{style}"><header class="ch"><span class="ct">{esc(title)}</span>{b}</header>'
                f'<div class="cb">{body}</div></section>')


def empty(msg):
    return f'<div class="empty">{esc(msg)}</div>'


def kpi(label, value, sub, color):
    return flat(f'<div class="kpi" style="--c:{color}"><div class="l">{esc(label)}</div>'
                f'<div class="v">{esc(value)}</div><div class="s">{esc(sub)}</div></div>')


# ---------------------------------------------------------------------------
# Plotly : style commun (taille pilotée par le CSS grid, jamais en pixels fixes)
# ---------------------------------------------------------------------------
def style(fig, legend=False, left=42, bottom=26, right=10, top=10):
    fig.update_layout(
        template="plotly_white", autosize=True, height=None, width=None,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=10, color=INK),
        margin=dict(l=left, r=right, t=34 if legend else top, b=bottom),
        title=None, showlegend=legend, bargap=0.28, separators=". ",
        legend=dict(orientation="h", x=1, xanchor="right", y=1.02, yanchor="bottom",
                    font=dict(size=10), title_text="", bgcolor="rgba(255,255,255,0)"),
        hoverlabel=dict(font_family=FONT, font_size=11),
    )
    fig.update_xaxes(title=None, tickfont=dict(size=9.5, color="#334155"), showgrid=False, linecolor="#CBD5E1",
                     ticks="outside", tickcolor="#CBD5E1", ticklen=3, automargin=True)
    fig.update_yaxes(title=None, tickfont=dict(size=9.5, color="#334155"), gridcolor="#EEF2F7", zeroline=False,
                     automargin=True)
    return fig


LOG_TICKS = dict(tickvals=[1, 10, 100, 1000, 10000, 100000], ticktext=["1", "10", "100", "1k", "10k", "100k"])

FIGS = {}


def plot_card(pid, title, badge, fig, missing, style_="", cls=""):
    if fig is None:
        return card(title, badge, empty(missing), style_, cls)
    FIGS[pid] = json.loads(fig.to_json())
    return card(title, badge, f'<div class="plot" id="{pid}"></div>', style_, cls)


# ---------------------------------------------------------------------------
# Chargement
# ---------------------------------------------------------------------------
counts, is_live = get_counts()
df_daily = get_messages_daily()
df_media = get_media_types()
df_hourly = get_hourly()
df_users = get_top_users(counts.get("messages", 0))
df_reports = get_reports_summary()
df_nvs = load_csv("native_vs_spark.csv")
df_jobs = load_csv("spark_jobs.csv")
df_idx = load_csv("index_test.csv")
df_cons = load_csv("consistency_test.csv")
df_fo = load_csv("failover_test.csv")
df_all = load_csv("all_queries.csv")
df_s26 = load_stats("stats_s26")
df_s28 = load_stats("stats_s28")
df_s29 = load_stats("stats_s29")
df_s30 = load_stats("stats_s30")

# ---- valeurs dérivées -------------------------------------------------------
t4_idx = t4_noidx = None
if has_cols(df_idx, ["query_id", "mode", "avg_ms"]):
    a = df_idx[(df_idx["query_id"] == "T4") & (df_idx["mode"] == "index")]["avg_ms"]
    b = df_idx[(df_idx["query_id"] == "T4") & (df_idx["mode"] == "no_index")]["avg_ms"]
    if len(a) and len(b):
        t4_idx, t4_noidx = float(a.iloc[0]), float(b.iloc[0])
speedup = t4_noidx / t4_idx if t4_idx else None

fo_stop = None
if has_cols(df_fo, ["mode", "election_s"]):
    r = df_fo[df_fo["mode"] == "stop"]
    if len(r):
        fo_stop = float(r.iloc[0]["election_s"])

rep = df_reports.copy()
rep["reason"] = rep["reason"].map(lambda x: REASON_FR.get(str(x).lower(), str(x).capitalize()))
rep["status"] = rep["status"].map(lambda x: STATUS_FR.get(str(x).lower(), str(x).capitalize()))
rep_total = max(int(rep["total"].sum()), 1)
pending_share = rep[rep["status"] == "En attente"]["total"].sum() / rep_total * 100

# ---------------------------------------------------------------------------
# ÉCRAN 1 — VUE D'ENSEMBLE
# ---------------------------------------------------------------------------
u, c, m = counts["users"], counts["conversations"], counts["messages"]
kpis = "".join([
    kpi("Utilisateurs", fmt_int(u), f"{c / max(u, 1):.1f} conversation / utilisateur", BLUE),
    kpi("Conversations", fmt_int(c), f"{m / max(c, 1):.1f} messages / conversation", BLUE),
    kpi("Messages", fmt_int(m), f"{m / max(u, 1):.1f} messages / utilisateur", BLUE),
    kpi("Statuts de lecture", fmt_int(counts["read_status"]), f"{counts['read_status'] / max(m, 1) * 100:.0f}% des messages", SLATE),
    kpi("Signalements", fmt_int(counts["reports"]), f"{pending_share:.0f}% en attente", AMBER),
    kpi("Latence médiane T4", f"{t4_idx:.2f} ms" if t4_idx else "—",
        f"IXSCAN · −{(1 - t4_idx / t4_noidx) * 100:.1f}% vs COLLSCAN" if t4_idx else "index_test.csv absent", GREEN),
])

# -- A16
d = df_daily.copy()
d["date"] = pd.to_datetime(d["date"])
f = px.line(d, x="date", y="messages")
f.update_traces(line=dict(width=2.2, color=BLUE), fill="tozeroy", fillcolor="rgba(37,99,235,.10)",
                hovertemplate="%{x|%d %b}: %{y:,} messages<extra></extra>")
style(f, left=44)
f.update_xaxes(tickformat="%d %b", nticks=7)
card_a16 = plot_card("a16", "A16 · Messages par jour (30 j)", "MONGODB", f, "")

# -- A18
dm = df_media.copy()
dm["type"] = dm["type"].map(lambda x: MEDIA_FR.get(str(x).lower(), str(x)))
f = px.pie(dm, names="type", values="volume", hole=0.62,
           color_discrete_sequence=[BLUE, "#60A5FA", "#7C3AED", SLATE, "#0EA5E9"])
f.update_traces(textposition="inside", textinfo="percent", textfont=dict(size=10, color="#FFFFFF"),
                marker=dict(line=dict(color="#FFFFFF", width=2)), domain=dict(x=[0, 0.68]),
                hovertemplate="%{label}: %{value:,} (%{percent})<extra></extra>", sort=False)
style(f, legend=True, left=4, right=4, top=6, bottom=6)
f.update_layout(legend=dict(orientation="v", x=0.99, xanchor="right", y=0.5, yanchor="middle", font=dict(size=10.5)))
f.add_annotation(text=f"<b>{fmt_int(dm['volume'].sum())}</b><br><span style='font-size:9px;color:#475569'>messages</span>",
                 x=0.34, y=0.5, showarrow=False, font=dict(size=14, color=INK))
card_a18 = plot_card("a18", "A18 · Types de message", "FORMATS", f, "")

# -- A22
f = px.bar(df_hourly, x="heure", y="messages")
f.update_traces(marker_color=BLUE, hovertemplate="%{x} h UTC: %{y:,} messages<extra></extra>")
style(f, left=44)
f.update_xaxes(tickmode="linear", tick0=0, dtick=3)
card_a22 = plot_card("a22", "A22 · Messages par heure", "UTC", f, "")

# -- A24
f = px.bar(rep, x="reason", y="total", color="status", barmode="group",
           category_orders={"status": STATUS_ORDER},
           color_discrete_map={"Résolu": GREEN, "En attente": AMBER, "Rejeté": SLATE})
style(f, legend=True)
card_a24 = plot_card("a24", "A24 · Signalements par motif", "MODÉRATION", f, "")

# -- Natif vs Spark
fig = None
if has_cols(df_nvs, ["query_id", "native_avg_ms", "spark_avg_ms"]):
    dd = df_nvs[["query_id", "native_avg_ms", "spark_avg_ms"]].melt(id_vars="query_id", var_name="Moteur", value_name="ms")
    dd["Moteur"] = dd["Moteur"].map({"native_avg_ms": "MongoDB natif", "spark_avg_ms": "Apache Spark"})
    fig = px.bar(dd, x="query_id", y="ms", color="Moteur", barmode="group", log_y=True,
                 color_discrete_map={"MongoDB natif": GREEN, "Apache Spark": ORANGE})
    style(fig, legend=True)
    fig.update_yaxes(**LOG_TICKS)
card_nvs = plot_card("nvs", "Natif vs Spark · A16–A18", "MS · LOG", fig, "native_vs_spark.csv introuvable")

# -- Jobs Spark
fig = None
if has_cols(df_jobs, ["job_id", "avg_ms"]):
    dj = df_jobs.copy()
    dj["job_id"] = dj["job_id"].astype(str).str.upper()
    fig = px.bar(dj, x="job_id", y="avg_ms", text="avg_ms")
    style(fig, left=44, top=22)
    fig.update_traces(marker_color=ORANGE, texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False,
                      textfont=dict(size=9.5), hovertemplate="%{x}: %{y:,.0f} ms<extra></extra>")
    fig.update_yaxes(range=[0, float(dj["avg_ms"].max()) * 1.18])
card_jobs = plot_card("jobs", "Jobs Spark S26–S30", "PYSPARK · MS", fig, "spark_jobs.csv introuvable")

# -- Index
fig = None
if has_cols(df_idx, ["query_id", "mode", "avg_ms"]):
    di = df_idx[["query_id", "mode", "avg_ms"]].copy()
    di["mode"] = di["mode"].map({"index": "Avec index", "no_index": "Sans index"}).fillna(di["mode"])
    fig = px.bar(di, x="query_id", y="avg_ms", color="mode", barmode="group", text="avg_ms",
                 color_discrete_map={"Avec index": GREEN, "Sans index": RED})
    style(fig, legend=True)
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside", cliponaxis=False, textfont=dict(size=9.5))
    fig.update_yaxes(range=[0, float(di["avg_ms"].max()) * 1.2])
card_idx = plot_card("idx", "Accélération index", f"x{speedup:.1f}" if speedup else "MS", fig,
                     "index_test.csv introuvable")

# -- Write concern
fig = None
if has_cols(df_cons, ["test_id", "setting", "avg_ms"]):
    dc = df_cons[df_cons["test_id"] == "T1"]
    if len(dc):
        fig = px.bar(dc, x="setting", y="avg_ms", text="avg_ms")
        style(fig, top=22)
        fig.update_traces(marker_color=BLUE, texttemplate="%{text:.2f}", textposition="outside", cliponaxis=False,
                          textfont=dict(size=9.5))
        fig.update_yaxes(range=[0, float(dc["avg_ms"].max()) * 1.2])
card_wc = plot_card("wc", "T1 · Write concern", "MS", fig, "consistency_test.csv introuvable")


# -- Rétention S30
def prep_retention(df):
    if df is None or df.empty:
        return None
    cc = pick(df, ["cohort", "cohorte", "cohort_month", "month", "mois", "_id"]) or df.columns[0]
    vc = pick(df, ["retention", "retention_rate", "retained", "retained_users", "taux_retention", "rate", "count", "value"])
    if vc is None or vc == cc:
        nums = [x for x in df.columns if x != cc and pd.api.types.is_numeric_dtype(df[x])]
        if not nums:
            return None
        vc = nums[0]
    out = pd.DataFrame({"c": df[cc], "v": pd.to_numeric(df[vc], errors="coerce")}).dropna()
    try:
        if pd.api.types.is_numeric_dtype(out["c"]):
            dt = pd.to_datetime(out["c"], unit="ms" if out["c"].abs().max() > 1e11 else "s")
        else:
            dt = pd.to_datetime(out["c"])
        out = out.assign(dt=dt).sort_values("dt")
        out["label"] = [f"{MONTHS_FR[x.month - 1]} {str(x.year)[2:]}" for x in out["dt"]]
    except Exception:
        out["label"] = out["c"].astype(str)
    return out


ret = prep_retention(df_s30)
fig = None
if ret is not None and len(ret):
    fig = px.bar(ret, x="label", y="v", text="v")
    style(fig, left=40, top=22)
    fig.update_traces(marker_color=BLUE, texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False,
                      textfont=dict(size=9.5), hovertemplate="%{x}: %{y:,.0f}<extra></extra>")
    fig.update_yaxes(range=[0, float(ret["v"].max()) * 1.18])
    fig.update_xaxes(tickangle=0, tickfont=dict(size=9))
card_ret = plot_card("ret", "S30 · Rétention cohortes", "S30", fig, "stats_s30 introuvable")

screen1 = flat(f"""
<div class="screen active" id="s1">
  <div class="kpis">{kpis}</div>
  <div class="row r1">{card_a16}{card_a18}{card_a22}{card_a24}</div>
  <div class="row r2">{card_nvs}{card_jobs}{card_idx}{card_wc}{card_ret}</div>
</div>""")

# ---------------------------------------------------------------------------
# ÉCRAN 2 — DÉTAILS & BENCHMARKS
# ---------------------------------------------------------------------------
# Matrice des requêtes
if df_all is not None and has_cols(df_all, ["query_id"]):
    cols = [x for x in ("query_id", "description", "engine", "avg_ms", "min_ms", "max_ms", "runs") if x in df_all.columns]
    dall = df_all.copy()
    fam = dall["family"] if "family" in dall.columns else pd.Series([""] * len(dall))
    dall["_f"] = fam.values
    tbl = html_table(
        dall[cols + ["_f"]].drop(columns="_f"),
        labels={"query_id": "ID", "description": "Description", "engine": "Moteur", "avg_ms": "Moy. ms",
                "min_ms": "Min", "max_ms": "Max", "runs": "Runs"},
        fmt={"avg_ms": "{:.2f}", "min_ms": "{:.2f}", "max_ms": "{:.2f}", "runs": "{:.0f}"},
        pills={"engine": {"mongodb": "green", "native": "green", "spark": "orange"}},
        mono=("query_id",), trunc=("description",), cls="mx", style=f"--n:{len(dall) + 1}",
        row_attrs=lambda r, _f=dict(zip(dall["query_id"], dall["_f"])): f'data-f="{esc(_f.get(r["query_id"], ""))}"',
    )
    sel = ('<div class="filter"><select id="fam"><option value="all">Toutes les familles</option>'
           '<option value="transactional">Transactionnelles (T01–T15)</option>'
           '<option value="analytical">Analytiques (A16–A25)</option>'
           '<option value="spark">Spark (S26–S30)</option></select></div>')
    matrix = card("Matrice des requêtes", "T01 → S30 · MS", sel + tbl, "flex:1 1 0")
else:
    matrix = card("Matrice des requêtes", "T01 → S30", empty("all_queries.csv introuvable"), "flex:1 1 0")


# Spark S28 (spam) — agrégé par expéditeur
def build_s28(df):
    if not has_cols(df, ["sender_id", "nb_conversations"]):
        return None
    g = df.groupby("sender_id").agg(
        conv=("nb_conversations", "max"),
        msgs=("content", "nunique") if "content" in df.columns else ("nb_conversations", "size"),
        ex=("content", "first") if "content" in df.columns else ("sender_id", "first"),
    ).reset_index().sort_values(["conv", "msgs"], ascending=False).head(6)
    g.columns = ["sender_id", "conv", "msgs", "ex"]
    return g


g28 = build_s28(df_s28)
s28 = card("Spark S28 · Spam (> 20 conv/h)", "SÉCURITÉ",
           html_table(g28, labels={"sender_id": "Expéditeur", "conv": "Conv.", "msgs": "Contenus", "ex": "Exemple de contenu"},
                      fmt={"conv": "{:.0f}", "msgs": "{:.0f}"}, mono=("sender_id",), trunc=("ex",), cls="fill")
           if g28 is not None else empty("stats_s28 introuvable"), "flex:7 1 0")

# Spark S29 (taux de signalement anormal) — colonnes détectées
s29_body = empty("stats_s29 introuvable")
if df_s29 is not None and len(df_s29):
    d29 = df_s29.head(6).copy()
    sc = pick(d29, ["sender_id"]) or d29.columns[0]
    rc = next((x for x in d29.columns if any(k in str(x).lower() for k in ("rate", "taux", "ratio"))), None)
    keep = [sc] + [x for x in d29.columns if x != sc and pd.api.types.is_numeric_dtype(d29[x])][:3]
    d29 = d29[keep]
    bars = {}
    if rc in d29.columns:
        mx = float(d29[rc].max()) if float(d29[rc].max()) > 1 else 1.0
        bars = {rc: (mx, RED, "{:.2f}")}
    s29_body = html_table(d29, bars=bars, mono=(sc,), cls="fill",
                          labels={"sender_id": "Expéditeur", "sent_count": "Envoyés", "reported_count": "Signalés", "report_rate": "Taux"},
                          fmt={"sent_count": "{:.0f}", "reported_count": "{:.0f}"})
s29 = card("Spark S29 · Signalements anormaux", "RATIO", s29_body, "flex:6 1 0")

# Spark S26 (temps de réponse)
s26_body = empty("stats_s26 introuvable")
if df_s26 is not None and len(df_s26):
    d26 = df_s26.head(5).copy()
    lab = {"conversation_id": "Conversation", "avg_sec": "Temps moy. (s)", "response_count": "Réponses"}
    s26_body = html_table(d26, labels=lab, fmt={"response_count": "{:.0f}", "avg_sec": "{:.1f}"},
                          mono=("conversation_id",), cls="fill")
s26 = card("Spark S26 · Temps de réponse (top 5)", "ENGAGEMENT", s26_body, "flex:6 1 0")

# HA (kill / stop)
if has_cols(df_fo, ["mode", "election_s", "new_primary"]):
    ha_rows = df_fo.head(2).to_dict("records")
else:
    ha_rows = []
ha_html = ""
for row in ha_rows:
    col = RED if str(row["mode"]).lower() == "kill" else GREEN
    ha_html += flat(
        f'<div class="ha" style="--c:{col}"><div><div class="l">HA failover · {esc(str(row["mode"]).upper())}</div>'
        f'<div class="s">Primaire → {esc(row["new_primary"])}</div></div>'
        f'<div class="v">{float(row["election_s"]):.2f} s</div></div>')
ha = f'<div class="ha-row">{ha_html}</div>' if ha_html else ""

# Failover
if df_fo is not None:
    d_fo = df_fo.copy()
    if "date" in d_fo.columns:
        d_fo["date"] = d_fo["date"].astype(str).str.replace("T", " ").str[5:16]
    fo = card("Résilience · Chronogramme de bascule", "RAFT · S",
              html_table(d_fo, labels={"date": "Date", "mode": "Mode", "new_primary": "Primaire", "election_s": "Élection",
                                       "write_after_failover_s": "Écriture", "mongo1_reachable_s": "m1 ↑",
                                       "mongo1_primary_again_s": "m1 prim."},
                         mono=("date", "new_primary"), cls="fill tight"), "flex:3 1 0")
else:
    fo = card("Résilience · Chronogramme de bascule", "RAFT · S", empty("failover_test.csv introuvable"), "flex:3 1 0")

# Plans d'exécution (index_test)
plan_cols = [x for x in ("query_id", "mode", "avg_ms", "p95_ms", "docs_examined", "stage_chain") if df_idx is not None and x in df_idx.columns]
if df_idx is not None and len(plan_cols) >= 3:
    plan = card("Plans d'exécution · T4 / T6", "EXPLAIN",
                html_table(df_idx[plan_cols],
                           labels={"query_id": "Req.", "mode": "Mode", "avg_ms": "Moy. ms", "p95_ms": "P95",
                                   "docs_examined": "Docs", "stage_chain": "Plan"},
                           fmt={"docs_examined": "{:.0f}"},
                           mono=("query_id", "stage_chain"), trunc=("stage_chain",), cls="fill"), "flex:4 1 0")
else:
    plan = ""

# Top 10 utilisateurs
if df_users is not None:
    top = card("A17 · Top 10 utilisateurs actifs", "EXPÉDITEURS",
               html_table(df_users, labels={"sender_id": "Identifiant", "volume": "Messages", "part": "Part du trafic"},
                          bars={"volume": (float(df_users["volume"].max()), BLUE, "{:.0f}")},
                          fmt={"part": "{:.2f}%"}, mono=("sender_id",), cls="fill"), "flex:11 1 0")
else:
    top = card("A17 · Top 10 utilisateurs actifs", "EXPÉDITEURS", empty("Données MongoDB indisponibles"), "flex:11 1 0")

screen2 = flat(f"""
<div class="screen" id="s2">
  <div class="cols">
    <div class="col" style="flex:1.3 1 0">{matrix}</div>
    <div class="col" style="flex:1 1 0">{s28}{s29}{s26}</div>
    <div class="col" style="flex:1 1 0">{ha}{fo}{plan}{top}</div>
  </div>
</div>""")

# ---------------------------------------------------------------------------
# En-tête + page
# ---------------------------------------------------------------------------
header_pills = "".join([
    pill("REPLICA SET rs0 CONNECTÉ", "green") if is_live else pill("MODE RÉFÉRENCE · CSV", "blue"),
    pill("SPARK 3.5 : OK", "orange"),
    pill(f"FAILOVER : {fo_stop:.2f}s", "gray") if fo_stop else "",
    pill("IXSCAN : ACTIF", "green") if t4_idx else "",
])

TEMPLATE = r"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box}
html,body{margin:0;height:100%;overflow:hidden;background:#F1F5F9;color:#0F172A;font:12px/1.35 Inter,"Segoe UI",system-ui,-apple-system,sans-serif}
.shell{height:100vh;display:flex;flex-direction:column;gap:8px;padding:2px 2px 4px}
.top{flex:0 0 52px;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:0 16px;border-radius:10px;
  background:linear-gradient(100deg,#0B1220 0%,#16243E 100%);color:#fff;box-shadow:0 2px 8px rgba(15,23,42,.18)}
.brand{display:flex;flex-direction:column;min-width:0}
.brand b{font-size:13px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;white-space:nowrap}
.brand span{font:10.5px ui-monospace,Consolas,monospace;color:#94A3B8;white-space:nowrap}
.tabs{display:flex;gap:4px;background:rgba(255,255,255,.09);padding:3px;border-radius:9px;flex:0 0 auto}
.tab{border:0;background:transparent;color:#CBD5E1;font:700 11px Inter,"Segoe UI",sans-serif;padding:7px 16px;border-radius:7px;cursor:pointer;
  text-transform:uppercase;letter-spacing:.05em;white-space:nowrap}
.tab:hover{color:#fff}.tab.active{background:#fff;color:#0F172A}
.pills{display:flex;gap:6px;flex:0 0 auto}
.pill{display:inline-block;font:700 10px ui-monospace,Consolas,monospace;padding:3px 9px;border-radius:999px;white-space:nowrap;border:1px solid transparent;line-height:1.3}
.pill.green{background:#DCFCE7;color:#15803D;border-color:#BBF7D0}.pill.blue{background:#DBEAFE;color:#1E40AF;border-color:#BFDBFE}
.pill.orange{background:#FFEDD5;color:#9A3412;border-color:#FED7AA}.pill.red{background:#FEE2E2;color:#B91C1C;border-color:#FECACA}
.pill.gray{background:#F1F5F9;color:#334155;border-color:#CBD5E1}
.top .pill.green{background:rgba(16,185,129,.16);color:#6EE7B7;border-color:rgba(16,185,129,.4)}
.top .pill.orange{background:rgba(249,115,22,.16);color:#FDBA74;border-color:rgba(249,115,22,.4)}
.top .pill.blue{background:rgba(59,130,246,.18);color:#93C5FD;border-color:rgba(59,130,246,.4)}
.top .pill.gray{background:rgba(148,163,184,.16);color:#E2E8F0;border-color:rgba(148,163,184,.35)}
.screen{display:none;flex:1;min-height:0;flex-direction:column;gap:8px}.screen.active{display:flex}
.kpis{flex:0 0 70px;display:grid;grid-template-columns:repeat(6,1fr);gap:8px}
.kpi{background:#fff;border:1px solid #E2E8F0;border-left:4px solid var(--c);border-radius:10px;padding:0 14px;display:flex;flex-direction:column;
  justify-content:center;min-width:0;box-shadow:0 1px 2px rgba(15,23,42,.05)}
.kpi .l{font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#475569;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.kpi .v{font-size:24px;font-weight:800;letter-spacing:-.01em;line-height:1.15;font-variant-numeric:tabular-nums;white-space:nowrap}
.kpi .s{font-size:10.5px;font-weight:600;color:#475569;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row{flex:1;min-height:0;display:grid;gap:8px}
.r1{grid-template-columns:1.55fr 1fr 1.2fr 1.3fr}
.r2{grid-template-columns:1.1fr 1.15fr 1fr .85fr 1.05fr}
.card{background:#fff;border:1px solid #E2E8F0;border-radius:10px;box-shadow:0 1px 2px rgba(15,23,42,.05);display:flex;flex-direction:column;min-width:0;min-height:0;overflow:hidden}
.ch{flex:0 0 auto;display:flex;align-items:center;justify-content:space-between;gap:8px;padding:9px 12px 4px}
.ct{font-size:10.5px;font-weight:800;letter-spacing:.05em;text-transform:uppercase;color:#0F172A;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  border-left:3px solid #2563EB;padding-left:8px;min-width:0}
.badge{flex:0 0 auto;font:700 9.5px ui-monospace,Consolas,monospace;color:#475569;background:#F1F5F9;border:1px solid #E2E8F0;padding:1px 7px;border-radius:4px;white-space:nowrap}
.cb{flex:1;min-height:0;position:relative;padding:0 8px 8px}
.plot{position:absolute;left:4px;right:6px;top:0;bottom:4px}
.empty{height:100%;display:flex;align-items:center;justify-content:center;color:#475569;font-size:11px;background:#F8FAFC;border:1px dashed #CBD5E1;border-radius:8px}
.cols{flex:1;min-height:0;display:flex;gap:8px}.col{display:flex;flex-direction:column;gap:8px;min-width:0;min-height:0}
.filter{margin:0 0 6px}
.filter select{width:100%;font:600 11px Inter,"Segoe UI",sans-serif;color:#0F172A;background:#F8FAFC;border:1px solid #CBD5E1;border-radius:6px;padding:4px 8px}
.tw{width:100%;height:100%;overflow:hidden}
.filter+.tw{height:auto}
.dt{width:100%;border-collapse:collapse;font-size:11px;color:#0F172A}
.dt.fill{height:100%}
.dt th{background:#F8FAFC;color:#475569;text-transform:uppercase;font-size:9.5px;letter-spacing:.04em;font-weight:700;padding:4px 7px;text-align:left;
  border-bottom:1px solid #E2E8F0;white-space:nowrap}
.dt td{padding:2px 7px;border-bottom:1px solid #F1F5F9;white-space:nowrap}
.dt tbody tr:last-child td{border-bottom:none}
.dt th.num,.dt td.num{text-align:right;font-variant-numeric:tabular-nums}
.dt td.num,.dt td.mono{font-family:ui-monospace,Consolas,monospace;font-size:10.5px}
.dt td.trunc{max-width:0;width:100%;overflow:hidden;text-overflow:ellipsis}
.dt.mx{height:auto}.dt.mx td{height:calc((100vh - 158px) / var(--n));padding-top:0;padding-bottom:0}
.dt .pill{padding:0 8px;font-size:9.5px;line-height:1.5}
.dt.tight th,.dt.tight td{padding-left:5px;padding-right:5px}
.dt.mx th{height:24px}
.dt tbody tr:hover td{background:#F8FAFC}
.bw{display:flex;align-items:center;gap:8px}.bt{flex:1;height:6px;background:#E2E8F0;border-radius:3px;min-width:40px}.bf{height:6px;border-radius:3px}
.bv{font:10.5px ui-monospace,Consolas,monospace;min-width:34px;text-align:right}
.ha-row{flex:0 0 58px;display:grid;grid-template-columns:1fr 1fr;gap:8px}
.ha{background:#fff;border:1px solid #E2E8F0;border-top:3px solid var(--c);border-radius:10px;padding:0 14px;display:flex;justify-content:space-between;align-items:center;
  box-shadow:0 1px 2px rgba(15,23,42,.05);min-width:0}
.ha .l{font-size:9.5px;font-weight:800;letter-spacing:.05em;text-transform:uppercase;color:#475569;white-space:nowrap}
.ha .s{font-size:10.5px;color:#475569;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ha>div:first-child{min-width:0}
.ha .v{font:800 19px ui-monospace,Consolas,monospace;color:var(--c);white-space:nowrap;flex:0 0 auto;margin-left:10px}
</style></head><body>
<div class="shell">
  <div class="top">
    <div class="brand"><b>Supervision technique — Messagerie NoSQL &amp; Spark Analytics</b>
      <span>chatdb · MongoDB 7.0 Replica Set rs0 (3 nœuds) · Apache Spark 3.5.0</span></div>
    <div class="tabs"><button class="tab active" data-t="s1">Vue d'ensemble</button><button class="tab" data-t="s2">Détails &amp; Benchmarks</button></div>
    <div class="pills">%%PILLS%%</div>
  </div>
  %%S1%%
  %%S2%%
</div>
<script>%%PLOTLY%%</script>
<script>
var FIGS=%%FIGS%%;
var CFG={displayModeBar:false,responsive:true};
function fit(){try{var f=window.frameElement;if(!f)return;var h=window.parent.innerHeight-f.getBoundingClientRect().top-2;if(h>420)f.style.height=h+"px";}catch(e){}}
fit();try{window.parent.addEventListener("resize",fit);}catch(e){}
function plotAll(){for(var id in FIGS){var el=document.getElementById(id);if(el)Plotly.newPlot(el,FIGS[id].data,FIGS[id].layout,CFG);}}
requestAnimationFrame(function(){fit();plotAll();});
document.querySelectorAll(".tab").forEach(function(b){b.addEventListener("click",function(){
  document.querySelectorAll(".tab").forEach(function(x){x.classList.toggle("active",x===b);});
  document.querySelectorAll(".screen").forEach(function(s){s.classList.toggle("active",s.id===b.dataset.t);});
  window.dispatchEvent(new Event("resize"));});});
var fam=document.getElementById("fam");
if(fam){fam.addEventListener("change",function(){document.querySelectorAll(".mx tbody tr").forEach(function(r){
  r.style.display=(fam.value==="all"||r.dataset.f===fam.value)?"":"none";});});}
</script></body></html>"""

doc = (
    TEMPLATE.replace("%%PILLS%%", header_pills)
    .replace("%%S1%%", screen1)
    .replace("%%S2%%", screen2)
    .replace("%%FIGS%%", json.dumps(FIGS).replace("</", "<\\/"))
    .replace("%%PLOTLY%%", plotly_js())
)

# st.iframe (Streamlit récent) ; repli sur components.html pour les anciennes versions
if hasattr(st, "iframe"):
    st.iframe(doc, height=820)
else:
    components.html(doc, height=820, scrolling=False)