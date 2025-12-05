import httpx


class AsyncHttpClient:
    def __init__(self, base_url: str, timeout: int = 5):
        self.base_url = base_url
        self.session = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def get(self, path: str, params: dict = None):
        resp = await self.session.get(path, params=params)
        resp.raise_for_status()
        return resp

    async def post(self, path: str, json: dict):
        resp = await self.session.post(path, json=json)
        resp.raise_for_status()
        return resp

    async def close(self):
        await self.session.aclose()
