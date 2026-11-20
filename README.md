# Customer Segmentation Pro 🚀

**Advanced ML Analytics Platform — CCE V · D. Y. Patil College of Engineering, Akurdi**

---

## 🆚 Key Upgrades Over Version 1

| Feature | v1 | v2 Pro |
|---|---|---|
| Clustering algorithms | K-Means only | K-Means + Hierarchical |
| Feature dimensions | 3 (R, F, M) | 10 (RFM + AvgBasket, Products, Tenure, Velocity, InterPurchaseTime, Diversity, TotalItems) |
| PCA components | 2 | 3 (3D scatter) |
| CLV prediction | ❌ | ✅ GBM-based 12-month forecast |
| Churn risk scoring | ❌ | ✅ Per customer + per segment |
| Anomaly detection | ❌ | ✅ Isolation Forest (3% contamination) |
| Scatter view | 2D | 2D + 3D (bubble chart simulation) |
| Revenue trend chart | ❌ | ✅ Monthly line chart |
| Customer cohort chart | ❌ | ✅ Monthly new customer bar chart |
| Top products chart | ❌ | ✅ Horizontal bar (top 15) |
| Churn polar chart | ❌ | ✅ Polar area per segment |
| Market basket metrics | support, conf, lift | + leverage + conviction |
| Download formats | CSV | CSV + Excel (multi-sheet) + JSON |
| Dark mode | ❌ | ✅ Full dark theme with persistence |
| Drag-and-drop upload | ❌ | ✅ |
| Animated progress bar | ❌ | ✅ |
| Tooltip help system | ❌ | ✅ |
| Segment action cards | Table only | Cards + Table |
| Sample data | 500 customers | 800 customers + product categories |
| Upload size | 50 MB | 100 MB |
| Export route | CSV only | CSV + JSON + Excel |

---

## ⚡ Quick Start

```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py

# 4. Open your browser
#    http://127.0.0.1:5000
```

---

## 🏗️ Project Structure

```
customer-segmentation-pro/
├── app.py                      # Flask backend (caching, 4 download formats, health check)
├── engine.py                   # ML engine (10 features, CLV, churn, anomaly, Apriori)
├── sample_data_generator.py    # 800-customer realistic generator
├── requirements.txt
├── static/
│   ├── app.js                  # Frontend (10 charts, dark mode, drag-drop, tooltips)
│   ├── style.css               # Design system (CSS variables, dark mode, animations)
│   └── vendor/
│       └── chart.umd.js        # Chart.js (bundled, no CDN needed)
└── templates/
    └── index.html              # 11-section layout
```

---

## 🧠 ML Pipeline

```
Raw Data
  ↓ load_table()         CSV / Excel → DataFrame
  ↓ clean()              Normalise columns, drop cancellations, coerce types
  ↓ build_rfm_extended() 10 behavioural features
  ↓ detect_anomalies()   Isolation Forest (contamination=3%)
  ↓ churn_risk()         Rule-based score: Recency × Velocity
  ↓ predict_clv()        GBM → 12-month CLV forecast
  ↓ log1p + StandardScaler
  ↓ PCA(3 components)
  ↓ K-Means or Hierarchical clustering
  ↓ name_segments()      Human-friendly segment names
  ↓ mine_rules()         Apriori per segment (support, conf, lift, leverage, conviction)
  ↓ Scatter, trend, cohort, top-products aggregations
  ↓ JSON response → Frontend renders 10+ charts
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/` | Main dashboard |
| POST | `/api/analyze` | Analyse uploaded file |
| POST | `/api/demo` | Run on built-in 800-customer dataset |
| GET  | `/api/sample.csv` | Download sample CSV |
| GET  | `/api/download/<id>` | Download segments as CSV |
| GET  | `/api/download/<id>/excel` | Download multi-sheet Excel |
| GET  | `/api/download/<id>/json` | Download full results JSON |
| GET  | `/api/compare/<id1>/<id2>` | Compare two runs |
| GET  | `/health` | Health check |

---

## 📋 Required CSV Columns

```
InvoiceNo, CustomerID, InvoiceDate, Description, Quantity, UnitPrice
```
*(UCI Online Retail format; extra columns such as StockCode, Country are ignored)*

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, Flask 3, Flask-Caching
- **ML**: scikit-learn (K-Means, Hierarchical, PCA, Isolation Forest, GBM), mlxtend (Apriori)
- **Data**: pandas, numpy, scipy
- **Frontend**: Vanilla JS (ES2022), Chart.js 4, CSS Grid/Variables
- **Export**: openpyxl (Excel), JSON, CSV
