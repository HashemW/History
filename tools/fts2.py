import json, re, sys, urllib.parse, urllib.request, concurrent.futures as cf
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.loads(r.read().decode('utf-8', 'replace'))
def fts(q, n=40):
    u = 'https://archive.org/services/search/beta/page_production/?service_backend=fts&hits_per_page=%d&user_query=' % n + urllib.parse.quote(q)
    hits = get(u).get('response', {}).get('body', {}).get('hits', {}).get('hits', [])
    out = []
    for h in hits:
        f = h.get('fields', {}); hl = (h.get('highlight') or {}).get('text', [''])
        out.append((f.get('identifier'), str(f.get('title'))[:60], f.get('year') or '', re.sub(r'\s+', ' ', str(hl[0] if hl else ''))[:120]))
    return out
def status(i):
    try:
        md = get('https://archive.org/metadata/' + i).get('metadata', {}); c = md.get('collection', []); c = [c] if isinstance(c, str) else c
        if 'inlibrary' in c: return 'BORROW'
        if md.get('access-restricted-item') in ('true', True): return 'restr'
        return 'PUBLIC[' + ','.join(c)[:40] + ']'
    except Exception as e:
        return 'ERR'
QUERIES = sys.argv[1:]
with cf.ThreadPoolExecutor(6) as ex:
    res = list(ex.map(lambda q: (q, fts(q)), QUERIES))
ids = sorted({h[0] for _, hs in res for h in hs})
with cf.ThreadPoolExecutor(16) as ex:
    S = dict(zip(ids, ex.map(status, ids)))
for q, hs in res:
    print('==', q)
    for h in hs:
        if S[h[0]] != 'restr':
            print('   ', S[h[0]], '|', h[0], '|', h[1], '|', h[2], '|', h[3])
