from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote
import json
from fastapi.testclient import TestClient
from backend.app.main import app
root=Path('frontend/out')
class Assets(HTMLParser):
    def __init__(self):super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='script' and a.get('src'):self.urls.append(a['src'])
        if tag=='link' and a.get('rel') in ['stylesheet','preload','icon','modulepreload'] and a.get('href'):self.urls.append(a['href'])
        if tag=='img' and a.get('src'):self.urls.append(a['src'])
urls=set();pages=[]
for html in root.rglob('*.html'):
    p=Assets();p.feed(html.read_text());urls.update(p.urls);pages.append(str(html.relative_to(root)))
remote=[u for u in urls if urlparse(u).scheme in ['http','https']]
missing=[u for u in urls if not urlparse(u).scheme and not (root/unquote(urlparse(u).path).lstrip('/')).is_file()]
client=TestClient(app)
responses={u:client.get(u).status_code for u in urls if u.startswith('/')}
result={'html_pages':pages,'asset_count':len(urls),'remote_assets':remote,'missing_assets':missing,'served_asset_status':responses,'passed':not remote and not missing and all(v==200 for v in responses.values()),'scope':'Static exported HTML assets verified in process; no external network was used. Does not simulate a physically disconnected laptop.'}
Path('artifacts/qa/offline_assets.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:result[k] for k in ['asset_count','remote_assets','missing_assets','passed']}))
assert result['passed']
