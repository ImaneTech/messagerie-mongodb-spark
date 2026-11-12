import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from config.settings import MONGO_URI, MONGO_DB, COLLECTIONS

st.set_page_config(page_title="Messagerie — Tableau de bord", layout="wide")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "benchmarks", "results")
CSV_SEARCH_PATHS = (
    RESULTS_DIR,
    PROJECT_ROOT,
    os.path.dirname(__file__),
)


# ---------------------------------------------------------------------------
# Connexion MongoDB partagée
# ---------------------------------------------------------------------------

@st.cache_resource
def get_client():
    return MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)


def get_db():
    return get_client()[MONGO_DB]


# ---------------------------------------------------------------------------
# Fonctions de chargement des données
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def get_counts():
    try:
        db = get_db()
        result = {col: db[COLLECTIONS[col]].count_documents({}) for col in COLLECTIONS}
        return result
    except Exception as e:
        st.error(f"Erreur de connexion MongoDB: {e}")
        return {}


@st.cache_data(ttl=60)
def get_messages_per_day():
    try:
        db = get_db()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        start_30d = now - timedelta(days=30)
        pipeline = [
            {"$match": {"ts": {"$gte": start_30d}}},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$ts"}
                    },
                    "total": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        docs = list(db[COLLECTIONS["messages"]].aggregate(pipeline))
        return docs
    except Exception as e:
        st.error(f"Erreur de connexion MongoDB: {e}")
        return []


@st.cache_data(ttl=60)
def get_messages_by_type():
    try:
        db = get_db()
        pipeline = [
            {"$group": {"_id": "$type", "total": {"$sum": 1}}},
            {"$sort": {"total": -1}},
        ]
        docs = list(db[COLLECTIONS["messages"]].aggregate(pipeline))
        return docs
    except Exception as e:
        st.error(f"Erreur de connexion MongoDB: {e}")
        return []


