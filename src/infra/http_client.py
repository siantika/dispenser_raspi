import requests


class HttpClient:
    """ Pakau global/settings untuk argument """
    def __init__(self, base_url: str, timeout: int = 5):
        self.base_url = base_url
        self.session = requests.Session()
        self.timeout = timeout

    def post(self, path: str, json: dict):
        url = f"{self.base_url}{path}"
        resp = self.session.post(url, json=json, timeout=self.timeout)
        resp.raise_for_status()
        return resp

    def get(self, path: str, params: dict = None):
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp

    def close(self):
        """Close underlying session when application shut down"""
        self.session.close()
