from pyspark.sql import SparkSession, DataFrame


def read_source(spark: SparkSession, path: str, fmt: str = "delta") -> DataFrame:
    return spark.read.format(fmt).load(path)


def write_output(df: DataFrame, path: str, fmt: str = "delta", mode: str = "overwrite") -> None:
    df.write.format(fmt).mode(mode).save(path)
