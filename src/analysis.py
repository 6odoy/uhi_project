import pandas as pd
import numpy as np
from scipy import stats
import pymannkendall as mk


PAIRS = [
    ("ndvi", "lst_celsius"),
    ("urban_pct", "lst_celsius"),
    ("urban_pct", "ndvi"),
]

PAIR_LABELS = {
    ("ndvi", "lst_celsius"): "ndvi_vs_lst",
    ("urban_pct", "lst_celsius"): "urban_vs_lst",
    ("urban_pct", "ndvi"): "urban_vs_ndvi",
}


def compute_correlations(df: pd.DataFrame) -> pd.DataFrame:
    """Pearson and Spearman correlations for each localidad across variable pairs."""
    records = []
    for localidad, group in df.groupby("localidad"):
        for x_col, y_col in PAIRS:
            x, y = group[x_col].values, group[y_col].values
            pr, pp = stats.pearsonr(x, y)
            sr, sp = stats.spearmanr(x, y)
            records.append(
                {
                    "localidad": localidad,
                    "pair": PAIR_LABELS[(x_col, y_col)],
                    "pearson_r": pr,
                    "pearson_p": pp,
                    "spearman_r": float(sr),
                    "spearman_p": float(sp),
                }
            )
    return pd.DataFrame(records)


def compute_trends(df: pd.DataFrame) -> pd.DataFrame:
    """Linear regression slope and Mann-Kendall trend test per localidad and variable."""
    records = []
    for localidad, group in df.groupby("localidad"):
        group_sorted = group.sort_values("year")
        years = group_sorted["year"].values
        for variable in ("lst_celsius", "ndvi"):
            values = group_sorted[variable].values
            slope, _, r_value, _, _ = stats.linregress(years, values)
            mk_result = mk.original_test(values)
            records.append(
                {
                    "localidad": localidad,
                    "variable": variable,
                    "slope": slope,
                    "r_squared": r_value ** 2,
                    "mk_trend": mk_result.trend,
                    "mk_p_value": mk_result.p,
                }
            )
    return pd.DataFrame(records)


def rank_localidades(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-localidad metrics ordered by LST change descending."""
    records = []
    for localidad, group in df.groupby("localidad"):
        group_sorted = group.sort_values("year")
        first_year = group_sorted["year"].min()
        last_year = group_sorted["year"].max()
        first = group_sorted[group_sorted["year"] == first_year].iloc[0]
        last = group_sorted[group_sorted["year"] == last_year].iloc[0]
        records.append(
            {
                "localidad": localidad,
                "lst_mean": group["lst_celsius"].mean(),
                "lst_last": last["lst_celsius"],
                "lst_change": last["lst_celsius"] - first["lst_celsius"],
                "ndvi_mean": group["ndvi"].mean(),
                "ndvi_change": last["ndvi"] - first["ndvi"],
                "urban_pct_last": last["urban_pct"],
            }
        )
    return (
        pd.DataFrame(records)
        .sort_values("lst_change", ascending=False)
        .reset_index(drop=True)
    )


def get_critical_localidades(df: pd.DataFrame, top_n: int = 2) -> list[str]:
    """Top-n localidades with the highest LST increase."""
    ranked = rank_localidades(df)
    return ranked.head(top_n)["localidad"].tolist()


def fit_lst_model(df: pd.DataFrame) -> dict:
    """OLS fit for LST ~ NDVI + urban_pct using the normal equations."""
    y = df["lst_celsius"].values
    X = np.column_stack([np.ones(len(y)), df["ndvi"].values, df["urban_pct"].values])
    coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    intercept, coef_ndvi, coef_urban = coeffs
    y_pred = X @ coeffs
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return {
        "intercept": float(intercept),
        "coef_ndvi": float(coef_ndvi),
        "coef_urban": float(coef_urban),
        "r_squared": float(r_squared),
        "n_samples": len(y),
    }


def predict_lst(ndvi: float, urban_pct: float, model: dict) -> float:
    """Apply the fitted OLS model to predict LST."""
    return model["intercept"] + model["coef_ndvi"] * ndvi + model["coef_urban"] * urban_pct
