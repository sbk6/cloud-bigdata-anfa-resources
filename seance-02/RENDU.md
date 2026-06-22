# Rendu Séance 2

**Nom et prénom :** BIKOZI Balakibawi Sylvain  
**Identifiant GitHub :** sbk6

---

## Résumé de la séance

Cette séance avait pour objectif de maîtriser Docker au-delà du simple `docker run` : écrire un `Dockerfile` pour conteneuriser une application PySpark, comprendre le mécanisme de cache des couches, puis orchestrer une stack multi-services (MinIO + Jupyter + application d'analyse) avec Docker Compose.

---

## Étapes principales

1. **Script PySpark** — Écriture de `analyse_referentiel.py` qui charge les 4 CSV du référentiel Anfa en mode local (`local[*]`) et calcule des statistiques agrégées (comptages, top 3, tarif moyen par type).
2. **Dockerfile** — Construction de l'image `anfa-analyse:v1` basée sur `python:3.11-slim-bookworm` avec installation de `openjdk-17-jre-headless` (requis par Spark). Un lien symbolique `/usr/local/java` rend `JAVA_HOME` portable entre amd64 et arm64 (Mac M1/M2).
3. **Couche de cache** — Ajout du `.dockerignore` et observation que la couche `pip install` est réutilisée depuis le cache quand seul le script Python est modifié (séparation `COPY requirements.txt` / `RUN pip install` / `COPY . .`).
4. **Docker Compose** — Orchestration de 3 services : `minio` (avec healthcheck), `jupyter` (depends_on minio healthy), `anfa-app` (construit depuis le Dockerfile local). Réutilisation du volume `anfa-minio-data` créé en séance 1 pour conserver les données uploadées.
5. **Notebook Jupyter** — Création de `exploration_minio.ipynb` qui se connecte à MinIO via `http://minio:9000` (DNS Docker Compose), liste les buckets, charge `lignes.csv` dans un DataFrame pandas et génère un graphique.
6. **Bonus** — Rédaction de `Dockerfile.multistage` : étape `builder` (installation des dépendances avec `--user`) copiée dans une image `slim` finale, réduisant ainsi la taille de l'image.

---

## Captures d'écran

### Stack Docker en cours d'exécution

![docker ps](captures/docker-ps.png)

*`docker ps` montrant les 3 conteneurs (anfa-minio, anfa-jupyter, anfa-app) du stack.*

### Notebook Jupyter — exploration des données

![jupyter pandas](captures/jupyter-pandas.png)

*Graphique généré dans `exploration_minio.ipynb` : longueur des lignes de bus Anfa (données chargées depuis MinIO avec pandas).*

---

## Difficultés rencontrées

- **JAVA_HOME sur Mac M2 (arm64)** : le chemin par défaut indiqué dans le Gist (`/usr/lib/jvm/java-17-openjdk-amd64`) ne fonctionne pas sur une architecture arm64. Solution : créer un lien symbolique neutre avec `ln -s "$(dirname $(dirname $(readlink -f /usr/bin/java)))" /usr/local/java` dans le `RUN` d'installation, puis `ENV JAVA_HOME=/usr/local/java`.
- **Volume MinIO** : le stack séance 2 réutilise le volume externe `anfa-minio-data` de séance 1 via `external: true` pour que le notebook Jupyter trouve directement les données uploadées.

---

## Exercices d'application

### Exercice 1 : Comprendre le Dockerfile

**1.1 Rôle de chaque instruction :**

| Instruction | Rôle |
|---|---|
| `FROM python:3.11-slim-bookworm` | Définit l'image de base : Python 3.11 sur Debian Bookworm minimal (sans les paquets superflus). |
| `ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1` | Désactive la génération de fichiers `.pyc` et force le flush immédiat des sorties (utile pour les logs en production). |
| `RUN apt-get update && apt-get install -y openjdk-17-jre-headless && rm -rf /var/lib/apt/lists/*` | Installe Java 17 (nécessaire pour Spark) et nettoie le cache apt dans la **même couche** pour ne pas l'embarquer dans l'image. |
| `ENV JAVA_HOME=/usr/local/java` | Indique à PySpark/Spark où se trouve l'installation Java. |
| `WORKDIR /app` | Définit le répertoire de travail dans le conteneur. Les commandes suivantes (COPY, RUN, CMD) s'exécutent depuis ce dossier. |
| `COPY requirements.txt .` | Copie seulement le fichier de dépendances (pas le code) pour tirer parti du cache Docker. |
| `RUN pip install --no-cache-dir -r requirements.txt` | Installe PySpark. `--no-cache-dir` évite de stocker le cache pip dans l'image (gain de taille). |
| `COPY . .` | Copie le reste du code applicatif. Placée **après** l'installation des dépendances pour que Docker réutilise le cache pip quand seul le code change. |
| `CMD ["python", "analyse_referentiel.py"]` | Commande exécutée par défaut au démarrage du conteneur (format exec, plus robuste que la forme shell). |

**1.2 Pourquoi séparer `COPY requirements.txt` du `COPY . .` ?**

Docker construit une image couche par couche. Chaque instruction `RUN`, `COPY` ou `ADD` crée une nouvelle couche. Si une couche est invalidée (le fichier source a changé), toutes les couches suivantes sont reconstruites.

En copiant d'abord `requirements.txt` puis en exécutant `pip install`, on crée une couche "dépendances" qui ne change que lorsque `requirements.txt` est modifié. Les modifications du code Python (`analyse_referentiel.py`) n'invalident pas cette couche → `pip install` est réutilisé depuis le cache, ce qui économise 60–120 secondes à chaque itération de développement.

---

### Exercice 2 : Observation du cache Docker

**2.1 Première construction :**

```
#6 [1/6] FROM python:3.11-slim-bookworm   → téléchargement de l'image de base
#7 [2/6] RUN apt-get install openjdk-17   → installation Java (~30 s)
#8 [3/6] COPY requirements.txt .          → copie du fichier requirements
#9 [4/6] RUN pip install pyspark==3.5.0   → téléchargement + installation (~90 s)
#10 [5/6] COPY . .                        → copie du code
```

**2.2 Deuxième construction (code Python modifié, requirements.txt inchangé) :**

```
#6 [1/6] FROM python:3.11-slim-bookworm   → CACHED
#7 [2/6] RUN apt-get install openjdk-17   → CACHED
#8 [3/6] COPY requirements.txt .          → CACHED
#9 [4/6] RUN pip install pyspark==3.5.0   → CACHED  ← gain majeur
#10 [5/6] COPY . .                        → invalidé (code changé)
```

Seule la couche `COPY . .` est reconstruite. Le `pip install` (la plus longue) est récupéré depuis le cache.

---

### Exercice 3 : Docker Compose multi-services

**3.1 Rôle de `depends_on` avec `condition: service_healthy` :**

Sans cette directive, Docker Compose démarrerait tous les services simultanément. Si Jupyter démarre avant que MinIO soit prêt à répondre, les premières connexions échoueront. `condition: service_healthy` force Compose à attendre que le `healthcheck` de MinIO retourne "healthy" (HTTP 200 sur `/minio/health/live`) avant de démarrer Jupyter.

**3.2 Différence `volumes nommés` vs `bind mounts` :**

| Aspect | Volume nommé (`anfa-minio-data`) | Bind mount (`./notebooks:/home/jovyan/work`) |
|---|---|---|
| Localisation | Géré par Docker (`/var/lib/docker/volumes/`) | Dossier précis sur l'hôte |
| Portabilité | Portable entre machines avec `docker volume` | Lié au chemin de la machine hôte |
| Usage typique | Données persistantes (base de données, MinIO) | Développement : code ou notebooks synchronisés |
| Visibilité hôte | Accès indirect via `docker volume inspect` | Accès direct depuis le Finder/explorateur |

**3.3 Pourquoi `restart: "no"` pour `anfa-app` ?**

Le service `anfa-app` exécute un script d'analyse qui termine normalement (code de sortie 0). Avec `restart: always` ou `unless-stopped`, Docker relancerait le conteneur en boucle après chaque fin d'exécution. `restart: "no"` est le comportement correct pour un **job** (one-shot) par opposition à un **service** (daemon).

---

### Exercice 4 : Diagnostic

**4.1 Pourquoi ce `Dockerfile` est inefficace ?**

```dockerfile
FROM python:3.11-slim-bookworm
COPY . .                         # ← PROBLÈME : copie tout d'abord
RUN pip install -r requirements.txt
```

Si on modifie `analyse_referentiel.py`, la couche `COPY . .` est invalidée, ce qui force la réexécution de `pip install` à chaque modification du code. Il faut inverser l'ordre :

```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```

**4.2 Erreur de connexion Jupyter → MinIO :**

```python
endpoint_url="http://localhost:9000"  # ← incorrect dans un conteneur
```

Dans un réseau Docker Compose, `localhost` désigne le conteneur Jupyter lui-même, pas MinIO. Il faut utiliser le nom du service tel que défini dans `docker-compose.yml` :

```python
endpoint_url="http://minio:9000"  # ← correct : résolution DNS Docker
```

---

### Exercice 5 : Mini-cas d'architecture

**Différences image standard vs image custom :**

| Critère | `jupyter/scipy-notebook:latest` | `anfa-analyse:v1` (custom) |
|---|---|---|
| Base | Image pré-construite par Jupyter | Construite depuis un `Dockerfile` maîtrisé |
| Taille | ~1–2 Go (inclut scipy, matplotlib, etc.) | ~700 Mo (Python + Java + PySpark uniquement) |
| Reproductibilité | Dépend des mises à jour de l'image externe | 100% contrôlée par notre `Dockerfile` |
| Déploiement | Plug-and-play, idéale pour l'exploration | Légère, optimisée pour la production |
| Audit sécurité | Dépendances opaques | Dépendances explicites dans `requirements.txt` |

**Quand construire sa propre image plutôt qu'utiliser une image existante ?**

- En **production** : contrôle total des dépendances, pas de surprise lors d'une mise à jour de l'image externe.
- Pour **réduire la taille** : une image custom n'embarque que ce dont l'application a besoin.
- Pour **intégrer des étapes de configuration** : variables d'environnement, certificats, utilisateurs spécifiques.
- Pour **respecter des exigences de sécurité** : audit des couches, pas de binaires inconnus.
