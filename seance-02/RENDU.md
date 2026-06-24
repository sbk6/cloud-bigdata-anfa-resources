# Rendu Séance 2

**Nom et prénom :** BIKOZI Balakibawi Sylvain  
**Identifiant GitHub :** sbk6

---

## Résumé de la séance

Cette séance avait pour objectif de maîtriser Docker au-delà du simple `docker run` : écrire un `Dockerfile` pour conteneuriser une application PySpark, comprendre le mécanisme de cache des couches, puis orchestrer une stack multi-services (MinIO + Jupyter + application d'analyse) avec Docker Compose.

---

## Étapes principales

1. **Script PySpark** : Écriture de `analyse_referentiel.py` qui charge les 4 CSV du référentiel Anfa en mode local (`local[*]`) et calcule des statistiques agrégées (comptages, top 3, tarif moyen par type).
2. **Dockerfile** : Construction de l'image `anfa-analyse:v1` basée sur `python:3.11-slim-bookworm` avec installation de `openjdk-17-jre-headless` (requis par Spark). Un lien symbolique `/usr/local/java` rend `JAVA_HOME` portable entre amd64 et arm64 (Mac M1/M2).
3. **Couche de cache** : Ajout du `.dockerignore` et observation que la couche `pip install` est réutilisée depuis le cache quand seul le script Python est modifié (séparation `COPY requirements.txt` / `RUN pip install` / `COPY . .`).
4. **Docker Compose** : Orchestration de 3 services : `minio` (avec healthcheck), `jupyter` (depends_on minio healthy), `anfa-app` (construit depuis le Dockerfile local). Réutilisation du volume `anfa-minio-data` créé en séance 1 pour conserver les données uploadées.
5. **Notebook Jupyter** : Création de `exploration_minio.ipynb` qui se connecte à MinIO via `http://minio:9000` (DNS Docker Compose), liste les buckets, charge `lignes.csv` dans un DataFrame pandas et génère un graphique.
6. **Bonus** : Rédaction de `Dockerfile.multistage` : étape `builder` (installation des dépendances avec `--user`) copiée dans une image `slim` finale, réduisant ainsi la taille de l'image.

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

### Exercice 1 : QCM conceptuel

---

**1.1** Réponse : **C. Un conteneur partage le noyau de la machine hôte.**

Un conteneur ne contient pas son propre noyau : il utilise celui de l'hôte via les namespaces Linux, ce qui le rend beaucoup plus léger et rapide à démarrer qu'une machine virtuelle qui embarque un noyau complet.

---

**1.2** Réponse : **B. L'image est un modèle figé en lecture seule ; le conteneur est une instance en cours d'exécution.**

L'image est un artefact statique stocké sur disque (comparable à une classe en POO) ; le conteneur est l'instance vivante et modifiable issue de cette image lors d'un `docker run`.

---

**1.3** Réponse : **B. Les namespaces.**

Docker utilise les namespaces Linux (pid, net, mnt, uts, ipc, user) pour donner à chaque conteneur une vue isolée du système : ses processus, ses interfaces réseau et son système de fichiers sont invisibles des autres conteneurs.

---

**1.4** Réponse : **A. Les cgroups.**

Les *control groups* (cgroups) du noyau Linux permettent de fixer et de mesurer les quotas de ressources (CPU, mémoire, I/O disque) d'un groupe de processus ; c'est sur ce mécanisme que Docker s'appuie pour `--memory`, `--cpus`, etc.

---

**1.5** Réponse : **B. Dans une machine virtuelle Linux invisible gérée par Docker Desktop.**

macOS ne partage pas de noyau Linux ; Docker Desktop crée silencieusement une VM Linux légère (via Apple Virtualization Framework ou HyperKit) dans laquelle tournent le daemon Docker et tous les conteneurs.

---

**1.6** Réponse : **B. La société d'origine qui a créé et open-sourcé Docker en 2013.**

DotCloud était une plateforme PaaS qui a développé Docker en interne pour ses propres besoins ; l'équipe l'a rendu open source en mars 2013 et a ensuite renommé l'entreprise « Docker Inc. ».

---

**1.7** Réponse : **C. Docker a apporté un format d'image portable, une CLI simple et un registre public, en s'appuyant sur les mêmes primitives que LXC.**

Docker n'a pas inventé les namespaces ni les cgroups (déjà présents dans le noyau Linux depuis 2008) mais il a standardisé l'empaquetage (image en couches + Dockerfile), la distribution (Docker Hub) et la CLI, rendant la conteneurisation accessible à tous les développeurs.

---

**1.8** Réponse : **B. Open Container Initiative — une norme ouverte pour les images et le runtime.**

L'OCI, fondée en 2015 sous l'égide de la Linux Foundation, définit les spécifications `image-spec` et `runtime-spec` qui garantissent l'interopérabilité entre outils (Docker, Podman, containerd, CRI-O…).

---

### Exercice 2 : Lecture et analyse d'un Dockerfile

Le Dockerfile analysé :

```dockerfile
FROM python:3.11
WORKDIR /application
COPY . /application
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python", "main.py"]
```

---

**2.1 Pour chaque instruction, expliquez en une phrase ce qu'elle fait.**

| Instruction | Rôle |
|---|---|
| `FROM python:3.11` | Définit l'image de base : Python 3.11 dans la version complète (non allégée, ~900 Mo). |
| `WORKDIR /application` | Crée et définit `/application` comme répertoire de travail courant ; toutes les instructions suivantes s'exécutent depuis ce dossier. |
| `COPY . /application` | Copie l'intégralité du contexte de build (dossier courant sur l'hôte) dans `/application` à l'intérieur du conteneur. |
| `RUN pip install -r requirements.txt` | Exécute pip pour installer les dépendances listées dans `requirements.txt` et crée une nouvelle couche de l'image avec ces packages installés. |
| `EXPOSE 5000` | Déclare (documentation) que l'application écoute sur le port 5000 ; n'ouvre aucun port vers l'hôte. |
| `CMD ["python", "main.py"]` | Définit la commande lancée par défaut au démarrage du conteneur (format exec : plus robuste que la forme shell). |

