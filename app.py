import os, re, hashlib, time, threading
from urllib.parse import quote
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, jsonify, request, send_from_directory
import requests

def load_env(path='.env'):
	if not os.path.exists(path): return
	for line in open(path, encoding='utf-8'):
		line=line.strip()
		if not line or line.startswith('#') or '=' not in line: continue
		k,_,v=line.partition('=')
		os.environ.setdefault(k.strip(), v.strip())

load_env()
app = Flask(__name__, static_folder='static')

DEMO = [
 {"id":"kimbell-art-museum","title":"Kimbell Art Museum","architect":"Louis Kahn","location":"Fort Worth, USA","year":1972,"area":"11,148 m²","type":"Cultural","tags":["concrete","vaults","daylight","museum"],"image":"https://images.unsplash.com/photo-1564399579883-451a5d44ec08?auto=format&fit=crop&w=1200&q=80","counts":{"photos":12,"plans":4,"sections":3,"details":6}},
 {"id":"therme-vals","title":"Therme Vals","architect":"Peter Zumthor","location":"Vals, Switzerland","year":1996,"area":"3,200 m²","type":"Hospitality","tags":["stone","thermal baths","light","tectonics"],"image":"https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?auto=format&fit=crop&w=1200&q=80","counts":{"photos":18,"plans":5,"sections":4,"details":8}},
 {"id":"casa-gilardi","title":"Casa Gilardi","architect":"Luis Barragán","location":"Mexico City, Mexico","year":1976,"area":"600 m²","type":"Residential","tags":["color","courtyard","water","light"],"image":"https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=1200&q=80","counts":{"photos":14,"plans":3,"sections":2,"details":4}},
 {"id":"salk-institute","title":"Salk Institute","architect":"Louis Kahn","location":"La Jolla, USA","year":1965,"area":"29,000 m²","type":"Research","tags":["concrete","courtyard","structure","sea view"],"image":"https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1200&q=80","counts":{"photos":16,"plans":6,"sections":4,"details":7}},
 {"id":"farnsworth-house","title":"Farnsworth House","architect":"Ludwig Mies van der Rohe","location":"Plano, USA","year":1951,"area":"139 m²","type":"Residential","tags":["steel","glass","minimal","landscape"],"image":"https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80","counts":{"photos":20,"plans":2,"sections":2,"details":5}},
]

CACHE_TTL = float(os.getenv('SEARCH_CACHE_TTL', '300'))
CACHE_MAX = 200
RATE_LIMIT = int(os.getenv('SEARCH_RATE_LIMIT', '20'))
RATE_WINDOW = 60
_cache = OrderedDict()
_cache_lock = threading.Lock()
_rate = OrderedDict()
_rate_lock = threading.Lock()

def cache_get(key):
    with _cache_lock:
        entry = _cache.get(key)
        if entry and time.time() - entry[0] < CACHE_TTL:
            _cache.move_to_end(key)
            return entry[1]
        if entry: del _cache[key]
    return None

def cache_set(key, value):
    with _cache_lock:
        _cache[key] = (time.time(), value)
        _cache.move_to_end(key)
        while len(_cache) > CACHE_MAX:
            _cache.popitem(last=False)

def rate_limited(client):
    now = time.time()
    with _rate_lock:
        hits = [t for t in _rate.get(client, ()) if now - t < RATE_WINDOW]
        if len(hits) >= RATE_LIMIT:
            _rate[client] = hits
            return True
        hits.append(now)
        _rate[client] = hits
        while len(_rate) > 1000:
            _rate.popitem(last=False)
    return False

def client_ip():
    fwd = request.headers.get('X-Forwarded-For', '')
    return (fwd.split(',')[0].strip() if fwd else (request.remote_addr or 'unknown'))

def local_matches(q):
    ql = q.lower()
    toks = [t for t in re.split(r'[^a-z0-9]+', ql) if t]
    if not toks: return []
    scored = []
    for p in DEMO:
        hay = ' '.join([p['title'], p['architect'], p['location'], p['type'], ' '.join(p['tags'])]).lower()
        words = set(re.split(r'[^a-z0-9]+', hay))
        hits = sum(1 for t in toks if t in words)
        if ql in hay:
            score = 100 + len(toks)
        elif hits == len(toks):
            score = 50 + hits
        elif len(toks) >= 3 and hits >= -(-3 * len(toks) // 5):
            score = hits
        else:
            continue
        scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored]

def brave(endpoint, params):
    key=os.getenv('BRAVE_API_KEY')
    if not key: return None
    try:
        r=requests.get(f'https://api.search.brave.com/res/v1/{endpoint}',headers={'Accept':'application/json','X-Subscription-Token':key},params=params,timeout=15)
        r.raise_for_status(); return r.json()
    except requests.RequestException as e:
        app.logger.warning('Brave %s failed: %s', endpoint, e)
        return None

