"""
test_anfa_logic.py
───────────────────
Tests unitaires de la logique métier du pipeline Anfa.
Aucune dépendance à Airflow, boto3 ou MinIO : tests rapides et isolés.
"""

import sys
import os

# Permet d'importer anfa_logic.py situé dans ../dags/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dags"))

import pytest  # noqa: E402
from anfa_logic import (  # noqa: E402
    construire_cle_trajets,
    verifier_liste_fichiers,
    construire_message_notification,
)


def test_construire_cle_trajets_valeur_par_defaut():
    """Sans argument, la clé doit pointer vers trajets/trajets_recent.csv"""
    assert construire_cle_trajets() == "trajets/trajets_recent.csv"


def test_construire_cle_trajets_prefixe_personnalise():
    """Avec un préfixe personnalisé, il doit être utilisé dans la clé."""
    assert construire_cle_trajets("archive") == "archive/trajets_recent.csv"


def test_verifier_liste_fichiers_leve_erreur_si_vide():
    """Une liste vide doit lever une ValueError (Spark n'a rien produit)."""
    with pytest.raises(ValueError):
        verifier_liste_fichiers([])


def test_verifier_liste_fichiers_calcule_correctement():
    """Le résumé doit compter les fichiers et sommer les tailles en Ko."""
    objets = [
        {"Key": "part-0000.parquet", "Size": 1024},
        {"Key": "part-0001.parquet", "Size": 2048},
    ]
    resultat = verifier_liste_fichiers(objets)
    assert resultat["nb_fichiers"] == 2
    assert resultat["taille_totale_ko"] == 3.0


def test_construire_message_notification():
    """Le message doit contenir le nombre de fichiers et la taille."""
    resume = {"nb_fichiers": 3, "taille_totale_ko": 12.5}
    message = construire_message_notification(resume)
    assert "3 fichier" in message
    assert "12.5 Ko" in message
