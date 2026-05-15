# Yearly 



## Layout

```
yearly/
├── main.py          # FastAPI app – all routes
├── database.py      # sqlite3 wrapper (replaces db/index.js)
├── models.py        # Pydantic request/response models
├── requirements.txt
├── data/            # created automatically; holds yearview.db
└── public/          # place index.html here (same as before)
    └── index.html
```

## Setup

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 3000
```

Open http://localhost:3000 — the frontend is served from `public/`.

