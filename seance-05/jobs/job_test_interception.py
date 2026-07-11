# job_test_interception.py
from pyspark.sql import SparkSession

# ⇄ 2.2 / 2.5 : SEULES ces deux valeurs changent entre les deux tests.
#   2.2 (avant) : ENDPOINT = "http://..."   SSL = "false"
#   2.5 (après) : ENDPOINT = "https://..."  SSL = "true"
ENDPOINT = "https://minio:9000"
SSL = "true"

TRUSTSTORE_OPTS = (
    "-Djavax.net.ssl.trustStore=/opt/truststore.jks "
    "-Djavax.net.ssl.trustStorePassword=changeit"
)

spark = SparkSession.builder \
    .appName("TestInterception") \
    .config("spark.hadoop.fs.s3a.endpoint", ENDPOINT) \
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", SSL) \
    .config("spark.hadoop.fs.s3a.access.key", "anfa-admin") \
    .config("spark.hadoop.fs.s3a.secret.key", "anfa-password-2026") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.driver.extraJavaOptions", TRUSTSTORE_OPTS) \
    .config("spark.executor.extraJavaOptions", TRUSTSTORE_OPTS) \
    .getOrCreate()

df = spark.createDataFrame([(1, "donnee_test_interception")], ["id", "valeur"])
df.write.mode("overwrite").parquet("s3a://anfa-raw/test-interception/")
print("Écriture terminée.")
