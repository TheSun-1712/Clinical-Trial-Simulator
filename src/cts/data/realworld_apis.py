import os
import json
import requests
from typing import List, Dict, Any

# Helper to fetch data from ClinicalTrials.gov
def fetch_clinical_trials(disease: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """Return a list of trial summaries for the given disease.
    Uses the public ClinicalTrials.gov API (no key required).
    """
    # Encode the disease name for simple query
    query = disease.replace(' ', '+')
    url = (
        f"https://clinicaltrials.gov/api/query/study_fields"
        f"?expr={query}&fields=NCTId,Title,Phase,Enrollment,LocationCountry,StartDate,CompletionDate,ResultsFirstPosted,OverallStatus"
        f"&min_rnk=1&max_rnk={max_results}&fmt=json"
    )
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        studies = data.get('StudyFieldsResponse', {}).get('StudyFields', [])
        results = []
        for s in studies:
            results.append({
                "nct_id": s.get('NCTId', [''])[0],
                "title": s.get('Title', [''])[0],
                "phase": s.get('Phase', [''])[0],
                "enrollment": s.get('Enrollment', [''])[0],
                "country": s.get('LocationCountry', [''])[0],
                "status": s.get('OverallStatus', [''])[0],
                "start_date": s.get('StartDate', [''])[0],
                "completion_date": s.get('CompletionDate', [''])[0],
                "results_posted": s.get('ResultsFirstPosted', [''])[0],
            })
        return results
    except Exception as e:
        print(f"ClinicalTrials.gov fetch error: {e}")
        return []

# Helper to fetch adverse events from OpenFDA for a given drug name
def fetch_adverse_events(drug_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Query OpenFDA drug event endpoint for recent adverse event reports.
    Returns a list of dictionaries with patient outcome details.
    """
    base = "https://api.fda.gov/drug/event.json"
    params = {
        "search": f'patient.drug.medicinalproduct:"{drug_name}"',
        "limit": limit,
    }
    try:
        resp = requests.get(base, params=params, timeout=10)
        data = resp.json()
        results = []
        for r in data.get('results', []):
            results.append({
                "safety_report_id": r.get('safetyreportid'),
                "serious": r.get('serious'),
                "outcome": r.get('patient', {}).get('reaction', []),
                "date": r.get('receiptdate'),
            })
        return results
    except Exception as e:
        print(f"OpenFDA fetch error: {e}")
        return []

# Helper to fetch PubMed / Europe PMC literature
def fetch_recent_literature(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search Europe PMC for the latest papers matching the query.
    Returns title, DOI, journal, and first author.
    """
    api_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {
        "query": query,
        "resulttype": "core",
        "pageSize": max_results,
        "format": "json",
    }
    try:
        resp = requests.get(api_url, params=params, timeout=10)
        data = resp.json()
        entries = data.get('resultList', {}).get('result', [])
        out = []
        for e in entries:
            out.append({
                "title": e.get('title'),
                "doi": e.get('doi'),
                "journal": e.get('journalTitle'),
                "first_author": e.get('authorString'),
                "pub_year": e.get('firstPublicationDate'),
                "pmcid": e.get('pmcid'),
                "url": e.get('url'),
            })
        return out
    except Exception as e:
        print(f"Europe PMC fetch error: {e}")
        return []
