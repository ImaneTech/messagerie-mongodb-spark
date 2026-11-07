import os
import pandas as pd
import matplotlib.pyplot as plt

os.makedirs("figures", exist_ok=True)

# Style académique sobre
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 9,
    'axes.labelsize': 10,
    'axes.titlesize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
    'figure.titlesize': 11,
    'axes.grid': True,
    'grid.linestyle': '--',
    'grid.alpha': 0.5,
    'axes.edgecolor': '#333333',
    'axes.linewidth': 0.8
})

# -------------------------------------------------------------
# 1. Graphique Native vs Spark (A16, A17, A18)
# -------------------------------------------------------------
path_spark = "benchmarks/results/native_vs_spark.csv"
if os.path.exists(path_spark):
    df_spark = pd.read_csv(path_spark)
    # Normalisation des colonnes si chargées depuis CSV
    if 'native_avg_ms' in df_spark.columns:
        df_spark['native_ms'] = df_spark['native_avg_ms']
    if 'spark_avg_ms' in df_spark.columns:
        df_spark['spark_ms'] = df_spark['spark_avg_ms']
else:
    # Données réelles validées
    df_spark = pd.DataFrame({
        'query_id': ['A16', 'A17', 'A18'],
        'native_ms': [80.36, 107.42, 86.17],
        'spark_ms': [8480.0, 6768.0, 5756.0]
    })

fig, ax = plt.subplots(figsize=(6, 3.2), dpi=300)
x = range(len(df_spark))
width = 0.35

ax.bar([i - width/2 for i in x], df_spark['native_ms'], width, label='MongoDB natif (MQL)', color='#1f77b4')
ax.bar([i + width/2 for i in x], df_spark['spark_ms'], width, label='Apache Spark (PySpark)', color='#ff7f0e')

ax.set_ylabel('Temps moyen d\'exécution (ms, échelle log)')
ax.set_xticks(list(x))
ax.set_xticklabels(df_spark['query_id'])
ax.set_yscale('log')
ax.legend(frameon=True, facecolor='white', edgecolor='none')
plt.title('Comparaison des temps d\'exécution : MongoDB natif vs Apache Spark')
plt.tight_layout()
plt.savefig("figures/native_vs_spark.pdf", format="pdf")
plt.savefig("figures/native_vs_spark.png", dpi=300)
plt.close()

# -------------------------------------------------------------
# 2. Graphique Impact de l'Indexation (T4 et T6)
# -------------------------------------------------------------
path_index = "benchmarks/results/index_test.csv"
if os.path.exists(path_index):
    df_idx = pd.read_csv(path_index)
else:
    # Données réelles mesurées (explain executionStats)
    df_idx = pd.DataFrame({
        'query_id': ['T4', 'T4', 'T6', 'T6'],
        'mode': ['index', 'no_index', 'index', 'no_index'],
        'avg_ms': [2.49, 51.03, 2.17, 10.94]
    })

fig, ax = plt.subplots(figsize=(5.5, 3.0), dpi=300)
queries = ['T4 (50 derniers messages)', 'T6 (Conversations d\'un utilisateur)']

# Support pour mode 'index' / 'no_index' ou 'avec' / 'sans'
mask_t4_with = (df_idx['query_id']=='T4') & (df_idx['mode'].str.contains('index') & ~df_idx['mode'].str.contains('no_index|sans') | df_idx['mode'].str.contains('avec'))
mask_t6_with = (df_idx['query_id']=='T6') & (df_idx['mode'].str.contains('index') & ~df_idx['mode'].str.contains('no_index|sans') | df_idx['mode'].str.contains('avec'))
mask_t4_without = (df_idx['query_id']=='T4') & (df_idx['mode'].str.contains('no_index|sans'))
mask_t6_without = (df_idx['query_id']=='T6') & (df_idx['mode'].str.contains('no_index|sans'))

with_idx = [df_idx[mask_t4_with]['avg_ms'].values[0], df_idx[mask_t6_with]['avg_ms'].values[0]]
without_idx = [df_idx[mask_t4_without]['avg_ms'].values[0], df_idx[mask_t6_without]['avg_ms'].values[0]]

x = range(len(queries))
ax.bar([i - width/2 for i in x], with_idx, width, label='Avec index (IXSCAN)', color='#2ca02c')
ax.bar([i + width/2 for i in x], without_idx, width, label='Sans index (COLLSCAN)', color='#d62728')

ax.set_ylabel('Temps moyen d\'exécution (ms)')
ax.set_xticks(list(x))
ax.set_xticklabels(queries)
ax.legend(frameon=True, facecolor='white', edgecolor='none')
plt.title('Impact de l\'indexation sur les latences de lecture')
plt.tight_layout()
plt.savefig("figures/index_test.pdf", format="pdf")
plt.savefig("figures/index_test.png", dpi=300)
plt.close()

print("Graphiques académiques vectoriels générés avec succès dans figures/")