---

**2.2 Quelle est la différence pratique entre `EXPOSE 5000` et l'option `-p 5000:5000` de `docker run` ?**

`EXPOSE 5000` est une **annotation documentaire** intégrée à l'image : elle signale aux utilisateurs que le processus interne écoute sur le port 5000, mais elle n'ouvre rien vers l'extérieur. Le port reste inaccessible depuis la machine hôte.

`-p 5000:5000` dans `docker run` **publie réellement** le port : il mappe le port 5000 de l'hôte vers le port 5000 du conteneur, rendant l'application joignable à `http://localhost:5000`. Sans ce flag, même un `EXPOSE` présent, l'application n'est pas accessible depuis l'hôte.

En résumé : `EXPOSE` → documentation ; `-p` → ouverture effective du port.

---

**2.3 Deux problèmes selon les bonnes pratiques**

**Problème 1 — Image de base trop lourde (`python:3.11`)**

`python:3.11` est l'image "full" (~900 Mo) qui embarque des outils de compilation, des bibliothèques système et des paquets superflus dont une application Flask/FastAPI n'a pas besoin à l'exécution. Cela augmente inutilement la taille de l'image finale, le temps de téléchargement et la surface d'attaque.

*Correction :* utiliser `python:3.11-slim-bookworm` (~130 Mo) qui n'inclut que le strict minimum pour faire tourner Python.

**Problème 2 — Mauvais ordre `COPY / RUN pip` (cache invalidé à chaque modification de code)**

La ligne `COPY . /application` copie **tout le code source avant** `RUN pip install`. Toute modification d'un fichier Python (même un caractère) invalide la couche `COPY`, forçant `pip install` à se réexécuter entièrement à chaque `docker build`.

*Correction :* copier d'abord `requirements.txt` seul, lancer `pip install`, puis copier le reste du code :

```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```

Ainsi, la couche `pip install` n'est invalidée que si `requirements.txt` change.

---

**2.4 Version corrigée du Dockerfile**

```dockerfile
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /application

# Dépendances d'abord → couche cachée tant que requirements.txt ne change pas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code applicatif ensuite
COPY . .

# Utilisateur non-root pour l'exécution (principe du moindre privilège)
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser
USER appuser

EXPOSE 5000
CMD ["python", "main.py"]
```

Améliorations appliquées :
- Image `slim` : réduit la taille d'environ 770 Mo.
- Ordre `COPY requirements.txt` → `pip install` → `COPY . .` : préserve le cache Docker.
- Utilisateur `appuser` non-root : si l'application est compromise, l'attaquant n'a pas les droits root dans le conteneur.
- `--no-cache-dir` : évite de stocker le cache pip dans l'image.
- Variables `PYTHONDONTWRITEBYTECODE` / `PYTHONUNBUFFERED` : pas de `.pyc` inutiles, logs en temps réel.

---

### Exercice 3 : Diagnostic

#### 3.1 Le build qui échoue

