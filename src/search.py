import argparse
from collections import Counter
from typing import Iterable, List, Optional, Tuple

import duckdb

try:
	from .config import COLUMNS as COLS, THRESHOLDS as TH, SEARCH as SP  # type: ignore
	from .utils import nlp  # type: ignore
except ImportError:  # script execution fallback
	from config import COLUMNS as COLS, THRESHOLDS as TH, SEARCH as SP
	from utils import nlp


def pick_canonical_names(rows: List[Tuple[str]]) -> List[str]:
	# rows are tuples containing name_norm
	counter = Counter([r[0] for r in rows if r and r[0]])
	return [n for n, _ in counter.most_common(3)]


def _get_table_columns(con: duckdb.DuckDBPyConnection, table: str = "transactions") -> set:
	rows = con.execute(f"PRAGMA table_info('{table}')").fetchall()
	# rows: (cid, name, type, notnull, dflt_value, pk)
	return {r[1] for r in rows}


def fetch_rows_for_pan(con: duckdb.DuckDBPyConnection, pan: str) -> List[Tuple[str, str, str, str, str]]:
	pan_up = nlp.canonicalize_pan(pan)
	cols = _get_table_columns(con)
	select_parts: List[str] = [
		"name_norm",
		("name_phonetic" if "name_phonetic" in cols else "'' AS name_phonetic"),
		("address" if "address" in cols else "'' AS address"),
		("mobile" if "mobile" in cols else "'' AS mobile"),
		("pan_upper" if "pan_upper" in cols else "'' AS pan_upper"),
	]
	q = f"SELECT {', '.join(select_parts)} FROM transactions WHERE pan_upper = ?"
	return con.execute(q, [pan_up]).fetchall()


def candidate_block_by_names(con: duckdb.DuckDBPyConnection, names: List[str]) -> List[Tuple]:
	cols = _get_table_columns(con)
	# Prefer phonetic blocking if available
	if "name_phonetic" in cols:
		keys = list({nlp.phonetic_key(n) for n in names if n})
		if not keys:
			return []
		placeholders = ",".join(["?"] * len(keys))
		select_parts: List[str] = [
			"name_norm",
			"name_phonetic",
			("address" if "address" in cols else "'' AS address"),
			("mobile" if "mobile" in cols else "'' AS mobile"),
			("pan_upper" if "pan_upper" in cols else "'' AS pan_upper"),
		]
		q = f"""
			SELECT {', '.join(select_parts)}
			FROM transactions
			WHERE name_phonetic IN ({placeholders})
			LIMIT {SP.candidate_limit}
		"""
		return con.execute(q, keys).fetchall()
	# Fallback: use exact name_norm blocking (less recall but works without phonetics)
	norms = list({nlp.normalize_name(n) for n in names if n})
	if not norms:
		return []
	placeholders = ",".join(["?"] * len(norms))
	select_parts = [
		"name_norm",
		("'' AS name_phonetic"),
		("address" if "address" in cols else "'' AS address"),
		("mobile" if "mobile" in cols else "'' AS mobile"),
		("pan_upper" if "pan_upper" in cols else "'' AS pan_upper"),
	]
	q = f"""
		SELECT {', '.join(select_parts)}
		FROM transactions
		WHERE name_norm IN ({placeholders})
		LIMIT {SP.candidate_limit}
	"""
	return con.execute(q, norms).fetchall()


def verify_candidate(base_names: List[str], row: Tuple[str, str, str, str, str]) -> bool:
	name_norm, _phon, address, mobile, _pan = row
	if not name_norm:
		return False
	best_name = max((nlp.fuzzy_name_score(name_norm, b) for b in base_names), default=0)
	if best_name >= TH.name_strict:
		return True
	if best_name >= TH.name_medium:
		return True
	if best_name >= TH.name_loose:
		# require some attribute evidence for loose matches
		address_scores = [nlp.fuzzy_address_score(address or "", adr or "") for adr in [address]]
		addr_ok = max(address_scores or [0]) >= TH.address_loose
		mobile_ok = True if not TH.mobile_exact_required else bool(mobile and mobile in (row[3] or ""))
		return addr_ok or mobile_ok
	return False


def expand_all_transactions_for_entities(con: duckdb.DuckDBPyConnection, pans: List[str], names: List[str]) -> List[Tuple]:
	pans = [nlp.canonicalize_pan(p) for p in pans if p]
	names = list({n for n in names if n})
	conds = []
	params: List[str] = []
	if pans:
		placeholders = ",".join(["?"] * len(pans))
		conds.append(f"pan_upper IN ({placeholders})")
		params.extend(pans)
	if names:
		placeholders = ",".join(["?"] * len(names))
		conds.append(f"name_norm IN ({placeholders})")
		params.extend(names)
	where = " OR ".join(conds) if conds else "1=0"
	q = f"SELECT * FROM transactions WHERE {where}"
	if SP.limit_return_rows:
		q += f" LIMIT {SP.limit_return_rows}"
	return con.execute(q, params).fetchall()


def search_by_pan(con: duckdb.DuckDBPyConnection, pan: str) -> List[Tuple]:
	base_rows = fetch_rows_for_pan(con, pan)
	if not base_rows:
		return []
	base_names = pick_canonical_names([(r[0],) for r in base_rows])
	candidates = candidate_block_by_names(con, base_names)
	verified = [r for r in candidates if verify_candidate(base_names, r)]
	all_pans = {r[4] for r in base_rows if r[4]}
	all_names = {r[0] for r in base_rows if r[0]} | {r[0] for r in verified}
	return expand_all_transactions_for_entities(con, list(all_pans), list(all_names))


def search_by_seed_name(con: duckdb.DuckDBPyConnection, seed_name: str) -> List[Tuple]:
	seed_norm = nlp.normalize_name(seed_name)
	base_names = [seed_norm]
	candidates = candidate_block_by_names(con, base_names)
	verified = [r for r in candidates if verify_candidate(base_names, r)]
	all_names = {r[0] for r in verified} | {seed_norm}
	# include PANs from verified candidates
	pans = [r[4] for r in verified if r[4]]
	return expand_all_transactions_for_entities(con, pans, list(all_names))


def main(db_path: str, pan: Optional[str], seed_name: Optional[str]) -> None:
	con = duckdb.connect(db_path, read_only=True)
	if pan:
		rows = search_by_pan(con, pan)
	elif seed_name:
		rows = search_by_seed_name(con, seed_name)
	else:
		raise SystemExit("Provide either --pan or --seed-name")
	print(f"Rows: {len(rows)}")
	# Print a small sample
	for row in rows[:20]:
		print(row)


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--db", required=True, help="Path to DuckDB database")
	parser.add_argument("--pan", help="PAN to search")
	parser.add_argument("--seed-name", help="Seed name (Marathi or English)")
	args = parser.parse_args()
	main(args.db, args.pan, args.seed_name)
