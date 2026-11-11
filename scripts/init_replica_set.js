/**
 * scripts/init_replica_set.js
 * Initialisation idempotente du Replica Set rs0 pour MongoDB 7.0
 * Conforme au guide du professeur : 3 membres, mongo1 en Primaire (priority: 2)
 *
 * Utilisation :
 *   docker exec -i mongo1 mongosh --quiet < scripts/init_replica_set.js
 * ou via python/powershell :
 *   python scripts/init_replica_set.py
 */

const config = {
  _id: "rs0",
  members: [
    {
      _id: 0,
      host: "192.168.0.100:27017",
      priority: 2 // Priorité supérieure pour forcer mongo1 en Primaire
    },
    {
      _id: 1,
      host: "192.168.0.101:27017",
      priority: 1
    },
    {
      _id: 2,
      host: "192.168.0.102:27017",
      priority: 1
    }
  ]
};

try {
  const status = rs.status();
  if (status.ok === 1) {
    print("[INFO] Replica Set rs0 déjà initialisé. Reconfiguration si nécessaire...");
    rs.reconfig(config, { force: false });
    print("[OK] Reconfiguration appliquée avec succès.");
  }
} catch (e) {
  print("[INFO] Initialisation initiale du Replica Set rs0...");
  const res = rs.initiate(config);
  if (res.ok === 1) {
    print("[OK] Replica Set rs0 initialisé avec succès.");
  } else {
    print("[ERREUR] Échec de rs.initiate : " + JSON.stringify(res));
  }
}

// Attente de l'élection d'un primaire
let attempts = 0;
while (attempts < 30) {
  try {
    const hello = db.hello();
    if (hello.isWritablePrimary) {
      print("[OK] Primaire actif : " + hello.primary);
      break;
    }
  } catch (err) {}
  sleep(1000);
  attempts++;
}

