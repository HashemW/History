import json, sys, urllib.parse, urllib.request, concurrent.futures as cf
UA = {'User-Agent': 'Mozilla/5.0 (study-repo builder)'}
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return json.loads(r.read().decode('utf-8'))
Q = {
 'OutOfGarden2': 'title:("out of the garden") AND title:(women)',
 'AlterISBN': 'identifier:(isbn_9780465004270)',
 'MilgromLev': 'title:("leviticus 1-16") AND creator:(milgrom)',
 'ABD1': 'title:("anchor bible dictionary") AND (volume:1 OR title:(A-C))',
 'Gutenberg Gilg': 'title:("old babylonian version of the gilgamesh")',
 'OutOfGarden': 'title:("out of the garden") AND (creator:(buchmann) OR creator:(spiegel))',
 'Alter': 'title:("art of biblical narrative")',
 'HebBibLitCrit': 'title:("hebrew bible in literary criticism")',
 'Milgrom': 'title:("studies in cultic theology") OR (title:("cult and conscience") AND creator:(milgrom))',
 'ABD': 'title:("anchor bible dictionary")',
 'Reis': 'title:("reading the lines") AND creator:(reis)',
 'Sternberg': 'title:("poetics of biblical narrative")',
 'EncRel': 'title:("encyclopedia of religion") AND creator:(eliade)',
 'Hayes': 'title:("introduction to the bible") AND creator:(hayes)',
 'King7Tablets': 'title:("seven tablets of creation")',
 'Gilgamish': 'title:("epic of gilgamish") AND creator:(thompson)',
}
def search(item):
    k, q = item
    url = ('https://archive.org/advancedsearch.php?q=' + urllib.parse.quote(q + ' AND mediatype:texts') +
           '&fl[]=identifier&fl[]=title&fl[]=year&fl[]=volume&rows=12&output=json')
    try:
        return k, get(url)['response']['docs']
    except Exception as e:
        return k, [{'identifier': 'ERR ' + str(e)}]
def meta(ident):
    try:
        m = get('https://archive.org/metadata/' + ident).get('metadata', {})
        c = m.get('collection', []); c = [c] if isinstance(c, str) else c
        if 'inlibrary' in c: st = 'BORROWABLE'
        elif m.get('access-restricted-item') in ('true', True): st = 'restricted(print-disabled only)' if 'printdisabled' in c else 'restricted'
        else: st = 'PUBLIC full view'
        return ident, st, m.get('date', ''), m.get('volume', ''), (m.get('publisher') or '')[:40] if isinstance(m.get('publisher'), str) else str(m.get('publisher'))[:40], ','.join(c)[:70]
    except Exception as e:
        return ident, 'ERR ' + str(e), '', '', '', ''
with cf.ThreadPoolExecutor(10) as ex:
    results = list(ex.map(search, Q.items()))
ids = sorted({d['identifier'] for _, docs in results for d in docs if not d['identifier'].startswith('ERR')})
with cf.ThreadPoolExecutor(16) as ex:
    M = {r[0]: r for r in ex.map(meta, ids)}
for k, docs in results:
    print('==', k)
    for d in docs:
        i = d['identifier']; m = M.get(i, (i, '?', '', '', '', ''))
        print(f"   {m[1]:<34} {i:<55} | {str(d.get('title'))[:60]} | {m[2]} vol={m[3]} | {m[4]} | {m[5]}")
