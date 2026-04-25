"""
Real Clinical Data Loader
=========================
Dual-source data pipeline:
  1. OpenFDA Drug Adverse Events API  (free, no auth, 328k+ diabetes records)
  2. HuggingFace Drug Reviews dataset (lewtun/drug-reviews, 161k records)

Both sources are fetched via HTTP, normalised to a shared schema, cached to
SQLite, and used to calibrate the trial simulator's disease priors.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OPENFDA_DRUG_EVENT = "https://api.fda.gov/drug/event.json"
HF_ROWS_API = "https://datasets-server.huggingface.co/rows"
HF_DRUG_REVIEWS_DATASET = "lewtun/drug-reviews"
CT_GOV_API = "https://clinicaltrials.gov/api/v2/studies"


# Maps lowercase drug name fragments → (drug_class, disease_key, component)
# component: "a" = primary therapeutic, "b" = adjuvant, "c" = high-toxicity
DRUG_LOOKUP: Dict[str, Dict[str, str]] = {
    # Type-2 Diabetes
    "metformin":      {"drug_class": "biguanide",            "disease": "type2_diabetes", "comp": "a"},
    "glipizide":      {"drug_class": "sulfonylurea",         "disease": "type2_diabetes", "comp": "b"},
    "glimepiride":    {"drug_class": "sulfonylurea",         "disease": "type2_diabetes", "comp": "b"},
    "sitagliptin":    {"drug_class": "dpp4_inhibitor",       "disease": "type2_diabetes", "comp": "a"},
    "empagliflozin":  {"drug_class": "sglt2_inhibitor",      "disease": "type2_diabetes", "comp": "a"},
    "insulin":        {"drug_class": "insulin",              "disease": "type2_diabetes", "comp": "c"},
    "saxagliptin":    {"drug_class": "dpp4_inhibitor",       "disease": "type2_diabetes", "comp": "a"},
    # Hypertension
    "lisinopril":     {"drug_class": "ace_inhibitor",        "disease": "hypertension",   "comp": "a"},
    "enalapril":      {"drug_class": "ace_inhibitor",        "disease": "hypertension",   "comp": "a"},
    "amlodipine":     {"drug_class": "calcium_channel_blocker","disease":"hypertension",  "comp": "b"},
    "losartan":       {"drug_class": "arb",                  "disease": "hypertension",   "comp": "a"},
    "hydrochlorothiazide": {"drug_class":"thiazide_diuretic","disease": "hypertension",   "comp": "b"},
    "metoprolol":     {"drug_class": "beta_blocker",         "disease": "hypertension",   "comp": "c"},
    "carvedilol":     {"drug_class": "beta_blocker",         "disease": "hypertension",   "comp": "c"},
    # NSCLC
    "carboplatin":    {"drug_class": "platinum_agent",       "disease": "nsclc",          "comp": "c"},
    "cisplatin":      {"drug_class": "platinum_agent",       "disease": "nsclc",          "comp": "c"},
    "paclitaxel":     {"drug_class": "taxane",               "disease": "nsclc",          "comp": "b"},
    "docetaxel":      {"drug_class": "taxane",               "disease": "nsclc",          "comp": "b"},
    "pembrolizumab":  {"drug_class": "pd1_inhibitor",        "disease": "nsclc",          "comp": "a"},
    "nivolumab":      {"drug_class": "pd1_inhibitor",        "disease": "nsclc",          "comp": "a"},
    "osimertinib":    {"drug_class": "egfr_inhibitor",       "disease": "nsclc",          "comp": "a"},
    "erlotinib":      {"drug_class": "egfr_inhibitor",       "disease": "nsclc",          "comp": "a"},
}

DISEASE_KEYWORDS: Dict[str, List[str]] = {
    "type2_diabetes": ["diabetes", "type 2", "t2d", "type2", "hyperglycaemia", "hyperglycemia"],
    "hypertension":   ["hypertension", "blood pressure", "hbp", "high blood pressure"],
    "nsclc":          ["lung cancer", "nsclc", "non-small cell", "carcinoma", "adenocarcinoma"],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_disease_from_text(text: str) -> Optional[str]:
    t = text.lower()
    for disease, kws in DISEASE_KEYWORDS.items():
        if any(k in t for k in kws):
            return disease
    return None


def _detect_disease_from_drugs(drugs: List[Dict]) -> Optional[str]:
    for drug in drugs:
        name = drug.get("name", "").lower()
        for fragment, info in DRUG_LOOKUP.items():
            if fragment in name:
                return info["disease"]
    return None


def _get_drug_info(drug_name: str) -> Optional[Dict[str, str]]:
    lower = drug_name.lower()
    for fragment, info in DRUG_LOOKUP.items():
        if fragment in lower:
            return info
    return None


# ---------------------------------------------------------------------------
# OpenFDA fetcher
# ---------------------------------------------------------------------------

def stream_fda_events(condition: str, batch_size: int = 100):
    """
    Generator yielding batches of FDA adverse event records.
    Enables streaming fetch to reduce memory usage and support online learning.
    """
    search_terms = {
        "type2_diabetes": "type 2 diabetes",
        "hypertension":   "hypertension",
        "nsclc":          "lung cancer",
    }
    query = search_terms.get(condition, condition.replace("_", " "))
    
    page = 0
    while True:
        params = {
            "search": f'patient.drug.drugindication:"{query}"',
            "limit": batch_size,
            "skip": page * batch_size,
        }
        try:
            resp = requests.get(OPENFDA_DRUG_EVENT, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if not results:
                break
            
            batch = []
            for raw in results:
                parsed = _parse_fda_record(raw)
                if parsed:
                    batch.append(parsed)
            yield batch
            time.sleep(0.2)  # polite rate-limiting
            page += 1
        except Exception as exc:
            print(f"[RealDataLoader] OpenFDA stream error at page {page}: {exc}")
            break

def fetch_fda_adverse_events(
    condition: str = "type2_diabetes",
    n_records: int = 500,
    cache_db: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch adverse event reports from the OpenFDA Drug Events endpoint.
    Uses the stream_fda_events generator and a local SQLite cache.
    """
    if cache_db:
        cached = _load_fda_cache(cache_db, condition, n_records)
        if cached:
            return cached

    all_records: List[Dict[str, Any]] = []
    print(f"[RealDataLoader] Fetching {n_records} OpenFDA records for '{condition}'...")
    
    for batch in stream_fda_events(condition, batch_size=100):
        all_records.extend(batch)
        if len(all_records) >= n_records:
            all_records = all_records[:n_records]
            break

    if cache_db and all_records:
        _save_fda_cache(cache_db, condition, all_records)

    print(f"[RealDataLoader] Parsed {len(all_records)} valid FDA records for '{condition}'.")
    return all_records


