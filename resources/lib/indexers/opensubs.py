import requests

class OpenSubsApi:

    def __init__(self):
        self._base_url = ' https://rest.opensubtitles.org/search'
        self._headers = {'User-Agent': "TemporaryUserAgent"}

    def _get(self, endpoint):
        url = self._base_url + endpoint
        return requests.get(url, headers=self._headers).json()

    def search(self, imdb):
        endpoint = '/sublanguageid-en/query-{}'.format(imdb)
        return self._get(endpoint)
        pass
