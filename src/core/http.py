import requests
class HttpError(RuntimeError): pass
def request_json(method, url, **kwargs):
    r=requests.request(method,url,timeout=30,**kwargs)
    if r.status_code>=400: raise HttpError(f'{method} {url} failed: {r.status_code} {r.text[:500]}')
    return r.json() if r.text else {}