def _parse_fda_record(raw: Dict) -> Optional[Dict[str, Any]]:
    patient = raw.get("patient", {})

    # Age (normalise all units to years, impute with median 60.0 if missing)
    age = 60.0
    age_val = patient.get("patientonsetage")
    age_unit = str(patient.get("patientonsetageunit", "801"))
    if age_val:
        try:
            val = float(age_val)
            if age_unit == "800":   val *= 10    # decades
            elif age_unit == "802": val /= 12    # months
            elif age_unit == "803": val /= 52    # weeks
            elif age_unit == "804": val /= 365   # days
            age = val
        except Exception:
            pass

    sex = {"1": "M", "2": "F"}.get(str(patient.get("patientsex", "0")), "M")

    # Weight (impute with median 80.0 if missing)
    weight = 80.0
    wt = patient.get("patientweight")
    if wt:
        try: weight = float(wt)
        except: pass

    # Reactions with basic SOC-level deduplication
    raw_rxns = patient.get("reaction", [])
    unique_rxns = {}
    for r in raw_rxns:
        term = r.get("reactionmeddrapt")
        if term:
            # Simple deduplication: take first occurrence of a term
            # (In a full implementation, this would map to MedDRA SOC codes)
            term_clean = term.lower().strip()
            if term_clean not in unique_rxns:
                unique_rxns[term_clean] = str(r.get("reactionoutcome", "6"))
                
    reactions = [{"name": k, "outcome": v} for k, v in unique_rxns.items()]

    outcomes = [r["outcome"] for r in reactions]
    is_fatal = "5" in outcomes
    is_serious = str(raw.get("serious", "2")) == "1"

    drugs = []
    for d in patient.get("drug", []):
        brand = d.get("medicinalproduct", "")
        openfda = d.get("openfda", {})
        generic_names = openfda.get("generic_name", [])
        name = (generic_names[0] if generic_names else brand).strip()
        drug_class = (openfda.get("pharm_class_epc") or ["unknown"])[0] if openfda else "unknown"
        drugs.append({
            "name": name,
            "indication": d.get("drugindication", "").lower(),
            "role": str(d.get("drugcharacterization", "1")),
            "drug_class": drug_class,
        })

    if not reactions:
        return None

    # Detect disease from indication text or drug names
    disease = _detect_disease_from_drugs(drugs)
    if not disease:
        for drug in drugs:
            disease = _detect_disease_from_text(drug.get("indication", ""))
            if disease:
                break

    return {
        "age": min(max(age, 18.0), 90.0),
        "sex": sex,
        "weight": weight,
        "reactions": reactions,
        "drugs": drugs,
        "is_fatal": is_fatal,
        "is_serious": is_serious,
        "n_reactions": len(reactions),
        "disease": disease,
    }


