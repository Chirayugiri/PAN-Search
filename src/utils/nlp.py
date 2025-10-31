import re
import unicodedata
from typing import Iterable, List, Optional, Tuple

import phonetics
from rapidfuzz import fuzz
from unidecode import unidecode
from indic_transliteration import sanscript
from indic_transliteration.sanscript import SchemeMap, SCHEMES, transliterate

DEVANAGARI_BLOCK = (0x0900, 0x097F)
PAN_REGEX = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", re.IGNORECASE)


def is_devanagari(text: str) -> bool:
	if not text:
		return False
	for ch in text:
		cp = ord(ch)
		if DEVANAGARI_BLOCK[0] <= cp <= DEVANAGARI_BLOCK[1]:
			return True
	return False


def normalize_whitespace(text: str) -> str:
	return re.sub(r"\s+", " ", text or "").strip()


def normalize_punct(text: str) -> str:
	# keep letters/digits/spaces; drop most punctuation
	return re.sub(r"[^\w\s\u0900-\u097F]", " ", text or "")


def to_nfc(text: str) -> str:
	return unicodedata.normalize("NFC", text or "")


def normalize_name(raw: Optional[str]) -> str:
	if not raw:
		return ""
	text = to_nfc(raw)
	text = normalize_punct(text)
	text = normalize_whitespace(text)
	return text.lower()


def detect_language(text: str) -> str:
	return "devanagari" if is_devanagari(text) else "latin"


def devanagari_to_latin(text: str) -> str:
	if not text:
		return ""
	# ITRANS is robust for consonant/vowel distinctions
	return transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)


def english_phonetic_key(text: str) -> str:
	p, s = phonetics.dmetaphone(text or "")
	return (p or s or "")


def marathi_phonetic_key(text: str) -> str:
	latin = devanagari_to_latin(text)
	p, s = phonetics.dmetaphone(latin or "")
	return (p or s or "")


def phonetic_key(text: str) -> str:
	if not text:
		return ""
	lang = detect_language(text)
	return marathi_phonetic_key(text) if lang == "devanagari" else english_phonetic_key(text)


def fuzzy_name_score(a: str, b: str) -> int:
	# robust to token order and spacing differences
	return int(fuzz.token_set_ratio(a, b))


def fuzzy_address_score(a: str, b: str) -> int:
	return int(fuzz.token_set_ratio(a, b))


def canonicalize_pan(pan: Optional[str]) -> str:
	if not pan:
		return ""
	return re.sub(r"\s+", "", pan).upper()


def extract_pan_codes(blob: Optional[str]) -> List[str]:
	if not blob:
		return []
	return [canonicalize_pan(m.group(1)) for m in PAN_REGEX.finditer(blob)]

# Heuristics for Marathi buyer/seller blob:
# Try to capture text after markers like "नाव:-" up to next field marker (वय|पत्ता|पॅन)
NAME_SNIPPET_PATTERNS = [
	re.compile(r"नाव[:-]\s*([^;:,\n]+?)\s*(?:वय|पत्ता|पॅन|,|;|\n)")
]


def extract_names_from_blob(blob: Optional[str]) -> List[str]:
	if not blob:
		return []
	candidates: List[str] = []
	for pat in NAME_SNIPPET_PATTERNS:
		candidates.extend([normalize_name(m.group(1)) for m in pat.finditer(blob)])
	# Fallbacks: split by digits/role markers like "1):" "2):"
	if not candidates:
		parts = re.split(r"\b\d+\)\s*[:：]", blob)
		for p in parts:
			p = normalize_whitespace(p)
			if p:
				# take first 4 words as a crude name guess
				words = re.split(r"\s+", normalize_punct(p))
				if 1 <= len(words) <= 6:
					candidates.append(normalize_name(" ".join(words)))
	# Deduplicate and keep non-empty
	seen = set()
	uniq = []
	for c in candidates:
		if c and c not in seen:
			seen.add(c)
			uniq.append(c)
	return uniq[:3]
