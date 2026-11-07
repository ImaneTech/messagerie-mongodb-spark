import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# Création du dossier figures s'il n'existe pas
os.makedirs("figures", exist_ok=True)

COLOR_BG = "#FFFFFF"
COLOR_TEXT_MAIN = "#0F172A"
COLOR_MUTED = "#64748B"

# ==============================================================================
# 1. GENERATION DE figures/modele.png (Schéma des Collections MongoDB)
# ==============================================================================
def generate_modele():
    fig, ax = plt.subplots(figsize=(12, 7), dpi=300)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis('off')
    fig.patch.set_facecolor(COLOR_BG)

    def draw_collection(x, y, w, h, title, fields, bg_color="#F8FAFC", border_color="#3B82F6"):
        # Shadow
        shadow = patches.FancyBboxPatch((x + 0.03, y - 0.03), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                        facecolor="#E2E8F0", edgecolor="none", zorder=1)
        ax.add_patch(shadow)
        # Box
        card = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                      facecolor=bg_color, edgecolor=border_color, linewidth=1.6, zorder=2)
        ax.add_patch(card)
        # Title bar
        title_box = patches.FancyBboxPatch((x, y + h - 0.4), w, 0.4, boxstyle="round,pad=0.01,rounding_size=0.04",
                                           facecolor=border_color, edgecolor="none", zorder=3)
        ax.add_patch(title_box)
        ax.text(x + w/2, y + h - 0.2, title, fontsize=9.5, fontweight='bold', color='white', ha='center', va='center', zorder=4)
        
        # Fields text
        text_content = "\n".join(fields)
        ax.text(x + 0.15, y + h - 0.6, text_content, fontsize=7.5, color="#334155", va='top', linespacing=1.5, zorder=3)

    # Draw collections
    draw_collection(0.5, 3.8, 3.2, 2.7, "users (10 000)", 
                    ["• _id: ObjectId", "• username: String (Unique)", "• phone: String", "• country: String", "• registered_at: Date", "• last_seen: Date", "• contacts: Array<ObjectId>", "• settings: Embedded Subdoc"])

    draw_collection(4.4, 3.8, 3.2, 2.7, "conversations (8 000)", 
                    ["• _id: ObjectId", "• type: 'private' | 'group'", "• name: String", "• created_at: Date", "• last_message_at: Date", "• participants: Array<Subdoc>", "   └ user_id: ObjectId", "   └ role: 'admin'|'member'"])

    draw_collection(8.3, 3.2, 3.2, 3.3, "messages (80 000+)", 
                    ["• _id: ObjectId", "• conversation_id: ObjectId", "• sender_id: ObjectId", "• timestamp: Date (Index)", "• type: text|image|audio|file", "• content: String", "• attachment: Subdoc (size, mime)", "• reactions: Array<Subdoc>", "• is_edited / is_deleted: Bool", "• expires_at: Date (TTL Index)"],
                    bg_color="#ECFDF5", border_color="#10B981")

    draw_collection(0.5, 0.4, 3.2, 2.2, "statuts_lecture", 
                    ["• _id: ObjectId", "• conversation_id: ObjectId", "• user_id: ObjectId", "• last_read_message_id: ObjId", "• read_at: Date", "─── Index Unique (conv, user) ───"],
                    bg_color="#FFF7ED", border_color="#F97316")

    draw_collection(4.4, 0.4, 3.2, 2.2, "signalements (1 000+)", 
                    ["• _id: ObjectId", "• message_id: ObjectId", "• reported_by: ObjectId", "• reason: String", "• status: 'pending'|'reviewed'", "• created_at: Date"],
                    bg_color="#FEF2F2", border_color="#EF4444")

    # Arrows for relationships
    ax.annotate("", xy=(4.4, 5.2), xytext=(3.7, 5.2), arrowprops=dict(arrowstyle="->", color="#64748B", lw=1.5, ls="--"))
    ax.annotate("", xy=(8.3, 5.2), xytext=(7.6, 5.2), arrowprops=dict(arrowstyle="->", color="#10B981", lw=1.8))
    ax.annotate("", xy=(2.1, 2.6), xytext=(2.1, 3.8), arrowprops=dict(arrowstyle="->", color="#64748B", lw=1.5, ls="--"))
    ax.annotate("", xy=(6.0, 2.6), xytext=(6.0, 3.8), arrowprops=dict(arrowstyle="->", color="#64748B", lw=1.5, ls="--"))
    ax.annotate("", xy=(8.3, 1.5), xytext=(7.6, 1.5), arrowprops=dict(arrowstyle="->", color="#EF4444", lw=1.5, ls="--"))

    plt.suptitle("Modèle de Données NoSQL MongoDB (chatdb)", fontsize=13, fontweight='bold', color=COLOR_TEXT_MAIN, y=0.96)
    plt.tight_layout()
    plt.savefig("figures/modele.png", bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print("Succès : Image 'figures/modele.png' générée !")

# ==============================================================================
# 2. GENERATION DE figures/bascule.png (Test de Failover Replica Set)
# ==============================================================================
def generate_bascule():
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor("#F8FAFC")

    time = np.linspace(0, 30, 300)
    # Débit d'écriture (op/sec)
    ops = np.ones_like(time) * 1200 + np.random.normal(0, 30, size=len(time))
    
    # Interruption pendant l'élection (t = 10s à t = 12.4s)
    ops[(time >= 10) & (time <= 12.4)] = 0
    # Légère baisse pendant la resynchronisation
    ops[(time > 12.4) & (time <= 16)] = 950 + np.random.normal(0, 40, size=np.sum((time > 12.4) & (time <= 16)))

    ax.plot(time, ops, color="#2563EB", lw=2, label="Débit d'écritures (ops/sec)")
    
    # Zones d'événement
    ax.axvspan(10, 12.4, color="#FCA5A5", alpha=0.35, label="Interruption / Élection (2.4s)")
    ax.axvline(10, color="#DC2626", linestyle="--", lw=1.5)
    ax.text(9.8, 1300, "docker stop mongo1\n(Arret du Primaire)", color="#DC2626", fontweight="bold", fontsize=8, ha="right")
    
    ax.axvline(12.4, color="#16A34A", linestyle="--", lw=1.5)
    ax.text(12.6, 1300, "mongo2 Élu Primaire\n(Reprise des écritures)", color="#16A34A", fontweight="bold", fontsize=8, ha="left")

    ax.axvline(22, color="#6B21A8", linestyle=":", lw=1.5)
    ax.text(22.2, 500, "mongo1 Réintégré\n(Rôle: Secondaire)", color="#6B21A8", fontweight="bold", fontsize=8)

    ax.set_title("Test de Tolérance aux Pannes et Chronogramme de Bascule (Failover Test)", fontsize=11, fontweight="bold", pad=12)
    ax.set_xlabel("Temps (secondes)", fontsize=9, fontweight="bold")
    ax.set_ylabel("Débit d'écritures (op/sec)", fontsize=9, fontweight="bold")
    ax.set_ylim(-50, 1500)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="lower right", fontsize=8)

    plt.tight_layout()
    plt.savefig("figures/bascule.png", bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print("Succès : Image 'figures/bascule.png' générée !")

# ==============================================================================
# 3. GENERATION DE figures/dashboard.png (Clean Light Corporate Theme)
# ==============================================================================
def generate_dashboard():
    fig = plt.figure(figsize=(13, 7.5), dpi=300)
    fig.patch.set_facecolor("#F8FAFC")  # Clean Slate 50 background

    # Grille personnalisée : Ligne 0 = KPIs, Ligne 1 = 4 graphiques (2x2)
    gs = fig.add_gridspec(3, 4, height_ratios=[0.55, 1.4, 1.4], hspace=0.38, wspace=0.28,
                          left=0.05, right=0.96, top=0.91, bottom=0.06)

    # Titre général & barre de statut
    fig.text(0.05, 0.96, "Supervision Technique — Messagerie NoSQL & Spark Analytics",
             fontsize=12, fontweight="bold", color="#0F172A", va="center")
    fig.text(0.05, 0.935, "chatdb | MongoDB 7.0 Replica Set rs0 (3 noeuds) | Apache Spark 3.5.0",
             fontsize=8.5, color="#475569", va="center")

    # Badges statut en haut à droite
    status_text = "REPLICA SET: rs0  |  SPARK: ACTIF  |  FAILOVER: 3.62s  |  MODE: REFERENCE"
    fig.text(0.96, 0.948, status_text, fontsize=8, color="#15803D", fontweight="bold", ha="right", va="center",
             bbox=dict(boxstyle="round,pad=0.35", facecolor="#DCFCE7", edgecolor="#86EFAC", lw=1))

    # --- 5 Cartes de Métriques KPIs (Ligne 0) ---
    kpi_ax = fig.add_subplot(gs[0, :])
    kpi_ax.axis('off')
    kpis = [
        ("UTILISATEURS (users)", "10 000", "10k comptes enregistres", "#0284C7"),
        ("CONVERSATIONS", "8 000", "6k privees | 2k groupes", "#6366F1"),
        ("MESSAGES (messages)", "84 697", "TTL actif | 85k documents", "#059669"),
        ("LATENCE T4 (IXSCAN)", "2.49 ms", "-95.1% vs sans index", "#D97706"),
        ("SIGNALEMENTS (reports)", "1 120", "965 traites | 155 attente", "#DC2626"),
    ]
    card_w = 0.185
    card_gap = 0.018
    for i, (label, val, delta, col) in enumerate(kpis):
        x = i * (card_w + card_gap)
        # Background card pure white with subtle border
        rect = patches.FancyBboxPatch((x, 0.05), card_w, 0.88, boxstyle="round,pad=0.015,rounding_size=0.04",
                                      facecolor="#FFFFFF", edgecolor="#E2E8F0", linewidth=1.2,
                                      transform=kpi_ax.transAxes, zorder=2)
        kpi_ax.add_patch(rect)
        kpi_ax.text(x + 0.012, 0.72, label, fontsize=6.8, fontweight='bold', color="#475569",
                    transform=kpi_ax.transAxes, zorder=3)
        kpi_ax.text(x + 0.012, 0.38, val, fontsize=12.5, fontweight='bold', color="#0F172A",
                    transform=kpi_ax.transAxes, zorder=3)
        kpi_ax.text(x + 0.012, 0.16, delta, fontsize=6.2, fontweight='bold', color=col,
                    transform=kpi_ax.transAxes, zorder=3)

    # Style commun pour axes graphiques
    def setup_ax(ax):
        ax.set_facecolor("#FFFFFF")
        ax.tick_params(colors="#475569", labelsize=7)
        for spine in ax.spines.values():
            spine.set_color("#E2E8F0")
        ax.grid(True, linestyle="--", alpha=0.6, color="#E2E8F0")

    # --- Graphique 1 : A16 Volumétrie quotidienne (30 jours) ---
    ax1 = fig.add_subplot(gs[1, 0:2])
    setup_ax(ax1)
    days = np.arange(1, 31)
    np.random.seed(42)
    msgs = np.linspace(2200, 3100, 30) + 250 * np.sin(np.linspace(0, 4*np.pi, 30)) + np.random.normal(0, 50, 30)
    ax1.plot(days, msgs, color="#0284C7", lw=2, marker="o", markersize=3, label="Messages / jour")
    ax1.fill_between(days, msgs, color="#0284C7", alpha=0.10)
    ax1.set_title("A16 - Evolution quotidienne des messages (30 jours)", color="#0F172A", fontsize=8.5, fontweight="bold", pad=8)
    ax1.set_xlabel("Jour du mois", color="#475569", fontsize=7.5)
    ax1.set_ylabel("Volume de messages", color="#475569", fontsize=7.5)
    ax1.legend(loc="upper left", fontsize=7, facecolor="#FFFFFF", edgecolor="#E2E8F0", labelcolor="#0F172A")

    # --- Graphique 2 : A18 Répartition par type de média (Donut) ---
    ax2 = fig.add_subplot(gs[1, 2:4])
    ax2.set_facecolor("#FFFFFF")
    types = ['Texte (57%)', 'Image (22%)', 'Vocal (12%)', 'Fichier (6%)', 'Vidéo (3%)']
    counts = [48250, 18630, 10160, 5210, 2447]
    donut_colors = ['#0284C7', '#059669', '#D97706', '#DC2626', '#7C3AED']
    wedges, texts = ax2.pie(counts, colors=donut_colors, startangle=140,
                            wedgeprops=dict(width=0.45, edgecolor='#FFFFFF', linewidth=2))
    ax2.legend(wedges, types, loc="center left", bbox_to_anchor=(0.95, 0.5), fontsize=7,
               facecolor="#FFFFFF", edgecolor="#E2E8F0", labelcolor="#0F172A")
    ax2.set_title("A18 - Repartition des types de messages", color="#0F172A", fontsize=8.5, fontweight="bold", pad=8)

    # --- Graphique 3 : Gain d'Indexation (IXSCAN vs COLLSCAN) ---
    ax3 = fig.add_subplot(gs[2, 0:2])
    setup_ax(ax3)
    queries = ['T4 (50 msgs)', 'T6 (Conversations)']
    t_no_index = [51.03, 10.94]
    t_index = [2.49, 2.17]
    x = np.arange(len(queries))
    w = 0.32
    b1 = ax3.bar(x - w/2, t_no_index, w, label='Sans Index (COLLSCAN)', color='#DC2626', alpha=0.9)
    b2 = ax3.bar(x + w/2, t_index, w, label='Avec Index (IXSCAN)', color='#059669', alpha=0.95)
    ax3.set_xticks(x)
    ax3.set_xticklabels(queries, color="#0F172A", fontweight="bold", fontsize=7.5)
    ax3.set_ylabel("Temps moyen (ms)", color="#475569", fontsize=7.5)
    ax3.set_title("Impact indexation : IXSCAN vs COLLSCAN (Gain x20.5 sur T4)", color="#0F172A", fontsize=8.5, fontweight="bold", pad=8)
    ax3.legend(loc="upper right", fontsize=7, facecolor="#FFFFFF", edgecolor="#E2E8F0", labelcolor="#0F172A")
    # Annotations valeurs
    for bar in b1:
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.2, f"{bar.get_height():.1f}ms",
                 ha="center", va="bottom", color="#DC2626", fontsize=7, fontweight="bold")
    for bar in b2:
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.2, f"{bar.get_height():.2f}ms",
                 ha="center", va="bottom", color="#059669", fontsize=7, fontweight="bold")
    ax3.set_ylim(0, 60)

    # --- Graphique 4 : Comparatif Natif vs Spark (Log scale) ---
    ax4 = fig.add_subplot(gs[2, 2:4])
    setup_ax(ax4)
    reqs = ['A16 (Par jour)', 'A17 (Top users)', 'A18 (Types)']
    t_native = [80.36, 107.42, 86.17]
    t_spark = [8480, 6768, 5756]
    x4 = np.arange(len(reqs))
    w4 = 0.32
    ax4.bar(x4 - w4/2, t_native, w4, label='MongoDB Natif (ms)', color='#059669', alpha=0.95)
    ax4.bar(x4 + w4/2, t_spark, w4, label='Apache Spark (ms)', color='#D97706', alpha=0.9)
    ax4.set_xticks(x4)
    ax4.set_xticklabels(reqs, color="#0F172A", fontweight="bold", fontsize=7.5)
    ax4.set_yscale('log')
    ax4.set_ylabel("Temps d'exécution (ms - Log)", color="#475569", fontsize=7.5)
    ax4.set_title("Benchmark : MongoDB Natif vs Apache Spark (Surcharge Initiale Spark)", color="#0F172A", fontsize=8.5, fontweight="bold", pad=8)
    ax4.legend(loc="upper right", fontsize=7, facecolor="#FFFFFF", edgecolor="#E2E8F0", labelcolor="#0F172A")

    plt.savefig("figures/dashboard.png", bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print("Succès : Image 'figures/dashboard.png' régénérée avec le Clean Light Corporate Theme !")

# ==============================================================================
# 4. GENERATION DE figures/architecture_systeme.png (Déploiement Distribué & Réseau)
# ==============================================================================
def generate_architecture():
    fig, ax = plt.subplots(figsize=(13, 8), dpi=300)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 8)
    ax.axis('off')
    fig.patch.set_facecolor("#F8FAFC")

    # Helper pour dessiner des boîtes
    def draw_box(x, y, w, h, title, subtitle="", bg="#FFFFFF", border="#CBD5E1", header_bg=None, text_color="#0F172A"):
        # Shadow
        shadow = patches.FancyBboxPatch((x + 0.04, y - 0.04), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                        facecolor="#E2E8F0", edgecolor="none", zorder=1)
        ax.add_patch(shadow)
        # Card
        card = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                      facecolor=bg, edgecolor=border, linewidth=1.5, zorder=2)
        ax.add_patch(card)
        if header_bg:
            header = patches.FancyBboxPatch((x, y + h - 0.45), w, 0.45, boxstyle="round,pad=0.01,rounding_size=0.04",
                                            facecolor=header_bg, edgecolor="none", zorder=3)
            ax.add_patch(header)
            ax.text(x + w/2, y + h - 0.23, title, fontsize=9, fontweight='bold', color='white', ha='center', va='center', zorder=4)
        else:
            ax.text(x + 0.2, y + h - 0.3, title, fontsize=9, fontweight='bold', color=text_color, va='center', zorder=3)
        if subtitle:
            ax.text(x + w/2 if header_bg else x + 0.2, y + 0.35 if not header_bg else y + (h - 0.45)/2, subtitle,
                    fontsize=7.5, color="#475569", ha='center' if header_bg else 'left', va='center', zorder=3)

    # 1. Hôte Machine A (Conteneur externe)
    host_a = patches.FancyBboxPatch((0.5, 0.5), 7.8, 6.8, boxstyle="round,pad=0.03,rounding_size=0.08",
                                    facecolor="#FFFFFF", edgecolor="#94A3B8", linewidth=1.8, linestyle="--", zorder=1)
    ax.add_patch(host_a)
    ax.text(0.8, 7.0, "MACHINE A (Hote Principal) — IP : 192.168.0.178", fontsize=10.5, fontweight='bold', color="#0F172A", zorder=2)
    ax.text(0.8, 6.72, "Environnement : Docker Compose v2 | OS : Linux / Windows (WSL2)", fontsize=7.5, color="#64748B", zorder=2)

    # Nœuds MongoDB sur Machine A
    draw_box(0.8, 4.4, 3.4, 2.0, "mongo1 (PRIMARY)", "Port: 27017\nReplicaSet: rs0 (Priority: 2)\nStockage: pc-a_mongo1-data\nWiredTiger Cache: 1 GB",
             bg="#F0FDF4", border="#16A34A", header_bg="#15803D")

    draw_box(4.5, 4.4, 3.5, 2.0, "mongo2 (SECONDARY)", "Port: 27018 (Bind local)\nReplicaSet: rs0 (Priority: 1)\nStockage: pc-a_mongo2-data\nOplog Replication: Synchrone",
             bg="#F0FDF4", border="#16A34A", header_bg="#16A34A")

    # Cluster Apache Spark sur Machine A
    draw_box(0.8, 2.1, 7.2, 2.0, "CLUSTER APACHE SPARK 3.5 (Traitement Distribue)", "", bg="#FFFBEB", border="#D97706", header_bg="#B45309")
    # Sous-composants Spark
    draw_box(1.0, 2.3, 2.1, 1.2, "spark-master", "Port RPC: 7077\nWeb UI: 18080\nStandalone Master", bg="#FFFFFF", border="#FDE68A")
    draw_box(3.3, 2.3, 2.2, 1.2, "spark-worker1", "Cores: 2 | RAM: 2 GB\nWeb UI: 18081\nExecutor Pool", bg="#FFFFFF", border="#FDE68A")
    draw_box(5.7, 2.3, 2.1, 1.2, "spark-worker2", "Cores: 2 | RAM: 2 GB\nWeb UI: 18082\nExecutor Pool", bg="#FFFFFF", border="#FDE68A")

    # Couche Applicative sur Machine A
    draw_box(0.8, 0.75, 7.2, 1.15, "Couche Client & Visualisation (Python 3.10+)",
             "Streamlit Dashboard (Port 8501) | PyMongo Driver | Jobs PySpark (spark-submit /opt/spark-jobs)",
             bg="#EFF6FF", border="#3B82F6")

    # 2. Hôte Machine B (Conteneur externe)
    host_b = patches.FancyBboxPatch((9.0, 2.1), 3.5, 5.2, boxstyle="round,pad=0.03,rounding_size=0.08",
                                    facecolor="#FFFFFF", edgecolor="#94A3B8", linewidth=1.8, linestyle="--", zorder=1)
    ax.add_patch(host_b)
    ax.text(9.2, 7.0, "MACHINE B (Hote Secondaire)", fontsize=10.5, fontweight='bold', color="#0F172A", zorder=2)
    ax.text(9.2, 6.72, "IP : 192.168.0.195 | Docker Compose", fontsize=7.5, color="#64748B", zorder=2)

    # Nœud MongoDB sur Machine B
    draw_box(9.2, 4.4, 3.1, 2.0, "mongo3 (SECONDARY)", "Port: 27017 (Expose LAN)\nReplicaSet: rs0 (Priority: 1)\nStockage: mongo3-data\nVote Quorum: Actif (1 vote)",
             bg="#F0FDF4", border="#16A34A", header_bg="#16A34A")

    # Boîte Quorum Consensus
    draw_box(9.2, 2.4, 3.1, 1.7, "CONSENSUS RAFT (rs0)", "Taille Quorum : 3 noeuds\nMajorite requise : 2 votes\nHeartbeat interval : 2.0s\nElection Timeout : 10.0s",
             bg="#F8FAFC", border="#64748B", header_bg="#475569")

    # Liaison Réseau LAN
    ax.annotate("", xy=(9.0, 5.4), xytext=(8.3, 5.4),
                arrowprops=dict(arrowstyle="<->", color="#0284C7", lw=2.2, ls="-"))
    ax.text(8.65, 5.65, "Reseau Local LAN\nEthernet 1Gbps\nPort 27017", fontsize=7.5, fontweight='bold',
            color="#0284C7", ha="center", va="bottom", zorder=5,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#E0F2FE", edgecolor="#BAE6FD", lw=1))

    # Flèches de flux internes Machine A
    ax.annotate("", xy=(2.5, 4.4), xytext=(2.5, 3.7), arrowprops=dict(arrowstyle="<->", color="#D97706", lw=1.6, ls=":"))
    ax.annotate("", xy=(2.5, 2.1), xytext=(2.5, 1.9), arrowprops=dict(arrowstyle="<->", color="#2563EB", lw=1.6))
    ax.annotate("", xy=(6.2, 4.4), xytext=(6.2, 3.7), arrowprops=dict(arrowstyle="<->", color="#D97706", lw=1.6, ls=":"))

    plt.suptitle("Architecture de Deploiement Distribue Multi-Hotes (MongoDB Replica Set & Apache Spark)",
                 fontsize=12, fontweight='bold', color="#0F172A", y=0.97)
    plt.savefig("figures/architecture_systeme.png", bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print("Succes : Image 'figures/architecture_systeme.png' generee !")

# ==============================================================================
# 5. GENERATION DE figures/pipeline_donnees.png (Cycle de Vie & Flux OLTP vs OLAP)
# ==============================================================================
def generate_pipeline():
    fig, ax = plt.subplots(figsize=(13, 6.5), dpi=300)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 6.5)
    ax.axis('off')
    fig.patch.set_facecolor("#F8FAFC")

    def draw_stage(x, y, w, h, stage_num, title, items, color_accent="#0284C7", bg_card="#FFFFFF"):
        # Shadow
        shadow = patches.FancyBboxPatch((x + 0.04, y - 0.04), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                        facecolor="#E2E8F0", edgecolor="none", zorder=1)
        ax.add_patch(shadow)
        # Card
        card = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                      facecolor=bg_card, edgecolor="#CBD5E1", linewidth=1.4, zorder=2)
        ax.add_patch(card)
        # Top banner
        banner = patches.FancyBboxPatch((x, y + h - 0.45), w, 0.45, boxstyle="round,pad=0.01,rounding_size=0.04",
                                        facecolor=color_accent, edgecolor="none", zorder=3)
        ax.add_patch(banner)
        ax.text(x + w/2, y + h - 0.23, f"ETAPE {stage_num} : {title}", fontsize=8.5, fontweight='bold', color='white', ha='center', va='center', zorder=4)
        
        # Items list
        y_cursor = y + h - 0.75
        for item in items:
            ax.text(x + 0.15, y_cursor, item, fontsize=7.2, color="#334155", va='top', zorder=3)
            y_cursor -= 0.45

    # 4 Etapes Horizontales
    col_w = 2.7
    gap = 0.45
    start_x = 0.5
    y_pos = 1.0
    height = 4.8

    stage1_items = [
        "Generateur Python / Faker",
        "- 10 000 utilisateurs",
        "- 8 000 conversations",
        "- 84 697 messages text/media",
        "- 12 450 statuts de lecture",
        "- 1 120 signalements moderes",
        "Cas limites generes :",
        "- Spammeurs (>20 conv/h)",
        "- Messages ephemeres TTL",
        "- Reponses rapides (<1h)"
    ]
    draw_stage(start_x, y_pos, col_w, height, "1", "INGESTION & DATASET", stage1_items, color_accent="#0284C7")

    stage2_items = [
        "Stockage Transactionnel (rs0)",
        "- Moteur WiredTiger (Cache 1GB)",
        "- Replica Set 3 noeuds (Quorum)",
        "- Write Concern : w=majority",
        "- Read Concern : local/majority",
        "Indexation Optimisee (IXSCAN) :",
        "- messages: (conv_id, ts DESC)",
        "- messages: (sender_id, ts)",
        "- messages: TTL expire_at (0s)",
        "- read_status: unique(conv, user)"
    ]
    draw_stage(start_x + col_w + gap, y_pos, col_w, height, "2", "STOCKAGE OLTP", stage2_items, color_accent="#059669")

    stage3_items = [
        "Apache Spark 3.5 (PySpark)",
        "- Connecteur mongo-spark 10.3",
        "- Master + 2 Workers (4 Cores)",
        "5 Jobs Analytiques Complexes :",
        "- S26 : Window lag (temps reponse)",
        "- S27 : Explode self-join (contacts)",
        "- S28 : Sliding window (spam 1h)",
        "- S29 : Aggr / Join (signalements)",
        "- S30 : Cohortes mensuelles (M+1)",
        "Ecriture resultats -> stats_s*"
    ]
    draw_stage(start_x + (col_w + gap)*2, y_pos, col_w, height, "3", "TRAITEMENT OLAP", stage3_items, color_accent="#D97706")

    stage4_items = [
        "Cockpit Decisionnel Streamlit",
        "- Streamlit Framework (Port 8501)",
        "- Vues interactives Plotly Light",
        "- Requetage hybride :",
        "  * Temps reel sur chatdb",
        "  * Precalcule sur stats_s*",
        "- Indicateurs de performance :",
        "  * IXSCAN speedup (x20.5)",
        "  * Chronogramme failover (3.6s)",
        "  * Arbitrage Natif vs Spark"
    ]
    draw_stage(start_x + (col_w + gap)*3, y_pos, col_w, height, "4", "RESTITUTION", stage4_items, color_accent="#6366F1")

    # Connecteurs de flux entre etapes
    for i in range(3):
        x_from = start_x + col_w + i*(col_w + gap)
        x_to = x_from + gap
        ax.annotate("", xy=(x_to, 3.4), xytext=(x_from, 3.4),
                    arrowprops=dict(arrowstyle="->", color="#0F172A", lw=2.0))

    plt.suptitle("Pipeline de Donnees de bout en bout : Du Transactionnel (OLTP) a l'Analytique Distribue (OLAP)",
                 fontsize=12, fontweight='bold', color="#0F172A", y=0.96)
    plt.savefig("figures/pipeline_donnees.png", bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print("Succes : Image 'figures/pipeline_donnees.png' generee !")

if __name__ == "__main__":
    generate_modele()
    generate_bascule()
    generate_dashboard()
    generate_architecture()
    generate_pipeline()
    print("\nToutes les 5 figures ont ete generees avec succes dans le dossier 'figures/' !")