# ---------------------------------------------------------------------------
# HuggingFace Drug Reviews fetcher
# ---------------------------------------------------------------------------

def fetch_hf_drug_reviews(
    condition: str = "type2_diabetes",
    n_records: int = 500,
    cache_db: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch drug reviews from the UCI Drug Reviews dataset via HuggingFace
    Datasets Server API (no API key needed).
    Returns normalised records: drugName, condition, rating, review, usefulCount.
    """
    if cache_db:
        cached = _load_hf_cache(cache_db, condition, n_records)
        if cached:
            return cached

    condition_kws = DISEASE_KEYWORDS.get(condition, [condition.replace("_", " ")])
    print(f"[RealDataLoader] Fetching HF drug reviews for '{condition}'...")

    per_page = 100
    offset = 0
    collected: List[Dict] = []

    # We scan batches until we have enough relevant records or exhaust the dataset
    max_scanned = n_records * 10  # scan up to 10x to find enough matches
    scanned = 0

    while len(collected) < n_records and scanned < max_scanned:
        params = {
            "dataset": HF_DRUG_REVIEWS_DATASET,
            "config": "default",
            "split": "train",
            "offset": offset,
            "length": per_page,
        }
        try:
            resp = requests.get(HF_ROWS_API, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            rows = data.get("rows", [])
            if not rows:
                break
            for row_wrap in rows:
                row = row_wrap.get("row", {})
                cond_text = str(row.get("condition", "")).lower()
                drug_name = str(row.get("drugName", ""))
                if any(kw in cond_text for kw in condition_kws):
                    collected.append({
                        "drugName": drug_name,
                        "condition": cond_text,
                        "rating": float(row.get("rating", 5.0)),
                        "review": str(row.get("review", "")),
                        "usefulCount": int(row.get("usefulCount", 0)),
                        "disease": condition,
                    })
                scanned += 1
        except Exception as exc:
            print(f"[RealDataLoader] HF API error at offset {offset}: {exc}")
            break
        offset += per_page
        time.sleep(0.1)

    result = collected[:n_records]
    if cache_db and result:
        _save_hf_cache(cache_db, condition, result)

    print(f"[RealDataLoader] Got {len(result)} HF reviews for '{condition}'.")
    return result

# ---------------------------------------------------------------------------
# ClinicalTrials.gov fetcher
# ---------------------------------------------------------------------------

def fetch_clinical_trials(
    condition: str = "nsclc",
    n_records: int = 20,
) -> List[Dict[str, Any]]:
    """
    Fetch study data from ClinicalTrials.gov API v2.
    Extracts SAE frequencies and demographics to ground-truth our AE rates.
    """
    search_terms = {
        "type2_diabetes": "Type 2 Diabetes",
        "hypertension":   "Hypertension",
        "nsclc":          "Non-Small Cell Lung Cancer",
    }
    query = search_terms.get(condition, condition.replace("_", " "))
    print(f"[RealDataLoader] Fetching ClinicalTrials.gov studies for '{condition}'...")

    params = {
        "query.cond": query,
        "filter.overallStatus": "COMPLETED",
        "fields": "NCTId,EligibilityModule,ResultsSection",
        "pageSize": min(n_records, 100),
    }

    collected = []
    try:
        resp = requests.get(CT_GOV_API, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        studies = data.get("studies", [])
        
        for study in studies:
            protocol = study.get("protocolSection", {})
            results = study.get("resultsSection", {})
            
            # Eligibility
            eligibility = protocol.get("eligibilityModule", {})
            min_age = eligibility.get("minimumAge", "18 Years")
            gender = eligibility.get("sex", "ALL")
            
            # Adverse Events
            ae_module = results.get("adverseEventsModule", {})
            sae_groups = ae_module.get("seriousEvents", [])
            total_affected = 0
            total_at_risk = 0
            
            for group in sae_groups:
                for event in group.get("assessmentGroups", []):
                    # ClinicalTrials API structure is deeply nested
                    # We approximate by summing across arms
                    try:
                        affected = int(event.get("numAffected", 0))
                        at_risk = int(event.get("numAtRisk", 1))
                        total_affected += affected
                        total_at_risk += at_risk
                    except:
                        pass
                        
            sae_rate = (total_affected / total_at_risk) if total_at_risk > 0 else None
            
            if sae_rate is not None:
                collected.append({
                    "nct_id": protocol.get("identificationModule", {}).get("nctId", "UNKNOWN"),
                    "min_age": min_age,
                    "gender_restriction": gender,
                    "sae_rate": sae_rate
                })
    except Exception as exc:
        print(f"[RealDataLoader] CT.gov API error: {exc}")

    print(f"[RealDataLoader] Got {len(collected)} CT.gov studies with SAE data.")
    return collected

# ---------------------------------------------------------------------------
# Priors computation
# ---------------------------------------------------------------------------

def build_disease_priors(
    fda_records: List[Dict],
    hf_reviews: List[Dict],
    condition: str,
    ct_trials: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Aggregate real data into calibrated disease profile priors for the
    Clinical Trial Simulator. Returns a dict compatible with the disease_profiles
    config format.
    """
    if ct_trials is None:
        ct_trials = []
        
    # Start with evidence-based defaults
    defaults: Dict[str, Dict[str, Any]] = {
        "type2_diabetes": {
            "baseline_response": 0.57, "toxicity_sensitivity": 0.42,
            "fatality_floor": 0.001,   "major_threshold": 0.58,
            "fatal_threshold": 0.83,   "mean_age": 60.0,
            "pct_female": 0.50,        "mean_weight": 85.0,
        },
        "hypertension": {
            "baseline_response": 0.62, "toxicity_sensitivity": 0.36,
            "fatality_floor": 0.0006,  "major_threshold": 0.55,
            "fatal_threshold": 0.80,   "mean_age": 58.0,
            "pct_female": 0.48,        "mean_weight": 83.0,
        },
        "nsclc": {
            "baseline_response": 0.41, "toxicity_sensitivity": 0.54,
            "fatality_floor": 0.0025,  "major_threshold": 0.62,
            "fatal_threshold": 0.86,   "mean_age": 65.0,
            "pct_female": 0.42,        "mean_weight": 72.0,
        },
    }

    prior = dict(defaults.get(condition, defaults["type2_diabetes"]))
    prior["source_fda_n"] = 0
    prior["source_hf_n"] = 0
    prior["source_ct_n"] = len(ct_trials)
    prior["top_adverse_reactions"] = {}
    prior["drug_class_composition"] = {"a": 0.0, "b": 0.0, "c": 0.0}
    prior["mean_rating"] = 5.5

    # ---- Aggregate FDA records ----
    n_fatal = 0
    n_serious = 0
    ages: List[float] = []
    weights: List[float] = []
    female_count = 0
    reaction_counts: Dict[str, int] = {}
    comp_votes: Dict[str, int] = {"a": 0, "b": 0, "c": 0}

    for rec in fda_records:
        if rec.get("disease") != condition and rec.get("disease") is not None:
            continue
        prior["source_fda_n"] += 1
        if rec["is_fatal"]:   n_fatal += 1
        if rec["is_serious"]: n_serious += 1
        ages.append(rec["age"])
        weights.append(rec["weight"])
        if rec["sex"] == "F": female_count += 1

        for rxn in rec.get("reactions", []):
            name = rxn["name"]
            if name:
                reaction_counts[name] = reaction_counts.get(name, 0) + 1

        for drug in rec.get("drugs", []):
            info = _get_drug_info(drug["name"])
            if info and info["disease"] == condition:
                comp_votes[info["comp"]] = comp_votes.get(info["comp"], 0) + 1

    n_fda = prior["source_fda_n"]
    if n_fda > 0:
        # Update demographic priors with real data (Bayesian blend: 30% weight to real)
        alpha = min(0.3, n_fda / 1000.0)
        prior["mean_age"]    = (1 - alpha) * prior["mean_age"]    + alpha * (sum(ages) / n_fda)
        prior["mean_weight"] = (1 - alpha) * prior["mean_weight"] + alpha * (sum(weights) / n_fda)
        prior["pct_female"]  = (1 - alpha) * prior["pct_female"]  + alpha * (female_count / n_fda)
        fatal_rate   = n_fatal / n_fda
        serious_rate = n_serious / n_fda
        prior["fatality_floor"]       = (1 - alpha) * prior["fatality_floor"]       + alpha * fatal_rate
        prior["toxicity_sensitivity"] = (1 - alpha) * prior["toxicity_sensitivity"] + alpha * serious_rate

        # Top-10 adverse reactions by frequency
        sorted_rxns = sorted(reaction_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        prior["top_adverse_reactions"] = {k: v for k, v in sorted_rxns}

        # Drug composition distribution
        total_votes = sum(comp_votes.values()) or 1
        prior["drug_class_composition"] = {c: v / total_votes for c, v in comp_votes.items()}

    # ---- Aggregate ClinicalTrials.gov studies ----
    if ct_trials:
        sae_rates = [t["sae_rate"] for t in ct_trials if t["sae_rate"] is not None]
        if sae_rates:
            mean_sae = sum(sae_rates) / len(sae_rates)
            # CT.gov SAE rates are highly structured and reliable ground truth.
            # We blend it heavily (50%) with the existing toxicity sensitivity.
            prior["toxicity_sensitivity"] = 0.5 * prior["toxicity_sensitivity"] + 0.5 * mean_sae

    # ---- Aggregate HuggingFace reviews ----
    ratings: List[float] = []
    for rev in hf_reviews:
        if rev.get("disease") == condition:
            ratings.append(rev["rating"])
            prior["source_hf_n"] += 1

    if ratings:
        prior["mean_rating"] = sum(ratings) / len(ratings)
        # High patient rating → better tolerance → lower toxicity sensitivity
        normalised_rating = (prior["mean_rating"] - 1) / 9  # 0-1
        prior["baseline_response"] = min(0.95, prior["baseline_response"] + normalised_rating * 0.05)

    return prior


# ---------------------------------------------------------------------------
# SQLite cache helpers
# ---------------------------------------------------------------------------

def _ensure_cache_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS fda_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            condition TEXT,
            record_json TEXT,
            fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS hf_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            condition TEXT,
            record_json TEXT,
            fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS real_priors (
            condition TEXT PRIMARY KEY,
            priors_json TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()


def _load_fda_cache(db_path: str, condition: str, limit: int) -> List[Dict]:
    try:
        with sqlite3.connect(db_path) as conn:
            _ensure_cache_tables(conn)
            rows = conn.execute(
                "SELECT record_json FROM fda_cache WHERE condition=? LIMIT ?",
                (condition, limit)
            ).fetchall()
            if rows:
                print(f"[RealDataLoader] Loaded {len(rows)} FDA records from cache.")
                return [json.loads(r[0]) for r in rows]
    except Exception:
        pass
    return []


def _save_fda_cache(db_path: str, condition: str, records: List[Dict]) -> None:
    try:
        with sqlite3.connect(db_path) as conn:
            _ensure_cache_tables(conn)
            conn.execute("DELETE FROM fda_cache WHERE condition=?", (condition,))
            conn.executemany(
                "INSERT INTO fda_cache (condition, record_json) VALUES (?, ?)",
                [(condition, json.dumps(r)) for r in records]
            )
            conn.commit()
    except Exception as e:
        print(f"[RealDataLoader] Cache save error: {e}")


def _load_hf_cache(db_path: str, condition: str, limit: int) -> List[Dict]:
    try:
        with sqlite3.connect(db_path) as conn:
            _ensure_cache_tables(conn)
            rows = conn.execute(
                "SELECT record_json FROM hf_cache WHERE condition=? LIMIT ?",
                (condition, limit)
            ).fetchall()
            if rows:
                print(f"[RealDataLoader] Loaded {len(rows)} HF reviews from cache.")
                return [json.loads(r[0]) for r in rows]
    except Exception:
        pass
    return []


def _save_hf_cache(db_path: str, condition: str, records: List[Dict]) -> None:
    try:
        with sqlite3.connect(db_path) as conn:
            _ensure_cache_tables(conn)
            conn.execute("DELETE FROM hf_cache WHERE condition=?", (condition,))
            conn.executemany(
                "INSERT INTO hf_cache (condition, record_json) VALUES (?, ?)",
                [(condition, json.dumps(r)) for r in records]
            )
            conn.commit()
    except Exception as e:
        print(f"[RealDataLoader] HF cache save error: {e}")


def save_priors_to_cache(db_path: str, condition: str, priors: Dict) -> None:
    try:
        with sqlite3.connect(db_path) as conn:
            _ensure_cache_tables(conn)
            conn.execute(
                "INSERT OR REPLACE INTO real_priors (condition, priors_json) VALUES (?, ?)",
                (condition, json.dumps(priors))
            )
            conn.commit()
    except Exception as e:
        print(f"[RealDataLoader] Priors cache save error: {e}")


def load_priors_from_cache(db_path: str, condition: str) -> Optional[Dict]:
    try:
        with sqlite3.connect(db_path) as conn:
            _ensure_cache_tables(conn)
            row = conn.execute(
                "SELECT priors_json FROM real_priors WHERE condition=?",
                (condition,)
            ).fetchone()
            if row:
                return json.loads(row[0])
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# High-level convenience function
# ---------------------------------------------------------------------------

def fetch_and_build_priors(
    condition: str = "type2_diabetes",
    n_fda: int = 300,
    n_hf: int = 200,
    cache_db: str = "artifacts/trial_data.db",
) -> Dict[str, Any]:
    """
    Full pipeline: fetch from both APIs, aggregate into priors, cache results.
    Returns a disease-profile dict ready for injection into TrialConfig.
    """
    # Check cache first
    cached = load_priors_from_cache(cache_db, condition)
    if cached:
        print(f"[RealDataLoader] Using cached priors for '{condition}'.")
        return cached

    fda_recs  = fetch_fda_adverse_events(condition, n_records=n_fda,  cache_db=cache_db)
    hf_revs   = fetch_hf_drug_reviews(condition,    n_records=n_hf,   cache_db=cache_db)
    ct_trials = fetch_clinical_trials(condition,    n_records=20)
    priors    = build_disease_priors(fda_recs, hf_revs, condition, ct_trials)

    save_priors_to_cache(cache_db, condition, priors)
    return priors
