# Curve Fit TSV Processor

Interactive Streamlit app for ingesting curve-fit TSV files, converting EC/IC values to nM, computing cell-line geomeans, and deriving HEKALOT9253 and HEPATOCYTE ratio tables.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Run tests

```bash
pytest tests/ -v
```

## Docker

```bash
docker build -t curve-fit-processor .
docker run -p 8080:8080 curve-fit-processor
```

Open http://localhost:8080

## Deploy to Google Cloud Run

Prerequisites: [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed and authenticated.

```bash
gcloud run deploy curve-fit-processor \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

For team-only access, omit `--allow-unauthenticated` and grant `roles/run.invoker` to colleagues.

## Processing rules

- **Column format:** `('Tissue', 'CELL (description) (CTG)')_MEASUREMENT`
- **Blank imputation:** EC50/EC90/IC50 → 1000 nM; Span → 0; aAUC/pAUC → 1.0
- **Unit conversion:** Non-blank EC/IC values multiplied by 1e9 (M → nM)
- **Geomean:** User-selected cell lines; HEKALOT9253 and HEPATOCYTES_HUMAN_LOT_240604 excluded by default
- **Output:** Ratio table with HEKALOT9253/geomean and HEPATOCYTE/geomean plus raw M values
