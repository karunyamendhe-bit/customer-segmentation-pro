"""
Advanced sample data generator — richer dataset with:
 - 800 customers across 4 countries
 - Seasonal purchase patterns
 - Product categories
 - Realistic price & quantity distributions
"""
import numpy as np
import pandas as pd

RNG = np.random.default_rng(2024)

PRODUCTS = {
    "Home & Kitchen": [
        ("CERAMIC MUG SET",         3.99,  12),
        ("BAMBOO CUTTING BOARD",    12.99,  8),
        ("GLASS STORAGE JARS 6PK",  9.99, 10),
        ("SCENTED CANDLE VANILLA",   4.49, 20),
        ("LINEN KITCHEN TOWELS",     7.99, 15),
        ("CAST IRON SKILLET",       29.99,  5),
        ("HERB PLANTER SET",         8.99, 10),
        ("COPPER MEASURING CUPS",   14.99,  7),
    ],
    "Stationery": [
        ("DOTTED NOTEBOOK A5",       5.99, 25),
        ("FELT TIP PEN SET 20PK",    7.49, 20),
        ("WASHI TAPE BUNDLE",        4.99, 18),
        ("STICKY NOTE MEGA PACK",    3.99, 30),
        ("LEATHER JOURNAL",         15.99,  8),
        ("DESK ORGANISER SET",      12.49,  9),
    ],
    "Garden": [
        ("TERRACOTTA POT 15CM",      5.49, 12),
        ("SEED STARTER KIT",        11.99,  8),
        ("GARDEN GLOVES PAIR",       6.99, 14),
        ("WATERING CAN 2L",          9.99,  7),
        ("BIRD FEEDER WOODEN",      13.99,  5),
    ],
    "Gifts": [
        ("GIFT WRAP PAPER 5 SHEETS", 2.99, 40),
        ("RIBBON ASSORTMENT",        1.99, 50),
        ("THANK YOU CARDS 10PK",     3.49, 35),
        ("GIFT TAG BUNDLE 20PK",     1.49, 60),
        ("SCENTED DRAWER SACHETS",   4.99, 15),
    ],
    "Seasonal": [
        ("CHRISTMAS TREE BAUBLE",    2.49, 30),
        ("HALLOWEEN LANTERN",        6.99,  8),
        ("EASTER EGG DECORATING KIT",4.99, 10),
        ("ADVENT CALENDAR BOX",     19.99,  4),
    ],
}

COUNTRIES = ["United Kingdom", "Germany", "France", "Netherlands"]
COUNTRY_W = [0.70, 0.12, 0.10, 0.08]


def generate(n_customers=800, seed=42):
    rng = np.random.default_rng(seed)
    start  = pd.Timestamp("2023-01-01")
    end    = pd.Timestamp("2023-12-31")
    span   = (end - start).days

    # Flatten product list
    all_products = [(name, price, qty_mean, cat)
                    for cat, items in PRODUCTS.items()
                    for name, price, qty_mean in items]

    rows = []
    cid_base = 10000

    for ci in range(n_customers):
        cid     = str(cid_base + ci)
        country = rng.choice(COUNTRIES, p=COUNTRY_W)
        # Customers in higher segments buy more frequently
        seg_type = rng.choice(["high", "mid", "low"], p=[0.15, 0.45, 0.40])
        n_orders = {"high": rng.integers(8, 25), "mid": rng.integers(2, 10), "low": rng.integers(1, 4)}[seg_type]

        # Choose preferred category
        pref_cat = rng.choice(list(PRODUCTS.keys()))
        order_dates = sorted(start + pd.to_timedelta(rng.integers(0, span, n_orders), unit="D"))

        for d, date in enumerate(order_dates):
            inv = f"INV{rng.integers(100000, 999999)}"
            # 2–5 items per order, biased toward preferred category
            n_items = rng.integers(2, 6)
            weights = np.array([
                3.0 if cat == pref_cat else 1.0
                for _, _, _, cat in all_products
            ])
            weights /= weights.sum()
            chosen_idxs = rng.choice(len(all_products), size=n_items, replace=False, p=weights)
            for idx in chosen_idxs:
                name, price, qty_mean, cat = all_products[idx]
                qty   = max(1, int(rng.poisson(qty_mean)))
                price = round(price * rng.uniform(0.9, 1.1), 2)
                rows.append({
                    "InvoiceNo":   inv,
                    "CustomerID":  cid,
                    "InvoiceDate": date,
                    "Description": name,
                    "Quantity":    qty,
                    "UnitPrice":   price,
                    "Country":     country,
                })

    df = pd.DataFrame(rows)
    return df
