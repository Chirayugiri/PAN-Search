import os
from typing import List, Optional

import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

try:
	from .config import THRESHOLDS as TH, SEARCH as SP  # type: ignore
	from .utils import nlp  # type: ignore
	from .search import search_by_pan as _search_by_pan, search_by_seed_name as _search_by_seed_name  # type: ignore
except ImportError:
	from config import THRESHOLDS as TH, SEARCH as SP
	from utils import nlp
	from search import search_by_pan as _search_by_pan, search_by_seed_name as _search_by_seed_name

DB_PATH = os.getenv("TX_DB_PATH", "data/tx.duckdb")

app = FastAPI(title="Transactions Search API", version="0.1.0")
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
	return {"status": "ok"}


@app.get("/search")
def search(
	pan: Optional[str] = Query(default=None),
	seed_name: Optional[str] = Query(default=None),
	limit: Optional[int] = Query(default=1000),
) -> dict:
	if not pan and not seed_name:
		raise HTTPException(status_code=400, detail="Provide either pan or seed_name")
	if not os.path.exists(DB_PATH):
		raise HTTPException(status_code=500, detail=f"DB not found at {DB_PATH}")
	con = duckdb.connect(DB_PATH, read_only=True)
	try:
		if pan:
			rows = _search_by_pan(con, pan)
		else:
			rows = _search_by_seed_name(con, seed_name or "")
		rows = rows[: (limit or len(rows))]
		# Fetch column names for transactions table
		cols = [r[1] for r in con.execute("PRAGMA table_info('transactions')").fetchall()]
		# Add score and current_age column names
		all_cols = cols + ["score", "age"]
		# Convert rows to dicts
		result_data = []
		for row in rows:
			row_dict = {}
			for i, col_name in enumerate(all_cols):
				val = row[i] if i < len(row) else None
				# Ensure age is properly serialized
				if col_name == "age" and val is not None:
					row_dict[col_name] = int(val) if isinstance(val, (int, float)) else val
				else:
					row_dict[col_name] = val
			result_data.append(row_dict)
		return {"count": len(rows), "data": result_data}
	finally:
		con.close()
