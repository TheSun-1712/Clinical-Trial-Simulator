import os
from datetime import datetime, timezone

from cts.integrations.base import CachedAPIClient


class ClinicalTrialsGovClient(CachedAPIClient):
    def search_trials(self, disease: str, intervention: str) -> dict:
        key = f"{disease}_{intervention}"
        url = (
            "https://clinicaltrials.gov/api/v2/studies?"
            f"query.term={disease}+{intervention}&pageSize=10"
        )
        fixture = {
            "source": "fixture",
            "studies": [
                {
                    "protocolSection": {
                        "identificationModule": {"nctId": "NCT00000000"},
                        "designModule": {"phases": ["PHASE2"]},
                        "conditionsModule": {"conditions": [disease]},
                        "armsInterventionsModule": {"interventions": [{"name": intervention}]},
                        "eligibilityModule": {"eligibilityCriteria": "Synthetic fixture eligibility"},
                    }
                }
            ],
        }
        return self.get_json(url, "clinicaltrials_gov", key, fixture=fixture)


class OpenFDAClient(CachedAPIClient):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.api_key = os.getenv("OPENFDA_API_KEY")

    def drug_label(self, drug_name: str) -> dict:
        key = f"label_{drug_name}"
        url = f"https://api.fda.gov/drug/label.json?search=openfda.brand_name:{drug_name}&limit=1"
        if self.api_key:
            url += f"&api_key={self.api_key}"
        fixture = {
            "source": "fixture",
            "results": [
                {
                    "warnings": ["Synthetic warning text"],
                    "contraindications": ["Synthetic contraindication"],
                    "adverse_reactions": ["Synthetic reaction"],
                }
            ],
        }
        return self.get_json(url, "openfda", key, fixture=fixture)

    def drug_event(self, drug_name: str) -> dict:
        key = f"event_{drug_name}"
        url = f"https://api.fda.gov/drug/event.json?search=patient.drug.medicinalproduct:{drug_name}&limit=5"
        if self.api_key:
            url += f"&api_key={self.api_key}"
        fixture = {
            "source": "fixture",
            "meta": {"disclaimer": "FAERS reports do not establish causation."},
            "results": [
                {"seriousnesshospitalization": "1", "patient": {"reaction": [{"reactionmeddrapt": "Nausea"}]}}
            ],
        }
        return self.get_json(url, "openfda", key, fixture=fixture)


class PubMedClient(CachedAPIClient):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.api_key = os.getenv("NCBI_API_KEY")

    def search_literature(self, disease: str, intervention: str, endpoint: str) -> dict:
        key = f"{disease}_{intervention}_{endpoint}"
        query = f"{disease}+{intervention}+{endpoint}"
        url = (
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?"
            f"db=pubmed&term={query}&retmode=json"
        )
        if self.api_key:
            url += f"&api_key={self.api_key}"
        fixture = {
            "source": "fixture",
            "esearchresult": {"idlist": ["00000000"]},
        }
        return self.get_json(url, "pubmed", key, fixture=fixture)

    def fetch_summary(self, pmid: str) -> dict:
        key = f"summary_{pmid}"
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
        if self.api_key:
            url += f"&api_key={self.api_key}"
        fixture = {
            "source": "fixture",
            "result": {
                pmid: {
                    "title": "Synthetic evidence",
                    "pubdate": "2024-01-01",
                    "source": "Synthetic Journal",
                }
            },
        }
        return self.get_json(url, "pubmed_summary", key, fixture=fixture)


class PubChemClient(CachedAPIClient):
    def resolve_compound(self, compound_name: str) -> dict:
        key = compound_name
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{compound_name}/JSON"
        fixture = {
            "source": "fixture",
            "PC_Compounds": [
                {
                    "id": {"id": {"cid": 12345}},
                    "props": [
                        {"urn": {"label": "IUPAC Name"}, "value": {"sval": compound_name}},
                        {"urn": {"label": "SMILES"}, "value": {"sval": "C1=CC=CC=C1"}},
                    ],
                }
            ],
        }
        return self.get_json(url, "pubchem", key, fixture=fixture)


class ChEMBLClient(CachedAPIClient):
    def molecule_summary(self, molecule_name: str) -> dict:
        key = molecule_name
        url = f"https://www.ebi.ac.uk/chembl/api/data/molecule/search?q={molecule_name}&format=json"
        fixture = {
            "source": "fixture",
            "molecules": [
                {
                    "pref_name": molecule_name,
                    "molecule_hierarchy": {"molecule_chembl_id": "CHEMBL000"},
                    "molecule_mechanisms": [{"mechanism_of_action": "Synthetic action"}],
                }
            ],
        }
        return self.get_json(url, "chembl", key, fixture=fixture)


class RxNormClient(CachedAPIClient):
    def normalize_drug_name(self, drug_name: str) -> dict:
        key = drug_name
        url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={drug_name}"
        fixture = {
            "source": "fixture",
            "idGroup": {"name": drug_name, "rxnormId": ["12345"]},
        }
        return self.get_json(url, "rxnorm", key, fixture=fixture)


class NciEvsCtcaeClient(CachedAPIClient):
    def load_ctcae_terms(self) -> dict:
        key = "ctcae_v5"
        url = "https://evsexplore.semantics.cancer.gov/ctcae"
        fixture = {
            "source": "fixture",
            "loaded_at": datetime.now(timezone.utc).isoformat(),
            "terms": [
                {
                    "term": "Neutropenia",
                    "grades": {
                        "1": "Asymptomatic",
                        "2": "Moderate",
                        "3": "Severe",
                        "4": "Life-threatening",
                        "5": "Death",
                    },
                }
            ],
        }
        return self.get_json(url, "nci_evs", key, fixture=fixture)

