import pytest
from unittest.mock import MagicMock
from src.pipeline import read_source, write_output


def test_read_source_calls_spark():
    spark = MagicMock()
    spark.read.format.return_value.load.return_value = MagicMock()
    read_source(spark, "dbfs:/data/input", "delta")
    spark.read.format.assert_called_once_with("delta")


def test_write_output_calls_spark():
    df = MagicMock()
    write_output(df, "dbfs:/data/output", "delta", "overwrite")
    df.write.format.assert_called_once_with("delta")
