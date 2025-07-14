def fill_nan(df):
    """
    针对每一列，用插值的方法进行缺失值填补
    """
    for col in df.columns:
        raw_series = df[col]
        if raw_series.isnull().sum() > 0:
            filled_series = raw_series.interpolate(
                limit_direction="both", kind="quadratic"
            )
            df[col] = filled_series
    return df
