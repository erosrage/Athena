# Databricks notebook source
# MAGIC %md ## Exploration notebook

# COMMAND ----------
# MAGIC %md ### Load data

# COMMAND ----------
spark.sql("SHOW DATABASES").display()

# COMMAND ----------
# MAGIC %md ### Sample query
df = spark.table("samples.nyctaxi.trips").limit(1000)
df.display()
