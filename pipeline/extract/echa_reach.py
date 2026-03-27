"""
ECHA REACH API Client for Hazard Data

Fetches hazard classifications from ECHA REACH database using CASRN.

NOTE: ECHA REACH API requires registration and API keys for programmatic access.
This implementation provides a framework that can be activated once proper credentials are obtained.

Alternative approaches:
1. Download ECHA REACH datasets from https://echa.europa.eu/en/information-on-chemicals
2. Use local CSV/Parquet files with pre-downloaded hazard data
3. Use alternative sources like ChemSpider or paid hazard databases

For production use, register at ECHA for API access.
"""

import requests
import pandas as pd
import time
from pathlib import Path
from typing import Optional, Dict, Any
import json


class ECHARearchAPI:
    """
    Client for ECHA REACH API to fetch chemical hazard data.

    IMPORTANT: This requires ECHA API registration and credentials.
    Current implementation returns mock data for testing.
    """

    BASE_URL = "https://echa.europa.eu/chem/api"

    def __init__(self, api_key: Optional[str] = None):
        self.session = requests.Session()
        self.api_key = api_key
        headers = {
            'User-Agent': 'HairGlueProject/1.0 (research@hairglue.org)',
            'Accept': 'application/json'
        }
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        self.session.headers.update(headers)

    def search_by_casrn(self, casrn: str) -> Optional[Dict[str, Any]]:
        """
        Search for a chemical by CASRN in ECHA REACH database.

        Returns chemical data including hazard classifications if found.
        """
        if not casrn or pd.isna(casrn):
            return None

        # Clean CASRN
        casrn = str(casrn).strip()

        # For now, return mock data since API requires registration
        # TODO: Replace with actual API call once credentials are obtained
        return self._get_mock_hazard_data(casrn)

        # Actual API call (uncomment when API access is available):
        """
        try:
            url = f"{self.BASE_URL}/search"
            params = {
                'cas': casrn,
                'format': 'json'
            }

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if data and len(data) > 0:
                substance = data[0]
                return self._extract_hazard_data(substance)

        except requests.RequestException as e:
            print(f"API request failed for CASRN {casrn}: {e}")
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed for CASRN {casrn}: {e}")

        return None
        """

    def _get_mock_hazard_data(self, casrn: str) -> Dict[str, Any]:
        """
        Return mock hazard data for testing purposes.
        Replace with actual API extraction when available.
        """
        # Mock data for common chemicals
        mock_data = {
            '7732-18-5': {  # Water
                'casrn': '7732-18-5',
                'ec_number': '231-791-2',
                'substance_name': 'Water',
                'hazard_classes': '',
                'hazard_statements': '',
                'precautionary_statements': '',
                'signal_word': None,
                'ghs_classes': '',
                'data_source': 'ECHA_REACH_MOCK',
                'last_updated': pd.Timestamp.now().isoformat()
            },
            '64-17-5': {  # Ethanol
                'casrn': '64-17-5',
                'ec_number': '200-578-6',
                'substance_name': 'Ethanol',
                'hazard_classes': 'Flammable liquids',
                'hazard_statements': 'H225',
                'precautionary_statements': 'P210,P233,P240,P241,P242,P243',
                'signal_word': 'Danger',
                'ghs_classes': 'Flammable liquid Category 2',
                'data_source': 'ECHA_REACH_MOCK',
                'last_updated': pd.Timestamp.now().isoformat()
            }
        }

        return mock_data.get(casrn, {
            'casrn': casrn,
            'ec_number': None,
            'substance_name': None,
            'hazard_classes': None,
            'hazard_statements': None,
            'precautionary_statements': None,
            'signal_word': None,
            'ghs_classes': None,
            'data_source': 'ECHA_REACH_NOT_FOUND',
            'last_updated': pd.Timestamp.now().isoformat()
        })

    def _extract_hazard_data(self, substance: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract hazard classification data from ECHA substance record.
        This is the actual extraction logic for when API access is available.
        """
        hazard_data = {
            'casrn': substance.get('casNumber'),
            'ec_number': substance.get('ecNumber'),
            'substance_name': substance.get('name'),
            'hazard_classes': [],
            'hazard_statements': [],
            'precautionary_statements': [],
            'signal_word': None,
            'ghs_classes': [],
            'data_source': 'ECHA_REACH',
            'last_updated': pd.Timestamp.now().isoformat()
        }

        # Extract hazard classifications from API response
        # This will need to be adjusted based on actual API response structure
        classifications = substance.get('hazardClassifications', [])

        for classification in classifications:
            if classification.get('classificationType') == 'GHS':
                hazard_class = classification.get('hazardClass')
                if hazard_class:
                    hazard_data['ghs_classes'].append(hazard_class)

                statements = classification.get('hazardStatements', [])
                for stmt in statements:
                    if stmt.get('code'):
                        hazard_data['hazard_statements'].append(stmt['code'])

                prec_statements = classification.get('precautionaryStatements', [])
                for stmt in prec_statements:
                    if stmt.get('code'):
                        hazard_data['precautionary_statements'].append(stmt['code'])

                if classification.get('signalWord') and not hazard_data['signal_word']:
                    hazard_data['signal_word'] = classification['signalWord']

        # Convert lists to strings
        hazard_data['ghs_classes'] = ','.join(hazard_data['ghs_classes'])
        hazard_data['hazard_statements'] = ','.join(hazard_data['hazard_statements'])
        hazard_data['precautionary_statements'] = ','.join(hazard_data['precautionary_statements'])

        return hazard_data

    def fetch_hazards_batch(self, casrns: list, batch_size: int = 10, delay: float = 1.0) -> pd.DataFrame:
        """
        Fetch hazard data for a batch of CASRNs with rate limiting.
        """
        results = []

        for i in range(0, len(casrns), batch_size):
            batch = casrns[i:i + batch_size]

            for casrn in batch:
                print(f"Fetching hazard data for CASRN: {casrn}")
                hazard_data = self.search_by_casrn(casrn)
                results.append(hazard_data)

                # Rate limiting
                time.sleep(delay)

        return pd.DataFrame(results)


def load_echa_hazards_from_file(file_path: str) -> pd.DataFrame:
    """
    Load hazard data from a local ECHA data file (CSV/Parquet).

    This is an alternative to API access when bulk data is downloaded.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"ECHA data file not found: {file_path}")

    if path.suffix == '.csv':
        df = pd.read_csv(path)
    elif path.suffix == '.parquet':
        df = pd.read_parquet(path)
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")

    # Standardize column names
    column_mapping = {
        'CAS Number': 'casrn',
        'EC Number': 'ec_number',
        'Substance Name': 'substance_name',
        'GHS Hazard Classes': 'ghs_classes',
        'Hazard Statements': 'hazard_statements',
        'Precautionary Statements': 'precautionary_statements',
        'Signal Word': 'signal_word'
    }

    df = df.rename(columns=column_mapping)

    # Add metadata
    df['data_source'] = 'ECHA_REACH_FILE'
    df['last_updated'] = pd.Timestamp.now().isoformat()

    return df[['casrn', 'ec_number', 'substance_name', 'ghs_classes',
               'hazard_statements', 'precautionary_statements', 'signal_word',
               'data_source', 'last_updated']]


def test_echa_api():
    """Test the ECHA API with a known CASRN."""
    api = ECHARearchAPI()

    # Test with water (should have minimal hazards)
    test_casrn = "7732-18-5"
    result = api.search_by_casrn(test_casrn)

    if result:
        print(f"Found data for {test_casrn}:")
        print(json.dumps(result, indent=2))
    else:
        print(f"No data found for {test_casrn}")


if __name__ == "__main__":
    test_echa_api()