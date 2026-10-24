import polars as pl

from pipeline.io import js_safe


def test_js_safe_casts_int64_to_int32_or_float():
    df = pl.DataFrame({"small": [1, 2], "big": [1, 2**40], "f": pl.Series([1.5, 2.5], dtype=pl.Float32)})
    out = js_safe(df)
    assert out.schema == {"small": pl.Int32, "big": pl.Float64, "f": pl.Float64}


def test_js_safe_all_null_int_column():
    out = js_safe(pl.DataFrame({"x": pl.Series([None, None], dtype=pl.Int64)}))
    assert out.schema["x"] == pl.Int32
