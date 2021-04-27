from saucenao_api.saucenao_api import SauceNao, SauceResponse
from typing import Optional
from saucenao_api.errors import BadKeyError, BadFileSizeError, LongLimitReachedError, ShortLimitReachedError, UnknownApiError
import requests
from saucenao_api.params import DB, Hide, BgColor


class newSauceNao(SauceNao):
    def __init__(self,
                 api_key:  Optional[str] = None,
                 *,
                 testmode: int = 0,
                 dbmask:   Optional[int] = None,
                 dbmaski:  Optional[int] = None,
                 db:       int = DB.ALL,
                 numres:   int = 6,
                 frame:    int = 1,
                 hide:     int = Hide.NONE,
                 bgcolor:  int = BgColor.NONE,
                 proxies:  dict
                 ) -> None:
        super().__init__(api_key=api_key, testmode=testmode, dbmask=dbmask,
                         dbmaski=dbmaski, db=db, numres=numres, frame=frame, hide=hide, bgcolor=bgcolor)
        self.proxies = proxies

    def _search(self, params, files=None):
        resp = requests.post(self.SAUCENAO_URL, params=params,
                             files=files, proxies=self.proxies)
        status_code = resp.status_code

        if status_code == 200:
            raw = self._verify_response(resp, params)
            return SauceResponse(raw)

        # Taken from https://saucenao.com/tools/examples/api/identify_images_v1.1.py
        # Actually server returns 200 and user_id=0 if key is bad
        elif status_code == 403:
            raise BadKeyError('Invalid API key')

        elif status_code == 413:
            raise BadFileSizeError('File is too large')

        elif status_code == 429:
            if 'Daily' in resp.json()['header']['message']:
                raise LongLimitReachedError('24 hours limit reached')
            raise ShortLimitReachedError('30 seconds limit reached')

        raise UnknownApiError(f'Server returned status code {status_code}')
