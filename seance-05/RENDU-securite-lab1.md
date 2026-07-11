# Rendu — Big Data & Sécurité · LAB 1 : Durcissement du stockage distribué

**Nom et prénom :** BIKOZI Balakibawi Sylvain
**Identifiant GitHub :** sbk6
**Date de soumission :** 11/07/2026

---

## Résumé du lab

Le cluster MinIO + Spark de la séance 05 a été durci selon deux axes complémentaires :
chiffrement des flux réseau par TLS (certificat signé par une CA locale) et authentification
fédérée par Keycloak 26.6 via le protocole OIDC. La comparaison des captures réseau avant et
après démontre concrètement le passage d'un trafic en clair (credentials exposés) à un trafic
opaque (TLS 1.3).

---

## Étapes réalisées

### Étape 2.1 — État initial & sauvegarde

**Carnet — informations du cluster :**
- Nom exact du service MinIO : `minio` (container : `anfa-minio`)
- Port exposé côté hôte pour l'API : `9000`
- Nom du volume de données MinIO : `seance-05_minio-data`

**Justification — pourquoi sauvegarder AVANT de modifier la config TLS ?**
Une mauvaise configuration TLS peut rendre MinIO inaccessible au démarrage suivant (le service
démarre mais aucun client ne peut se connecter, car les certificats sont rejetés en silence).
Sans sauvegarde préalable du volume, il serait impossible de revenir à un état fonctionnel sans
perte de données. La sauvegarde *avant* garantit qu'on peut restaurer l'état exact si la
modification TLS échoue — sauvegarder *après* ne servirait à rien puisque le volume aurait déjà
été modifié (ou serait inaccessible).

- Sauvegarde réalisée : `docker-compose.yml.bak` + archive `minio_data.tar.gz`

---

### Étape 2.2 — Capture trafic AVANT TLS (menace STRIDE : Information Disclosure)

- `tcpdump` lancé en mode `--net container:anfa-minio` avec `nicolaka/netshoot`.
- Job Spark soumis via HTTP → bucket `anfa-raw`, chemin `test-interception`, clé `anfa-admin` visibles en clair.
- Résultat `strings capture_avant.pcap` : **103× `Credential=anfa-admin`**, **143× `anfa-raw`**,
  **7× `donnee_test_interception`**, **187× `test-interception`**.
- **Capture sauvegardée** : `capture_avant.pcap`

---

### Étape 2.3 — Mise en place TLS sur MinIO

**Justification — corrections apportées par rapport au différentiel fourni :**

1. **Noms de fichiers obligatoires** : MinIO exige impérativement `public.crt` et `private.key`
   (pas `minio.crt`/`minio.key`). Le serveur démarre sans erreur avec n'importe quel nom,
   mais ignore silencieusement les fichiers mal nommés et continue en HTTP — c'est pourquoi
   aucun message explicite n'apparaît au démarrage même si les certificats sont présents.

2. **SANs (Subject Alternative Names) obligatoires** : le certificat initial utilisait seulement
   `CN=minio`. Le runtime Go (utilisé par MinIO et mc depuis Go 1.15 / 2020) refuse tout
   certificat sans SAN, avec l'erreur `x509: certificate relies on legacy Common Name field`.
   Correction : ajout de `DNS:minio`, `DNS:localhost`, `IP:127.0.0.1` dans les extensions v3.

**Que signifie concrètement l'absence de vérification des certificats clients (pas de mTLS) ?**
MinIO vérifie son propre identité auprès du client (le transport est chiffré, le serveur est
authentifié), mais il n'exige pas que le client prouve la sienne par certificat. En pratique,
tout client possédant des credentials valides (`access_key`/`secret_key`) peut se connecter :
le TLS protège la confidentialité du transport, mais la surface d'attaque sur les credentials
volés reste entière. L'étape 2.4 (OIDC) complémente cette lacune en permettant des credentials
temporaires à courte durée de vie (STS).

- CA locale créée (`CN=Cluster-CA-LOCAL`).
- Certificat serveur signé (`CN=minio`) avec SANs.
- Vérification : `openssl s_client -connect localhost:9000 -CAfile ~/certs/ca.crt` → `Verify return code: 0 (ok)`.

---

### Étape 2.4 — Authentification OIDC via Keycloak

**Justification — erreurs rencontrées et paramètres Keycloak concernés :**

1. **Première erreur : `AccessDenied` sur AssumeRoleWithWebIdentity (issuer mismatch).**
   Le token demandé via `http://localhost:8086` portait `iss: http://localhost:8086/realms/...`,
   mais MinIO interrogeait le discovery endpoint via `http://keycloak:8080` et attendait
   `iss: http://keycloak:8080/realms/...`. MinIO rejette tout token dont l'issuer ne correspond
   pas à celui du discovery document. Correction : requête du token depuis l'intérieur du réseau
   Docker (`--network seance-05_default`), garantissant la cohérence de l'URL émettrice.

2. **Deuxième erreur : `aud` (audience) ne contenait pas `minio-client`.**
   Par défaut, un client confidentiel Keycloak n'inclut pas son propre `client_id` dans l'`aud`
   du token — il place uniquement `"account"`. Ce comportement par défaut protège contre les
   tokens destinés à un service qui seraient réutilisés abusivement sur un autre service.
   Correction : ajout d'un mapper **Audience** (`included.client.audience=minio-client`).