Dockerfile problématique :

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install -r requirements.txt   ← exécuté avant le COPY !
COPY . .
CMD ["python", "main.py"]
```

**a. Cause précise de l'erreur :**

L'instruction `RUN pip install -r requirements.txt` est exécutée **avant** `COPY . .`. À cette étape du build, le fichier `requirements.txt` n'existe pas encore dans le filesystem du conteneur en construction — il n'a pas été copié. Pip cherche le fichier dans `/app/requirements.txt` et ne le trouve pas, d'où l'erreur `[Errno 2] No such file or directory`.

**b. Correction du Dockerfile :**

Copier `requirements.txt` avant de l'utiliser :

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .          # copier d'abord
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

**c. Pourquoi cette erreur illustre une mauvaise compréhension de Docker :**

L'étudiant a confondu le **contexte de build** (le dossier sur sa machine hôte) avec le **filesystem du conteneur en construction**. Chaque instruction `RUN` s'exécute dans l'état du conteneur tel qu'il est à cet instant du build — pas dans le dossier de l'hôte. Docker construit l'image couche par couche : tant qu'une instruction `COPY` n'a pas copié un fichier dans le conteneur, ce fichier n'existe pas pour les commandes suivantes. L'hôte et le conteneur sont deux environnements distincts dès le début du build.

---

#### 3.2 Le conteneur qui ne voit pas l'autre

docker-compose.yml problématique :

```yaml
services:
  api:
    build: ./api
    environment:
      DATABASE_URL: "postgresql://user:password@localhost:5432/anfa"
    depends_on:
      - db
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: anfa
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
```

**a. L'erreur dans le `DATABASE_URL` :**

L'hôte utilisé est `localhost`. Dans Docker Compose, chaque service tourne dans son propre conteneur avec sa propre interface réseau. `localhost` vu depuis le conteneur `api` désigne **le conteneur `api` lui-même**, pas la base de données. Il n'y a aucun processus PostgreSQL sur `localhost:5432` du point de vue d'`api`, d'où le `connection refused`.

**b. Correction :**

Remplacer `localhost` par le **nom du service** tel que déclaré dans `docker-compose.yml`. Docker Compose crée automatiquement un réseau interne où chaque service est résolvable par son nom via DNS :

```yaml
DATABASE_URL: "postgresql://user:password@db:5432/anfa"
```

`db` est résolu par Docker en l'adresse IP du conteneur `db` à l'intérieur du réseau Compose.

---

### Exercice 4 : Optimisation d'image

Dockerfile problématique (image finale : 1,1 Go) :

```dockerfile
FROM ubuntu:22.04
RUN apt-get update
RUN apt-get install -y python3 python3-pip
RUN apt-get install -y curl wget git build-essential
COPY . /app
WORKDIR /app
RUN pip3 install -r requirements.txt
CMD ["python3", "downloader.py"]
```

**a. Au moins quatre problèmes identifiés :**

| # | Problème | Explication |
|---|---|---|
| 1 | **Image de base inadaptée (`ubuntu:22.04`)** | Ubuntu est un OS généraliste de ~80 Mo, mais inclut des couches complètes d'un système Linux. Pour une app Python, `python:3.11-slim-bookworm` intègre déjà Python et pèse ~130 Mo, soit environ 900 Mo de moins. |
| 2 | **Packages inutiles (`curl`, `wget`, `git`, `build-essential`)** | Ces outils de build et de téléchargement ne sont pas nécessaires à l'exécution du script (qui utilise `requests` pour les téléchargements HTTP). Ils ajoutent ~200–300 Mo à l'image et élargissent la surface d'attaque. |
| 3 | **Trois `RUN apt-get` séparés sans nettoyage du cache** | Chaque `RUN` crée une couche distincte. Séparer `apt-get update` et `apt-get install` peut produire des incohérences de cache (le cache de paquets est périmé lors de l'install suivant). De plus, les listes apt (~40 Mo) ne sont jamais nettoyées (`rm -rf /var/lib/apt/lists/*`), gonflant l'image finale. |
| 4 | **`COPY . /app` avant `pip install`** | Toute modification de code invalide la couche `COPY`, forçant la réexécution de `pip install` inutilement. L'ordre correct est : `COPY requirements.txt` → `pip install` → `COPY . .`. |
| 5 | **Absence de `ENV PYTHONDONTWRITEBYTECODE` et `PYTHONUNBUFFERED`** | Sans ces variables, Python génère des fichiers `.pyc` inutiles et bufférise ses sorties, ce qui retarde l'apparition des logs dans `docker logs`. |
| 6 | **Exécution en root** | Aucun utilisateur non-root n'est créé. Si l'application est compromise, l'attaquant dispose des droits root dans le conteneur. |

---

### Exercice 5 : Mini-cas d'architecture

L'équipe d'Awa et Kossi veut industrialiser un pipeline nocturne GPS → MinIO + exploration Jupyter.

**a. Services à conteneuriser dans le `docker-compose.yml` :**

| Service | Image | Rôle |
|---|---|---|
| `minio` | `minio/minio:latest` | Stockage objet S3-compatible : reçoit les résultats agrégés écrits par le script et les expose au notebook Jupyter pour l'exploration. |
| `pipeline` | Image custom (Dockerfile) | Script Python one-shot qui se connecte au FTP, lit le fichier JSON Lines de positions GPS, nettoie et agrège les données, puis écrit le résultat dans MinIO. |
| `jupyter` | `jupyter/scipy-notebook:latest` | Environnement notebook interactif pour que Kossi explore les données stockées dans MinIO, génère des graphiques et valide les résultats. |

---

**b. Restart policy pour le script Python FTP :**

Je choisirais **`on-failure`**. Le script est un job nocturne qui doit s'arrêter proprement (exit 0) après avoir traité les données ; `on-failure` le relancera automatiquement s'il échoue pour une raison transitoire (FTP indisponible, fichier corrompu, erreur réseau) sans le boucler indéfiniment après une fin normale. Les politiques `always` ou `unless-stopped` relanceraient le conteneur même après un succès, ce qui n'a aucun sens pour un job one-shot.

---

**c. Passer la date au script — deux mécanismes :**

**Mécanisme 1 — Variable d'environnement (`environment:`) :**

```yaml
environment:
  PIPELINE_DATE: "2026-06-24"
```

Le script lit `os.environ["PIPELINE_DATE"]`. Pour rejouer une date précise, on surcharge au lancement :
```bash
docker compose run -e PIPELINE_DATE=2026-06-20 pipeline
```

**Mécanisme 2 — Argument de commande (`command:`) :**

```yaml
command: ["python", "pipeline.py", "--date", "2026-06-24"]
```

Pour rejouer :
```bash
docker compose run pipeline python pipeline.py --date 2026-06-20
```

**Recommandation : la variable d'environnement.** Elle ne nécessite pas de modifier la signature CLI du script (lecture via `os.environ`), est compatible avec n'importe quel orchestrateur externe (Cron, Airflow, GitHub Actions) et reste visible dans `docker inspect` pour l'audit et le débogage.

---

**d. Pourquoi un conteneur séparé plutôt que le script dans Jupyter ?**

Mélanger le script batch et le notebook dans un seul conteneur va à l'encontre du principe de **responsabilité unique** : chaque conteneur devrait avoir une seule fonction bien définie. Les deux composants ont des cycles de vie très différents — Jupyter tourne en permanence pour l'exploration interactive, tandis que le script s'exécute une fois par nuit puis s'arrête. Les embarquer ensemble maintient Jupyter actif en permanence et consomme inutilement des ressources. De plus, leurs images idéales divergent : le script n'a besoin que de Python + quelques bibliothèques légères, alors que `scipy-notebook` pèse ~1,5 Go. Enfin, un conteneur dédié permet de configurer des ressources, des logs et un restart policy spécifiques au job, impossibles à distinguer si tout est dans le même conteneur.

---

**e. Squelette de `docker-compose.yml` :**

```yaml
services:

  minio:
    image: minio/minio:latest
    environment:
      MINIO_ROOT_USER: anfa-admin
      MINIO_ROOT_PASSWORD: anfa-password
    volumes:
      - minio-data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 5

  pipeline:
    build: ./pipeline
    environment:
      PIPELINE_DATE: "2026-06-24"      # surcharger avec -e pour un rejeu
      MINIO_ENDPOINT: "http://minio:9000"
    restart: "on-failure"
    depends_on:
      minio:
        condition: service_healthy

  jupyter:
    image: jupyter/scipy-notebook:latest
    ports:
      - "8888:8888"
    environment:
      JUPYTER_TOKEN: anfa-token
    volumes:
      - ./notebooks:/home/jovyan/work
    depends_on:
      minio:
        condition: service_healthy

volumes:
  minio-data:
```

Structure défendable : MinIO démarre en premier avec un healthcheck ; `pipeline` et `jupyter` attendent que MinIO soit healthy avant de démarrer (`depends_on` + `condition: service_healthy`). Le réseau interne créé implicitement par Compose permet à `pipeline` et `jupyter` d'atteindre MinIO via `http://minio:9000`. Le volume `minio-data` est géré par Docker et persiste entre les arrêts/relances du stack.
