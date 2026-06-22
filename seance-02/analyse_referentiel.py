"""
analyse_referentiel.py
──────────────────────
Calcule quelques statistiques sur le référentiel d'Anfa
à partir des CSV (lignes, arrêts, bus, tarifs).

Le script utilise PySpark en mode LOCAL : aucune connexion à un
cluster externe, Spark simule un mini-cluster dans le processus
Python lui-même. Le code est strictement le même qu'en mode cluster ;
seul le paramètre "master" change.

Préparation à la séance 5 : ce même script sera réutilisé,
en pointant cette fois vers un vrai cluster Spark.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import sum as spark_sum, count, avg, desc

DATA_DIR = "/data/referentiel"   # chemin DANS le conteneur (bind mount)


def main() -> None:
    # ──────────────────────────────────────────────────────────
    # 1. Démarrer Spark en mode local
    # ──────────────────────────────────────────────────────────
    # "local[*]" demande à Spark d'utiliser tous les cœurs CPU
    # disponibles et de simuler un mini-cluster dans ce processus.
    spark = (
        SparkSession.builder
        .appName("Anfa - Analyse du référentiel")
        .master("local[*]")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )
    # Réduire le bruit des logs Spark (par défaut très verbeux)
    spark.sparkContext.setLogLevel("WARN")

    # ──────────────────────────────────────────────────────────
    # 2. Charger les 4 CSV
    # ──────────────────────────────────────────────────────────
    # header=True : la première ligne contient les noms de colonnes
    # inferSchema=True : Spark devine les types (int, string, etc.)
    lignes  = spark.read.csv(f"{DATA_DIR}/lignes.csv",  header=True, inferSchema=True)
    arrets  = spark.read.csv(f"{DATA_DIR}/arrets.csv",  header=True, inferSchema=True)
    bus     = spark.read.csv(f"{DATA_DIR}/bus.csv",     header=True, inferSchema=True)
    tarifs  = spark.read.csv(f"{DATA_DIR}/tarifs.csv",  header=True, inferSchema=True)

    # ──────────────────────────────────────────────────────────
    # 3. Calculs et affichage
    # ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  ANALYSE DU RÉFÉRENTIEL ANFA")
    print("=" * 60)



    nb_lignes = lignes.count()
    nb_arrets_uniques = arrets.select("arret_id").distinct().count()
    nb_bus = bus.count()
    nb_bus_actifs = bus.filter(bus.statut == "actif").count()

    print(f"\n  Nombre de lignes de bus       : {nb_lignes}")
    print(f"  Nombre d'arrêts uniques        : {nb_arrets_uniques}")
    print(f"  Nombre total de bus            : {nb_bus}")
    print(f"  Dont actifs                    : {nb_bus_actifs}")

    # Capacité totale de la flotte active
    capacite_totale = (
        bus.filter(bus.statut == "actif")
           .agg(spark_sum("capacite").alias("capacite_totale"))
           .collect()[0]["capacite_totale"]
    )
    print(f"  Capacité totale de la flotte   : {capacite_totale} places")

    # Top 3 des lignes les plus longues
    print("\n  Top 3 des lignes les plus longues :")
    top3 = lignes.orderBy(desc("distance_km")).limit(3).collect()
    for i, row in enumerate(top3, start=1):
        print(f"    {i}. {row['nom']:40s}  {row['distance_km']:5.2f} km")



    # Tarif moyen par type
    print("\n  Tarif moyen par type :")
    tarifs.groupBy("type").agg(avg("prix_fcfa").alias("prix_moyen")) \
          .orderBy("type") \
          .show(truncate=False)

    print("=" * 60)
    print("  Analyse terminée.\n")

    spark.stop()

if __name__ == "__main__":
    main()
