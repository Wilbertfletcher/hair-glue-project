"""
ChemSpider API Client for Chemical Data

Fetches chemical information from ChemSpider database using various search methods.
"""

import requests
import pandas as pd
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import json


class ChemSpiderAPI:
    """
    Client for ChemSpider API to fetch chemical data.

    ChemSpider provides access to chemical structures, properties, and identifiers.
    API documentation: https://developer.rsc.org/apis
    """

    BASE_URL = "https://api.rsc.org/compounds/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ChemSpider API client.

        Args:
            api_key: ChemSpider 
              (required for production use)
        """
        self.session = requests.Session()
        self.api_key = api_key
        headers = {
            'User-Agent': 'HairGlueProject/1.0 (research@hairglue.org)',
            'Accept': 'application/json'
        }
        if api_key:
            headers['apikey'] = api_key
        self.session.headers.update(headers)

    def search_by_name(self, name: str) -> Optional[List[Dict[str, Any]]]:
        """
        Search for compounds by name.

        Returns list of matching compounds with basic information.
        """
        if not name or pd.isna(name):
            return None

        name = str(name).strip()

        try:
            # Step 1: Submit search query
            filter_url = f"{self.BASE_URL}/filter/name"
            filter_data = {'name': name}

            filter_response = self.session.post(filter_url, json=filter_data, timeout=30)
            filter_response.raise_for_status()

            query_data = filter_response.json()
            query_id = query_data.get('queryId')

            if not query_id:
                return None

            # Step 2: Get search results (compound IDs)
            time.sleep(1)  # Brief delay for processing
            results_url = f"{self.BASE_URL}/filter/{query_id}/results"
            results_response = self.session.get(results_url, timeout=30)
            results_response.raise_for_status()

            results_data = results_response.json()
            compound_ids = results_data.get('results', [])

            if not compound_ids:
                return None

            # Step 3: Get details for each compound (limit to first result for now)
            compounds = []
            for compound_id in compound_ids[:1]:  # Just get first match
                details = self.get_compound_details(compound_id)
                if details:
                    compounds.append(details)

            return compounds

        except requests.RequestException as e:
            print(f"API request failed for name '{name}': {e}")
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed for name '{name}': {e}")

        return None

    def search_by_casrn(self, casrn: str) -> Optional[Dict[str, Any]]:
        """
        Search for compounds by CASRN.

        Note: ChemSpider API requires registration at https://developer.rsc.org/
        """
        if not casrn or pd.isna(casrn):
            return None

        casrn = str(casrn).strip()

        # Use real API if key is available, otherwise fall back to mock data
        if self.api_key:
            try:
                results = self.search_by_name(casrn)
                if results and len(results) > 0:
                    compound_id = results[0].get('id')
                    if compound_id:
                        return self.get_compound_details(compound_id)
            except Exception as e:
                print(f"CASRN search failed for '{casrn}': {e}")
                # Fall back to mock data if API fails
                return self._get_mock_data(casrn)
        else:
            # No API key - use mock data
            return self._get_mock_data(casrn)

        return None

    def _get_mock_data(self, casrn: str) -> Dict[str, Any]:
        """
        Return mock ChemSpider data for testing purposes.
        """
        mock_data = {
            '7732-18-5': {  # Water
                'chemspider_id': 937,
                'smiles': 'O',
                'inchi': 'InChI=1S/H2O/h1H2',
                'inchikey': 'XLYOFNOQVPJJNP-UHFFFAOYSA-N',
                'molecular_formula': 'H2O',
                'molecular_weight': '18.015',
                'common_name': 'Water',
                'systematic_name': 'Water',
                'casrn': '7732-18-5',
                'pubchem_cid': '962',
                'data_source': 'CHEMSPIDER_MOCK',
                'last_updated': pd.Timestamp.now().isoformat()
            },
            '64-17-5': {  # Ethanol
                'chemspider_id': 682,
                'smiles': 'CCO',
                'inchi': 'InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3',
                'inchikey': 'LFQSCWFLJHTTHZ-UHFFFAOYSA-N',
                'molecular_formula': 'C2H6O',
                'molecular_weight': '46.069',
                'common_name': 'Ethanol',
                'systematic_name': 'Ethanol',
                'casrn': '64-17-5',
                'pubchem_cid': '702',
                'data_source': 'CHEMSPIDER_MOCK',
                'last_updated': pd.Timestamp.now().isoformat()
            }
        }

        return mock_data.get(casrn, {
            'casrn': casrn,
            'chemspider_id': None,
            'smiles': None,
            'inchi': None,
            'inchikey': None,
            'molecular_formula': None,
            'molecular_weight': None,
            'common_name': None,
            'systematic_name': None,
            'pubchem_cid': None,
            'data_source': 'CHEMSPIDER_NOT_FOUND',
            'last_updated': pd.Timestamp.now().isoformat()
        })

    def get_compound_details(self, compound_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific compound.

        Args:
            compound_id: ChemSpider compound ID

        Returns:
            Detailed compound data including identifiers, properties, etc.
        """
        try:
            url = f"{self.BASE_URL}/records/{compound_id}/details"

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()

            if data:
                return self._extract_compound_data(data)

        except requests.RequestException as e:
            print(f"API request failed for compound {compound_id}: {e}")
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed for compound {compound_id}: {e}")

        return None

    def _extract_compound_data(self, compound_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant chemical data from ChemSpider response.
        """
        extracted = {
            'chemspider_id': compound_data.get('id'),
            'smiles': None,
            'inchi': None,
            'inchikey': None,
            'molecular_formula': None,
            'molecular_weight': None,
            'common_name': compound_data.get('name'),
            'systematic_name': None,
            'casrn': None,
            'pubchem_cid': None,
            'data_source': 'CHEMSPIDER',
            'last_updated': pd.Timestamp.now().isoformat()
        }

        # Extract identifiers
        identifiers = compound_data.get('identifiers', [])
        for identifier in identifiers:
            id_type = identifier.get('identifierType')
            value = identifier.get('value')

            if id_type == 'SMILES':
                extracted['smiles'] = value
            elif id_type == 'InChI':
                extracted['inchi'] = value
            elif id_type == 'InChIKey':
                extracted['inchikey'] = value
            elif id_type == 'CAS':
                extracted['casrn'] = value
            elif id_type == 'PubChem':
                extracted['pubchem_cid'] = value

        # Extract names
        names = compound_data.get('names', [])
        for name_info in names:
            name_type = name_info.get('nameType')
            name_value = name_info.get('name')

            if name_type == 'Systematic':
                if not extracted['systematic_name']:
                    extracted['systematic_name'] = name_value
            elif name_type == 'Synonym' and not extracted['common_name']:
                extracted['common_name'] = name_value

        # Extract molecular properties
        properties = compound_data.get('properties', [])
        for prop in properties:
            prop_name = prop.get('name')
            prop_value = prop.get('value')

            if prop_name == 'Molecular Formula':
                extracted['molecular_formula'] = prop_value
            elif prop_name == 'Molecular Weight':
                extracted['molecular_weight'] = prop_value

        return extracted

    def search_hazards_by_casrn(self, casrn: str) -> Optional[Dict[str, Any]]:
        """
        Search for hazard information by CASRN.

        Note: ChemSpider may not have comprehensive hazard data.
        This is a placeholder for when hazard data becomes available.
        """
        # ChemSpider primarily provides chemical identifiers and structures
        # Hazard data might be available through related services
        # For now, return basic compound data
        return self.search_by_casrn(casrn)

    def fetch_batch(self, casrns: List[str], batch_size: int = 5, delay: float = 1.0) -> pd.DataFrame:
        """
        Fetch data for a batch of CASRNs with rate limiting.
        """
        results = []

        for i in range(0, len(casrns), batch_size):
            batch = casrns[i:i + batch_size]

            for casrn in batch:
                print(f"Fetching ChemSpider data for CASRN: {casrn}")
                data = self.search_by_casrn(casrn)

                if data:
                    results.append(data)
                else:
                    # Add empty record for not found
                    results.append({
                        'casrn': casrn,
                        'chemspider_id': None,
                        'smiles': None,
                        'inchi': None,
                        'inchikey': None,
                        'molecular_formula': None,
                        'molecular_weight': None,
                        'common_name': None,
                        'systematic_name': None,
                        'pubchem_cid': None,
                        'data_source': 'CHEMSPIDER_NOT_FOUND',
                        'last_updated': pd.Timestamp.now().isoformat()
                    })

                # Rate limiting
                time.sleep(delay)

        return pd.DataFrame(results)


def test_chemspider_api():
    """Test the ChemSpider API with a sample compound."""
    # Note: This will fail without API key, but shows the structure
    api = ChemSpiderAPI()

    # Test with water
    test_casrn = "7732-18-5"
    result = api.search_by_casrn(test_casrn)

    if result:
        print(f"Found ChemSpider data for {test_casrn}:")
        print(json.dumps(result, indent=2))
    else:
        print(f"No ChemSpider data found for {test_casrn}")
        print("Note: ChemSpider API requires registration and API key")


if __name__ == "__main__":
    test_chemspider_api()