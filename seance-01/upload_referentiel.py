"""
upload_referentiel.py
Dépose le référentiel statique d'Anfa (lignes, arrêts, bus, tarifs)
dans un bucket MinIO local.
"""

from pathlib import Path

import boto3
from botocore.exceptions import ClientError

MINIO_ENDPOINT = "http://localhost:9000"
MINIO_ACCESS_KEY = "anfa-app-key"
MINIO_SECRET_KEY = "anfa-app-secret-2026"
BUCKET_NAME = "anfa-raw"

s3 = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    region_name="us-east-1",
)


def verifier_bucket(nom_bucket: str) -> None:
    try:
        s3.head_bucket(Bucket=nom_bucket)
        print(f"[OK] Bucket '{nom_bucket}' accessible.")
    except ClientError as e:
        print(f"[ERREUR] Bucket '{nom_bucket}' inaccessible : {e}")
        print("  Avez-vous bien créé le bucket et la clé applicative en partie 3 ?")
        raise


def uploader_fichier(chemin_local: Path, cle_objet: str) -> None:
    print(f"[UP] {chemin_local.name} -> s3://{BUCKET_NAME}/{cle_objet}")
    s3.upload_file(
        Filename=str(chemin_local),
        Bucket=BUCKET_NAME,
        Key=cle_objet,
    )


def lister_objets(nom_bucket: str) -> None:
    print(f"\nContenu du bucket '{nom_bucket}'")
    reponse = s3.list_objects_v2(Bucket=nom_bucket)
    if "Contents" not in reponse:
        print("  (vide)")
        return
    for obj in reponse["Contents"]:
        taille_ko = obj["Size"] / 1024
        print(f"  - {obj['Key']:35s} ({taille_ko:6.1f} Ko)")


def main() -> None:
    dossier_data = Path(__file__).parent.parent / "data" / "referentiel"

    verifier_bucket(BUCKET_NAME)

    fichiers_a_uploader = sorted(dossier_data.glob("*.csv"))

    if not fichiers_a_uploader:
        print(f"[ERREUR] Aucun fichier CSV trouvé dans {dossier_data}")
        return

    for chemin in fichiers_a_uploader:
        cle = f"referentiel/{chemin.name}"
        uploader_fichier(chemin, cle)

    lister_objets(BUCKET_NAME)
    print("\n[OK] Upload du référentiel Anfa terminé.")


if __name__ == "__main__":
    main()