def classify(text):
    t=(text or '').lower()
    rules=[('plan',['plan','plans','floor plan','floor plans','site plan','site plans','ground floor','layout','layouts']),('section',['section','sections','cross section','cross sections','longitudinal','transverse']),('elevation',['elevation','elevations','facade','facades','façade','façades']),('detail',['detail','details','junction','junctions','construction detail','assembly','assemblies']),('photo',['photograph','photographs','photo','photos','interior','exterior'])]
    scores={k:sum(1 for w in words if re.search(r'\b'+re.escape(w)+r'\b',t)) for k,words in rules}
    k=max(scores,key=scores.get)
    return k if scores[k] else 'reference'

def normalize(item, kind='web'):
    title=item.get('title') or item.get('description') or 'Untitled'
    url=item.get('url') or item.get('link') or ''
    return {'id':hashlib.md5((kind+'|'+url).encode()).hexdigest()[:8] if url else None,'title':title,'url':url,'source':item.get('profile',{}).get('long_name') or item.get('meta_url',{}).get('hostname') or 'Web','type':classify(title+' '+item.get('description','')),'thumbnail':item.get('thumbnail',{}).get('src') if isinstance(item.get('thumbnail'),dict) else None,'kind':kind}

@app.get('/')
def home(): return send_from_directory(app.static_folder,'index.html')
@app.get('/api/projects')
def projects():
    q=request.args.get('q','').strip().lower(); typ=request.args.get('type','All'); country=request.args.get('country','All')
    out=DEMO
    if q: out=[p for p in out if q in ' '.join([p['title'],p['architect'],p['location'],' '.join(p['tags'])]).lower()]
    if typ!='All': out=[p for p in out if p['type']==typ]
    if country!='All': out=[p for p in out if country.lower() in p['location'].lower()]
    return jsonify({'projects':out,'mode':'demo','source':'local catalogue'})

@app.get('/api/project/<pid>')
def project(pid):
    p=next((x for x in DEMO if x['id']==pid),None)
    if not p: return jsonify({'error':'Project not found'}),404
    assets=[]
    for typ,n in p['counts'].items():
        for i in range(n):
            assets.append({'id':hashlib.md5(f'{pid}-{typ}-{i}'.encode()).hexdigest()[:8],'type':typ.rstrip('s'),'title':f'{typ.title()} {i+1}','source':'Project research index','url':f'https://www.google.com/search?q={quote(p["title"]+" "+typ)}','thumbnail':p['image'] if typ=='photos' and i==0 else None})
    return jsonify({'project':p,'assets':assets})

@app.get('/api/search')
def search():
    q=request.args.get('q','').strip(); mode=request.args.get('mode','all')
    if mode not in ('all','web','images'):
        return jsonify({'error':"Invalid mode. Valid values: all, web, images."}),400
    if not q: return jsonify({'query':'','results':[],'message':'Enter a project, architect, building type or precedent query.'})
    if rate_limited(client_ip()):
        return jsonify({'error':f'Search rate limit exceeded. Try again in {RATE_WINDOW} seconds.'}),429
    local=[{'kind':'project','project':p} for p in local_matches(q)]
    results=[]
    ck=('search', q.lower(), mode)
    cached=cache_get(ck)
    if cached is not None:
        results=cached
    else:
        tasks={}
        if mode in ('all','web'):
            tasks['web']=('web/search',{'q':q+' architecture project plans sections','count':12,'country':'ALL','search_lang':'en'})
        if mode in ('all','images'):
            tasks['images']=('images/search',{'q':q+' architecture plan section','count':20,'country':'ALL','search_lang':'en'})
        if tasks:
            with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
                futs={k:ex.submit(brave,*v) for k,v in tasks.items()}
                data={k:f.result() for k,f in futs.items()}
            if data.get('web'):
                results=[normalize(x,'web') for x in data['web'].get('web',{}).get('results',[])]
            if data.get('images'):
                results += [normalize(x,'image') for x in data['images'].get('results',[])]
        cache_set(ck, results)
    if results:
        notice=''
    elif not os.getenv('BRAVE_API_KEY'):
        notice='Live web search requires BRAVE_API_KEY. Demo catalogue remains available.'
    else:
        notice='Search returned no results, or the search service is unavailable. Please try again.'
    return jsonify({'query':q,'local':local,'results':results,'mode':'live' if results else 'demo','notice':notice})

@app.get('/health')
def health(): return {'ok':True}

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')),debug=os.getenv('FLASK_DEBUG','0')=='1')