@st.cache_data(ttl=60)
def get_messages_by_hour():
    try:
        db = get_db()
        pipeline = [
            {"$group": {"_id": {"$hour": "$ts"}, "total": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
        docs = list(db[COLLECTIONS["messages"]].aggregate(pipeline))
        return docs
    except Exception as e:
        st.error(f"Erreur de connexion MongoDB: {e}")
        return []


@st.cache_data(ttl=60)
def get_top_users(limit=10):
    try:
        db = get_db()
        pipeline = [
            {"$group": {"_id": "$sender_id", "total": {"$sum": 1}}},
            {"$sort": {"total": -1}},
            {"$limit": limit},
        ]
        docs = list(db[COLLECTIONS["messages"]].aggregate(pipeline))
        return docs
    except Exception as e:
        st.error(f"Erreur de connexion MongoDB: {e}")
        return []


@st.cache_data(ttl=60)
def get_reports_by_reason_status():
    try:
        db = get_db()
        pipeline = [
            {
                "$group": {
                    "_id": {"reason": "$reason", "status": "$status"},
                    "total": {"$sum": 1},
                }
            },
            {"$sort": {"total": -1}},
        ]
        docs = list(db[COLLECTIONS["reports"]].aggregate(pipeline))
        return docs
    except Exception as e:
        st.error(f"Erreur de connexion MongoDB: {e}")
        return []


@st.cache_data(ttl=60)
def get_stats_collection(collection_name, sort_field=None, ascending=True, limit=None):
    """Charge une collection stats_* ; retourne (docs, error_msg)."""
    try:
        db = get_db()
        if collection_name not in db.list_collection_names():
            return None, "Données non disponibles (job Spark non exécuté)."
        coll = db[collection_name]
        if coll.count_documents({}) == 0:
            return None, "Données non disponibles (job Spark non exécuté)."
        query = coll.find({}, {"_id": 0})
        if sort_field:
            direction = 1 if ascending else -1
            query = query.sort(sort_field, direction)
        if limit:
            query = query.limit(limit)
        docs = list(query)
        return docs, None
    except Exception as e:
        return None, f"Erreur de connexion MongoDB: {e}"


def load_csv(filename):
    """Charge un CSV depuis les emplacements du projet.

    Les benchmarks écrivent normalement dans ``benchmarks/results``. Les
    emplacements racine et ``dashboard`` sont conservés comme solutions de
    repli pour les résultats générés par d'anciennes commandes.
    """
    candidate_paths = [os.path.join(directory, filename) for directory in CSV_SEARCH_PATHS]
    path = next((candidate for candidate in candidate_paths if os.path.isfile(candidate)), None)
    if path is None:
        expected_paths = ", ".join(candidate_paths)
        return None, (
            f"Fichier CSV absent. Lancez d'abord les benchmarks. "
            f"Emplacements vérifiés : {expected_paths}"
        )
    try:
        df = pd.read_csv(path)
        if filename == "native_vs_spark.csv":
            expected_columns = ["query_id", "native_avg_ms", "spark_avg_ms"]
            if list(df.columns) != expected_columns:
                return None, (
                    "Format invalide pour native_vs_spark.csv : "
                    f"colonnes attendues {expected_columns}, reçues {list(df.columns)}"
                )
            for column in expected_columns[1:]:
                df[column] = pd.to_numeric(df[column], errors="raise")
        return df, None
    except (OSError, pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
        return None, f"Erreur de lecture du CSV ({path}) : {exc}"


# ---------------------------------------------------------------------------
# Navigation (Top Header Tabs)
# ---------------------------------------------------------------------------

tab_vue, tab_usage, tab_abus, tab_engagement, tab_perf = st.tabs(
    [
        "Vue d'ensemble",
        "Usage",
        "Abus et modération",
        "Engagement",
        "Performance",
    ]
)

# ---------------------------------------------------------------------------
# Page : Vue d'ensemble
# ---------------------------------------------------------------------------

with tab_vue:
    st.title("Vue d'ensemble")

    counts = get_counts()
    labels_fr = {
        "users": "Utilisateurs",
        "conversations": "Conversations",
        "messages": "Messages",
        "read_status": "Statuts de lecture",
        "reports": "Signalements",
    }
    cols = st.columns(len(counts))
    for col, (key, count) in zip(cols, counts.items()):
        col.metric(labels_fr.get(key, key), f"{count:,}")

    st.subheader("Messages par jour (30 derniers jours)")
    docs = get_messages_per_day()
    if not docs:
        st.info("Aucun message sur les 30 derniers jours.")
    else:
        df_day = pd.DataFrame(docs).rename(columns={"_id": "date", "total": "Messages"})
        fig = px.bar(
            df_day,
            x="date",
            y="Messages",
            title="Messages par jour (30 derniers jours)",
            labels={"date": "Date", "Messages": "Nombre de messages"},
            color_discrete_sequence=["#4C78A8"],
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig)

# ---------------------------------------------------------------------------
# Page : Usage
# ---------------------------------------------------------------------------

with tab_usage:
    st.title("Usage")

    # A18 — Répartition par type
    st.subheader("Répartition par type de message (A18)")
    docs_type = get_messages_by_type()
    if not docs_type:
        st.info("Aucune donnée disponible.")
    else:
        df_type = pd.DataFrame(docs_type).rename(columns={"_id": "Type", "total": "Nombre"})
        fig_type = px.bar(
            df_type,
            x="Type",
            y="Nombre",
            title="Répartition par type de message",
            labels={"Type": "Type", "Nombre": "Nombre de messages"},
            color_discrete_sequence=["#72B7B2"],
        )
        st.plotly_chart(fig_type)

    # A22 — Messages par heure
    st.subheader("Messages par heure de la journée (A22)")
    docs_hour = get_messages_by_hour()
    if not docs_hour:
        st.info("Aucune donnée disponible.")
    else:
        df_hour = pd.DataFrame(docs_hour).rename(columns={"_id": "Heure", "total": "Nombre"})
        fig_hour = px.bar(
            df_hour,
            x="Heure",
            y="Nombre",
            title="Messages par heure de la journée",
            labels={"Heure": "Heure (UTC)", "Nombre": "Nombre de messages"},
            color_discrete_sequence=["#54A24B"],
        )
        fig_hour.update_xaxes(tickmode="linear", tick0=0, dtick=1)
        st.plotly_chart(fig_hour)

    # A17 — Top 10 utilisateurs actifs
    st.subheader("Top 10 utilisateurs actifs (A17)")
    docs_users = get_top_users(10)
    if not docs_users:
        st.info("Aucune donnée disponible.")
    else:
        df_users = pd.DataFrame(docs_users).rename(
            columns={"_id": "Identifiant utilisateur", "total": "Nombre de messages"}
        )
        df_users["Identifiant utilisateur"] = df_users["Identifiant utilisateur"].astype(str)
        st.dataframe(df_users, hide_index=True)

# ---------------------------------------------------------------------------
# Page : Abus et modération
# ---------------------------------------------------------------------------

with tab_abus:
    st.title("Abus et modération")

    # A24 — Signalements par motif et statut
    st.subheader("Signalements par motif et statut (A24)")
    docs_rep = get_reports_by_reason_status()
    if not docs_rep:
        st.info("Aucun signalement disponible.")
    else:
        rows = [
            {
                "Motif": d["_id"].get("reason", ""),
                "Statut": d["_id"].get("status", ""),
                "Nombre": d["total"],
            }
            for d in docs_rep
        ]
        df_rep = pd.DataFrame(rows)
        fig_rep = px.bar(
            df_rep,
            x="Motif",
            y="Nombre",
            color="Statut",
            barmode="group",
            title="Signalements par motif et statut",
            labels={"Motif": "Motif", "Nombre": "Nombre", "Statut": "Statut"},
        )
        st.plotly_chart(fig_rep)

    # stats_s29 — Top 20 taux de signalement
    st.subheader("Top 20 taux de signalement (stats_s29)")
    docs_s29, err_s29 = get_stats_collection("stats_s29", sort_field="report_rate", ascending=False, limit=20)
    if err_s29:
        st.info(err_s29)
    else:
        df_s29 = pd.DataFrame(docs_s29)
        if "_id" in df_s29.columns:
            df_s29 = df_s29.drop(columns=["_id"])
        st.dataframe(df_s29, hide_index=True)

    # stats_s28 — Spam senders
    st.subheader("Expéditeurs de spam (stats_s28)")
    docs_s28, err_s28 = get_stats_collection("stats_s28")
    if err_s28:
        st.info(err_s28)
    else:
        df_s28 = pd.DataFrame(docs_s28)
        if "_id" in df_s28.columns:
            df_s28 = df_s28.drop(columns=["_id"])
        st.dataframe(df_s28, hide_index=True)

# ---------------------------------------------------------------------------
# Page : Engagement
# ---------------------------------------------------------------------------

with tab_engagement:
    st.title("Engagement")

    # stats_s30 — Rétention par cohorte
    st.subheader("Rétention par cohorte mensuelle (stats_s30)")
    docs_s30, err_s30 = get_stats_collection("stats_s30")
    if err_s30:
        st.info(err_s30)
    else:
        df_s30 = pd.DataFrame(docs_s30)
        if "_id" in df_s30.columns:
            df_s30 = df_s30.drop(columns=["_id"])

        # Détecter colonnes cohorte et rétention
        cohort_col = next(
            (c for c in df_s30.columns if "cohort" in c.lower() or "cohorte" in c.lower()),
            df_s30.columns[0] if len(df_s30.columns) > 0 else None,
        )
        retain_col = next(
            (c for c in df_s30.columns if "retain" in c.lower() or "rate" in c.lower() or "taux" in c.lower()),
            df_s30.columns[1] if len(df_s30.columns) > 1 else None,
        )

        if cohort_col and retain_col:
            df_s30[cohort_col] = df_s30[cohort_col].astype(str)
            fig_s30 = px.bar(
                df_s30,
                x=cohort_col,
                y=retain_col,
                title="Rétention par cohorte mensuelle",
                labels={cohort_col: "Cohorte", retain_col: "Taux de rétention"},
                color_discrete_sequence=["#E45756"],
            )
            st.plotly_chart(fig_s30)
        else:
            st.dataframe(df_s30, hide_index=True)

    # stats_s26 — Temps de réponse top 20
    st.subheader("Temps de réponse — top 20 (stats_s26)")
    docs_s26, err_s26 = get_stats_collection("stats_s26", sort_field="avg_sec", ascending=True, limit=20)
    if err_s26:
        st.info(err_s26)
    else:
        df_s26 = pd.DataFrame(docs_s26)
        if "_id" in df_s26.columns:
            df_s26 = df_s26.drop(columns=["_id"])
        st.dataframe(df_s26, hide_index=True)

# ---------------------------------------------------------------------------
# Page : Performance
# ---------------------------------------------------------------------------

with tab_perf:
    st.title("Performance")

    # all_queries.csv
    st.subheader("Toutes les requêtes — temps moyen (all_queries.csv)")
    df_all, err_all = load_csv("all_queries.csv")
    if err_all:
        st.info(err_all)
    else:
        fig_all = px.bar(
            df_all,
            x="query_id",
            y="avg_ms",
            color="engine",
            title="Temps moyen par requête",
            labels={"query_id": "Requête", "avg_ms": "Temps moyen (ms)", "engine": "Moteur"},
            barmode="group",
        )
        fig_all.update_xaxes(tickangle=-45)
        st.plotly_chart(fig_all)

    # native_vs_spark.csv
    st.subheader("Comparaison natif / Spark (native_vs_spark.csv)")
    df_nvs, err_nvs = load_csv("native_vs_spark.csv")
    if err_nvs:
        st.info(err_nvs)
    else:
        df_nvs_melted = df_nvs[["query_id", "native_avg_ms", "spark_avg_ms"]].melt(
            id_vars="query_id",
            value_vars=["native_avg_ms", "spark_avg_ms"],
            var_name="Moteur",
            value_name="Temps moyen (ms)",
        )
        df_nvs_melted["Moteur"] = df_nvs_melted["Moteur"].map(
            {"native_avg_ms": "MongoDB natif", "spark_avg_ms": "Spark"}
        )
        fig_nvs = px.bar(
            df_nvs_melted,
            x="query_id",
            y="Temps moyen (ms)",
            color="Moteur",
            barmode="group",
            title="Natif vs Spark — A16, A17, A18",
            labels={"query_id": "Requête"},
        )
        st.plotly_chart(fig_nvs)

    # index_test.csv
    st.subheader("Test des index — T4 et T6 (index_test.csv)")
    df_idx, err_idx = load_csv("index_test.csv")
    if err_idx:
        st.info(err_idx)
    else:
        st.dataframe(df_idx, hide_index=True)

        fig_idx = px.bar(
            df_idx,
            x="query_id",
            y="avg_ms",
            color="mode",
            barmode="group",
            title="Avec index vs sans index",
            labels={"query_id": "Requête", "avg_ms": "Temps moyen (ms)", "mode": "Mode"},
        )
        st.plotly_chart(fig_idx)

    # consistency_test.csv
    st.subheader("Test de cohérence — write concern et read concern (consistency_test.csv)")
    df_cons, err_cons = load_csv("consistency_test.csv")
    if err_cons:
        st.info(err_cons)
    else:
        st.caption(
            "Note : les résultats devront être recalculés quand mongo3 (machine B) sera de nouveau en ligne."
        )
        st.dataframe(df_cons, hide_index=True)

        fig_cons = px.bar(
            df_cons,
            x="test_id",
            y="avg_ms",
            color="setting",
            barmode="group",
            title="Cohérence — temps moyen par paramètre",
            labels={
                "test_id": "Test",
                "avg_ms": "Temps moyen (ms)",
                "setting": "Paramètre",
            },
        )
        st.plotly_chart(fig_cons)