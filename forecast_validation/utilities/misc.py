from typing import Union
import os
import urllib.request

def fetch_url(url: str, to_path: Union[str, os.PathLike]) -> str:
    urllib.request.urlretrieve(url, to_path)
    return to_path