3. **Troisième erreur : `role_policy` vs `claim_name`.**
   MinIO en mode `role_policy` exige un `RoleArn` dans la requête STS ; en mode `claim_name`,
   il lit la policy directement dans le JWT. Correction : configuration via
   `mc admin config set identity_openid claim_name=policy` et requête STS en **POST**
   (un GET est silencieusement traité comme un `ListBuckets` et retourne 403).

**Pourquoi `Direct Access Grants` est-il désactivé par défaut ?**
Ce grant permet à l'application de recevoir directement le mot de passe de l'utilisateur
(sans redirection OAuth). Il est désactivé par défaut pour éviter qu'une application compromise
ne capture les credentials utilisateur. Dans ce lab, il est activé car il n'y a pas d'interface
web de login utilisateur — c'est un cas d'usage de type machine-to-machine.

**Ce que prouve AssumeRoleWithWebIdentity que la simple configuration OIDC ne prouvait pas :**
La simple activation OIDC dans MinIO confirme que MinIO a chargé le discovery endpoint.
`AssumeRoleWithWebIdentity` retournant un `AccessKeyId` prouve que MinIO a : (1) téléchargé la
JWK set, (2) vérifié la signature du JWT, (3) validé l'issuer, l'audience et l'expiration,
(4) extrait le claim `policy=readwrite`, (5) créé un credentials STS temporaire associé à cette
policy. C'est la preuve end-to-end que le chemin d'authentification fédérée est fonctionnel.

- Service Keycloak 26.6 ajouté dans `docker-compose.yml` (port 8086).
- Realm `bigdata-securite`, client confidentiel `minio-client`, utilisateur `sylvain`.
- **Mapper Keycloak** : claim hardcodé `policy=readwrite` + mapper audience `minio-client`.
- Test `AssumeRoleWithWebIdentity` (POST) → `AccessKeyId` retourné avec succès.

---

### Étape 2.5 — Capture trafic APRÈS TLS

- Truststore JKS créé (`keytool -importcert`) avec la CA locale, distribué sur master et workers.
- `tcpdump` relancé, trafic HTTPS généré via `mc` vers MinIO.
- **Aucune string sensible** dans `capture_apres.pcap` (bucket, chemin, credentials chiffrés).
- **Capture sauvegardée** : `capture_apres.pcap`

---

## Comparaison avant / après

| Élément observable       | `capture_avant.pcap` (HTTP) | `capture_apres.pcap` (HTTPS/TLS) |
|--------------------------|-----------------------------|-----------------------------------|
| Bucket S3                | `anfa-raw` visible          | Absent (chiffré)                  |
| Chemin de l'objet        | `test-interception` visible | Absent (chiffré)                  |
| Credential AWS           | `Credential=anfa-admin/...` | Absent (chiffré)                  |
| Verbe HTTP               | `GET /`, `PUT /` visibles   | Absent (données opaques)          |
| Protocole négocié (ALPN) | –                           | `http/1.1` (extension TLS, normal)|

**Menace STRIDE mitigée** : *Information Disclosure* (T3) — un attaquant sur le réseau
Docker ne peut plus intercepter les secrets de stockage.

---

## Captures d'écran

### MinIO console accessible en HTTPS (cadenas TLS)
![MinIO HTTPS Console](captures/minio-https-console.png)

### Keycloak — Realm bigdata-securite, client minio-client
![Keycloak Realm](captures/keycloak-realm.png)

### Réponse STS AssumeRoleWithWebIdentity (AccessKeyId obtenu)
![STS Response](captures/sts-assume-role.png)

### Strings lisibles dans capture_avant.pcap (trafic en clair)
![Capture avant TLS](captures/pcap-avant-lisible.png)

### Absence de strings dans capture_apres.pcap (trafic chiffré)
![Capture après TLS](captures/pcap-apres-chiffre.png)

---

## Réflexion personnelle

La principale difficulté technique rencontrée a été l'**issuer mismatch** entre Keycloak et
MinIO : le token demandé via `localhost:8086` portait un `iss` différent de ce que MinIO voyait
en interrogeant `keycloak:8080`. La solution a été de demander le token depuis l'intérieur du
réseau Docker, garantissant la cohérence de l'émetteur. Par ailleurs, les certificats TLS sans
SANs étaient rejetés par Go (runtime de MinIO et de mc) depuis 2021, ce qui a nécessité de
régénérer les certificats avec les extensions `subjectAltName`.

Ce lab illustre que la sécurité du stockage distribué n'est pas juste une question de
permissions d'accès (IAM) mais aussi de **confidentialité des flux** : sans TLS, toute la
pile d'authentification AWS-SigV4 de MinIO est inopérante car un attaquant réseau peut voir
les signatures HMAC en transit et les rejouer sur un autre objet.

---

## Difficultés rencontrées

1. Certificat TLS sans SANs → `x509: certificate relies on legacy Common Name field` (fix : ajout des SANs via `openssl.cnf`).
2. Issuer mismatch Keycloak (`localhost:8086` vs `keycloak:8080`) → token rejeté par MinIO (fix : requête token depuis le réseau interne Docker).
3. `mc admin config set` avec `--insecure` insuffisant → montée la CA dans `~/.mc/certs/CAs/`.
4. Requête STS en GET ignorée (traitée comme ListBuckets) → correction en POST avec `Content-Type: application/x-www-form-urlencoded`.
5. Classe `S3AFileSystem` : truststore JVM non chargé par le SDK AWS S3A → utilisation de `mc` pour la capture après TLS.
