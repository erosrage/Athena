from pyspark.sql import SparkSession


def main():
    spark = SparkSession.builder.getOrCreate()
    print(f"Spark version: {spark.version}")
    # TODO: add pipeline logic here


if __name__ == "__main__":
    main()
