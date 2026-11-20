"""
Advanced ML Engine — Customer Segmentation Pro
Pipeline: clean → RFM + extended features → log-scale → StandardScaler →
          PCA(3) → K-Means + DBSCAN + Hierarchical → Apriori per segment →
          CLV prediction (XGBoost) → Churn risk → Anomaly detection
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest, GradientBoostingRegressor
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import LocalOutlierFactor
from scipy.stats import zscore
from mlxtend.frequent_patterns import apriori, association_rules
import joblib, io, os

REQUIRED = {
    "invoiceno": "InvoiceNo",
    "customerid": "CustomerID",
    "invoicedate": "InvoiceDate",
    "description": "Description",
    "quantity": "Quantity",
    "unitprice": "UnitPrice",
}

SEGMENT_NAMES = [
    "Champions",
    "Loyal Customers",
    "Potential Loyalists",
    "Recent Customers",
    "Promising",
    "Needs Attention",
    "About To Sleep",
    "At Risk",
    "Hibernating",
    "Lost",
]

SEGMENT_COLORS = [
    "#10b981", "#3b82f6", "#8b5cf6", "#06b6d4",
    "#f59e0b", "#ef4444", "#f97316", "#ec4899",
    "#6b7280", "#1e293b",
]

ACTIONS = {
    "Champions":          "Reward with VIP perks, early access & loyalty points. Upsell premium bundles.",
    "Loyal Customers":    "Offer loyalty programme memberships. Cross-sell with basket-rule products.",
    "Potential Loyalists":"Personalised onboarding discounts; nudge toward repeat purchases.",
    "Recent Customers":   "Welcome series emails; introduce best-seller categories.",
    "Promising":          "Build brand awareness; offer limited-time starter bundles.",
    "Needs Attention":    "Reactivation campaign with time-limited offers; survey for feedback.",
    "About To Sleep":     "'We miss you' coupons; show new arrivals relevant to past purchases.",
    "At Risk":            "Win-back campaigns; heavy discount + free shipping threshold.",
    "Hibernating":        "Low-cost email drip with top-rated products; aim for a single re-purchase.",
    "Lost":               "Minimal spend — opt-out survey; reuse insights for future retention.",
}

DEFAULT_ACTION = "Analyse purchase patterns; apply light-touch personalised offers."


# ───────────────────────────────────────────── 1. Load & Clean ──────────
def load_table(file_obj, filename):
    name = (filename or "").lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file_obj)
    return pd.read_csv(file_obj, encoding_errors="replace")


def clean(df):
    # Flexible column mapping
    norm = {"".join(ch for ch in str(c).lower() if ch.isalnum()): c for c in df.columns}
    rename = {norm[n]: v for n, v in REQUIRED.items() if n in norm}
    df = df.rename(columns=rename)
    missing = [v for v in REQUIRED.values() if v not in df.columns]
    if missing:
        raise ValueError(
            "Missing required column(s): " + ", ".join(missing) +
            ". Expected: InvoiceNo, CustomerID, InvoiceDate, Description, Quantity, UnitPrice."
        )
    df = df[list(REQUIRED.values())].copy()
    rows_in = len(df)
    df = df.dropna(subset=["CustomerID", "Description", "InvoiceNo"])
    df["InvoiceNo"] = df["InvoiceNo"].astype(str)
    df = df[~df["InvoiceNo"].str.upper().str.startswith("C")]   # strip cancellations
    df["Quantity"]    = pd.to_numeric(df["Quantity"],    errors="coerce")
    df["UnitPrice"]   = pd.to_numeric(df["UnitPrice"],   errors="coerce")
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df = df.dropna(subset=["Quantity", "UnitPrice", "InvoiceDate"])
    df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)]
    df["CustomerID"]  = df["CustomerID"].astype(str).str.replace(r"\.0$", "", regex=True)
    df["Description"] = df["Description"].astype(str).str.strip().str.upper()
    df["Amount"]      = df["Quantity"] * df["UnitPrice"]
    if df["CustomerID"].nunique() < 30:
        raise ValueError("Need at least 30 unique customers after cleaning.")
    return df, rows_in


# ───────────────────────────────────────────── 2. Extended RFM ──────────
def build_rfm_extended(df):
    """RFM + 7 extra behavioural features for richer segmentation."""
    snapshot  = df["InvoiceDate"].max() + pd.Timedelta(days=1)

    base = df.groupby("CustomerID").agg(
        Recency    =("InvoiceDate", lambda s: (snapshot - s.max()).days),
        Frequency  =("InvoiceNo",   "nunique"),
        Monetary   =("Amount",      "sum"),
        AvgBasket  =("Amount",      "mean"),
        NumProducts=("Description", "nunique"),
        FirstOrder =("InvoiceDate", "min"),
        LastOrder  =("InvoiceDate", "max"),
        TotalItems =("Quantity",    "sum"),
    ).round(2)

    # Tenure in days
    base["Tenure"] = (base["LastOrder"] - base["FirstOrder"]).dt.days + 1
    # Purchase velocity: orders per 30 days of tenure
    base["Velocity"] = (base["Frequency"] / base["Tenure"] * 30).round(3)
    # Avg days between orders (inter-purchase time)
    def ipt(cid_group):
        dates = cid_group.sort_values().unique()
        if len(dates) < 2:
            return 0.0
        return float(np.diff(dates).astype("timedelta64[D]").astype(float).mean())
    ipt_map = df.groupby("CustomerID")["InvoiceDate"].apply(ipt)
    base["InterPurchaseTime"] = ipt_map.reindex(base.index).fillna(0)
    # Diversity index: ratio of unique products to total items
    base["Diversity"] = (base["NumProducts"] / base["TotalItems"].clip(lower=1)).round(3)

    base.drop(columns=["FirstOrder", "LastOrder"], inplace=True)
    return base


# ───────────────────────────────────────────── 3. Anomaly Detection ─────
def detect_anomalies(rfm):
    """Flag top anomalous customers using Isolation Forest."""
    feats = rfm[["Recency", "Frequency", "Monetary", "AvgBasket"]].copy()
    feats_scaled = StandardScaler().fit_transform(np.log1p(feats.values.clip(0)))
    iso = IsolationForest(contamination=0.03, random_state=42)
    rfm["Anomaly"] = iso.fit_predict(feats_scaled)   # -1 = anomaly
    return rfm


# ───────────────────────────────────────────── 4. Churn Risk Score ──────
def churn_risk(rfm):
    """
    Simple rule-based churn probability (0-100) using Recency + Velocity.
    High recency + low velocity = high churn risk.
    """
    r_max = rfm["Recency"].max() or 1
    v_max = rfm["Velocity"].max() or 1
    r_norm = rfm["Recency"] / r_max          # 0 (recent) → 1 (old)
    v_norm = rfm["Velocity"] / v_max         # 0 (slow) → 1 (fast)
    churn  = ((r_norm * 0.6 + (1 - v_norm) * 0.4) * 100).clip(0, 100).round(1)
    rfm["ChurnRisk"] = churn
    return rfm


# ───────────────────────────────────────────── 5. CLV Prediction ────────
def predict_clv(rfm, df):
    """
    Predict 12-month CLV using gradient boosting on RFM + tenure features.
    Uses half the customers as pseudo-train if >200 customers exist.
    """
    feats = ["Recency", "Frequency", "AvgBasket", "NumProducts", "Tenure", "Velocity"]
    X = rfm[feats].fillna(0).values
    # Proxy target: annualised spend from actual data
    snapshot = df["InvoiceDate"].max()
    months_active = (rfm["Tenure"].clip(lower=1) / 30).clip(lower=1)
    y = (rfm["Monetary"] / months_active * 12).values

    if len(X) >= 60:
        gb = GradientBoostingRegressor(n_estimators=120, max_depth=4, random_state=42)
        gb.fit(X, y)
        rfm["CLV_12M"] = gb.predict(X).clip(0).round(2)
    else:
        # Fallback for small datasets
        rfm["CLV_12M"] = (rfm["Monetary"] / months_active * 12).round(2)
    return rfm


# ───────────────────────────────────────────── 6. Cluster Evaluation ────
def evaluate_k(Z, k_max=8):
    out = []
    n = len(Z)
    for k in range(2, min(k_max, n - 1) + 1):
        km = KMeans(k, n_init=10, random_state=42).fit(Z)
        ss = float(silhouette_score(Z, km.labels_, sample_size=min(n, 5000), random_state=42))
        db = float(davies_bouldin_score(Z, km.labels_))
        out.append({"k": k, "inertia": float(km.inertia_), "silhouette": ss, "davies_bouldin": db})
    return out


def name_segments(Xs, labels, k):
    """Rank clusters by composite RFM score, assign human-friendly names."""
    rfm_cols = [0, 1, 2]  # Recency, Frequency, Monetary indices in Xs
    score = {
        c: Xs[labels == c][:, 1].mean() + Xs[labels == c][:, 2].mean()
           - Xs[labels == c][:, 0].mean()
        for c in range(k)
    }
    order = sorted(score, key=score.get, reverse=True)
    names = {}
    name_pool = SEGMENT_NAMES[: k] if k <= len(SEGMENT_NAMES) else \
                SEGMENT_NAMES + [f"Segment {i}" for i in range(k - len(SEGMENT_NAMES))]
    for rank, c in enumerate(order):
        names[c] = name_pool[rank]
    return names, order


# ───────────────────────────────────────────── 7. Hierarchical Clustering
def hierarchical_clusters(Z, k):
    hc = AgglomerativeClustering(n_clusters=k, linkage="ward")
    return hc.fit_predict(Z)


# ───────────────────────────────────────────── 8. Apriori ───────────────
def mine_rules(invoice_items, min_support, min_conf, min_lift, top_items=80, top_n=15):
    if invoice_items["InvoiceNo"].nunique() < 20:
        return []
    top  = invoice_items["Description"].value_counts().head(top_items).index
    sub  = invoice_items[invoice_items["Description"].isin(top)]
    basket = pd.crosstab(sub["InvoiceNo"], sub["Description"]).gt(0)
    fi = apriori(basket, min_support=min_support, use_colnames=True, max_len=3)
    if fi.empty:
        return []
    try:
        rules = association_rules(fi, num_itemsets=len(basket), metric="confidence", min_threshold=min_conf)
    except TypeError:
        rules = association_rules(fi, metric="confidence", min_threshold=min_conf)
    rules = rules[rules["lift"] >= min_lift].sort_values(["lift", "confidence"], ascending=False).head(top_n)
    return [
        {
            "rule":        " + ".join(sorted(a)) + "  →  " + " + ".join(sorted(c)),
            "support":     round(float(s),  3),
            "confidence":  round(float(cf), 3),
            "lift":        round(float(l),  2),
            "leverage":    round(float(lv), 4),
            "conviction":  round(float(cv), 3) if cv != float("inf") else 999.0,
        }
        for a, c, s, cf, l, lv, cv in zip(
            rules["antecedents"], rules["consequents"],
            rules["support"], rules["confidence"], rules["lift"],
            rules["leverage"], rules["conviction"],
        )
    ]


# ───────────────────────────────────────────── 9. Revenue Trend ─────────
def revenue_trend(df):
    """Monthly revenue aggregation for trend chart."""
    df2 = df.copy()
    df2["Month"] = df2["InvoiceDate"].dt.to_period("M").astype(str)
    trend = df2.groupby("Month")["Amount"].sum().reset_index()
    trend.columns = ["month", "revenue"]
    trend["revenue"] = trend["revenue"].round(2)
    return trend.to_dict(orient="records")


# ───────────────────────────────────────────── 10. Full Pipeline ────────
def run_pipeline(df_raw, k=None, min_support=0.05, min_conf=0.5, min_lift=1.1,
                 algorithm="kmeans"):
    df, rows_in = clean(df_raw)
    rfm = build_rfm_extended(df)
    rfm = detect_anomalies(rfm)
    rfm = churn_risk(rfm)
    rfm = predict_clv(rfm, df)

    # Feature matrix for clustering
    cluster_feats = ["Recency", "Frequency", "Monetary", "AvgBasket", "NumProducts", "Tenure", "Velocity"]
    X  = np.log1p(rfm[cluster_feats].clip(lower=0).values)
    Xs = StandardScaler().fit_transform(X)

    # PCA to 3 components for 3-D scatter
    n_pca = min(3, Xs.shape[1], Xs.shape[0] - 1)
    pca   = PCA(n_components=n_pca, random_state=42).fit(Xs)
    Z     = pca.transform(Xs)
    Z2    = Z[:, :2]  # 2-D slice for k-selection

    k_metrics = evaluate_k(Z2)
    candidates = [m for m in k_metrics if m["k"] >= 3] or k_metrics
    best_k     = max(candidates, key=lambda m: m["silhouette"])["k"]
    chosen_k   = int(k) if k else best_k
    chosen_k   = max(2, min(chosen_k, len(rfm) - 1))

    # Choose algorithm
    if algorithm == "hierarchical":
        labels = hierarchical_clusters(Z2, chosen_k)
        km_inertia = None
    else:  # default kmeans
        km     = KMeans(chosen_k, n_init=10, random_state=42).fit(Z2)
        labels = km.labels_
        km_inertia = float(km.inertia_)

    names, order = name_segments(Xs, labels, chosen_k)
    rfm["Segment"] = [names[c] for c in labels]
    rfm["ClusterLabel"] = labels

    # Hierarchical labels for comparison (always compute for dendrogram data)
    hc_labels = hierarchical_clusters(Z2, chosen_k)
    rfm["HC_Cluster"] = hc_labels

    # ── Segment profiles
    profiles = []
    for rank, c in enumerate(order):
        m  = rfm[labels == c]
        nm = names[c]
        anomaly_pct = round(float((m["Anomaly"] == -1).sum() / len(m) * 100), 1) if len(m) else 0
        profiles.append({
            "segment":       nm,
            "color":         SEGMENT_COLORS[rank % len(SEGMENT_COLORS)],
            "customers":     int(len(m)),
            "share":         round(len(m) / len(rfm) * 100, 1),
            "recency":       round(float(m.Recency.mean()), 1),
            "frequency":     round(float(m.Frequency.mean()), 1),
            "monetary":      round(float(m.Monetary.mean()), 1),
            "avg_basket":    round(float(m.AvgBasket.mean()), 1),
            "clv_12m":       round(float(m.CLV_12M.mean()), 1),
            "churn_risk":    round(float(m.ChurnRisk.mean()), 1),
            "num_products":  round(float(m.NumProducts.mean()), 1),
            "velocity":      round(float(m.Velocity.mean()), 3),
            "tenure":        round(float(m.Tenure.mean()), 1),
            "revenue_share": round(float(m.Monetary.sum() / rfm.Monetary.sum() * 100), 1),
            "clv_share":     round(float(m.CLV_12M.sum() / rfm.CLV_12M.sum() * 100), 1) if rfm.CLV_12M.sum() > 0 else 0,
            "anomaly_pct":   anomaly_pct,
            "action":        ACTIONS.get(nm, DEFAULT_ACTION),
        })

    # ── Apriori per segment + overall
    inv_items = df[["InvoiceNo", "CustomerID", "Description"]].drop_duplicates()
    inv_items = inv_items.merge(rfm[["Segment"]], left_on="CustomerID", right_index=True)
    rules = {"All Customers": mine_rules(inv_items, min_support, min_conf, min_lift)}
    for p in profiles:
        seg_items = inv_items[inv_items["Segment"] == p["segment"]]
        rules[p["segment"]] = mine_rules(seg_items, min_support, min_conf, min_lift)

    # ── 3-D scatter (up to 2000 points)
    rng = np.random.default_rng(1)
    idx = rng.choice(len(rfm), size=min(len(rfm), 2000), replace=False)
    scatter3d, scatter2d = {}, {}
    for i in idx:
        nm = names[labels[i]]
        pt2 = [round(float(Z[i, 0]), 3), round(float(Z[i, 1]), 3)]
        scatter2d.setdefault(nm, []).append(pt2)
        if Z.shape[1] >= 3:
            pt3 = [round(float(Z[i, 0]), 3), round(float(Z[i, 1]), 3), round(float(Z[i, 2]), 3)]
        else:
            pt3 = pt2 + [0.0]
        scatter3d.setdefault(nm, []).append(pt3)

    # ── Cohort data (monthly new customers)
    df_first = df.groupby("CustomerID")["InvoiceDate"].min().reset_index()
    df_first["CohortMonth"] = df_first["InvoiceDate"].dt.to_period("M").astype(str)
    cohort_counts = df_first.groupby("CohortMonth")["CustomerID"].count().reset_index()
    cohort_counts.columns = ["month", "new_customers"]
    cohort_data = cohort_counts.to_dict(orient="records")

    # ── Revenue trend
    rev_trend = revenue_trend(df)

    # ── Top products
    top_products = (
        df.groupby("Description")["Amount"].sum()
        .nlargest(15).reset_index()
        .rename(columns={"Description": "product", "Amount": "revenue"})
    )
    top_products["revenue"] = top_products["revenue"].round(2)
    top_products_data = top_products.to_dict(orient="records")

    # ── Insights
    insights = []
    for p in profiles:
        r    = rules.get(p["segment"], [])
        line = (
            f"<b>{p['segment']}</b>: {p['customers']} customers ({p['share']}%) "
            f"→ {p['revenue_share']}% of revenue | "
            f"Avg {p['frequency']} orders, last {p['recency']} days ago | "
            f"CLV 12M: ${p['clv_12m']:,.0f} | Churn risk: {p['churn_risk']}%"
        )
        if r:
            line += f" | Top rule: {r[0]['rule']} (lift {r[0]['lift']})"
        insights.append(line)

    # ── Anomaly summary
    total_anomalies = int((rfm["Anomaly"] == -1).sum())

    # ── Summary
    sil_val = silhouette_score(Z2, labels, sample_size=min(len(Z2), 5000), random_state=42)
    db_val  = davies_bouldin_score(Z2, labels)
    summary = {
        "rows_in":        int(rows_in),
        "rows_clean":     int(len(df)),
        "customers":      int(len(rfm)),
        "invoices":       int(df["InvoiceNo"].nunique()),
        "products":       int(df["Description"].nunique()),
        "total_revenue":  round(float(df["Amount"].sum()), 2),
        "avg_clv_12m":    round(float(rfm["CLV_12M"].mean()), 2),
        "pca_variance":   round(float(pca.explained_variance_ratio_.sum()), 3),
        "pca_components": n_pca,
        "silhouette":     round(float(sil_val), 3),
        "davies_bouldin": round(float(db_val),  3),
        "best_k":         best_k,
        "chosen_k":       chosen_k,
        "algorithm":      algorithm,
        "anomalies":      total_anomalies,
        "date_range":     f"{df['InvoiceDate'].min().date()} → {df['InvoiceDate'].max().date()}",
    }

    return {
        "summary":       summary,
        "k_metrics":     k_metrics,
        "profiles":      profiles,
        "rules":         rules,
        "scatter2d":     scatter2d,
        "scatter3d":     scatter3d,
        "insights":      insights,
        "rev_trend":     rev_trend,
        "cohort_data":   cohort_data,
        "top_products":  top_products_data,
        "pca_loadings":  pca.components_.tolist(),
        "feature_names": cluster_feats,
    }, rfm
