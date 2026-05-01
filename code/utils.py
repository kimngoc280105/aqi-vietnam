import pandas as pd
import numpy as np
import os




# ════════════════════════════════════════════════════════════════════════════
# LOAD & DESCRIBE
# ════════════════════════════════════════════════════════════════════════════

def load_data(path: str) -> pd.DataFrame:
    """Load CSV và in thông tin cơ bản về dataset."""
    df = pd.read_csv(path)
    print(f"{'='*55}")
    print(f"  Dataset loaded: {path}")
    print(f"{'='*55}")
    print(f"  Số mẫu (rows)     : {df.shape[0]:,}")
    print(f"  Số features (cols): {df.shape[1]}")
    print(f"\n  Kiểu dữ liệu:")
    for col, dtype in df.dtypes.items():
        null_count = df[col].isnull().sum()
        null_str = f"  ← {null_count} NaN" if null_count > 0 else ""
        print(f"    {col:<35} {str(dtype):<12}{null_str}")
    return df


def describe_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Thống kê mô tả mở rộng (thêm skewness & kurtosis)."""
    numeric = df.select_dtypes(include=np.number)
    desc = numeric.describe().T
    desc["skewness"] = numeric.skew().round(3)
    desc["kurtosis"] = numeric.kurtosis().round(3)
    return desc.round(3)