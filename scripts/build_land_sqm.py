#!/usr/bin/env python3
"""Generate sourced Sydney suburb land $/m². Standalone; no FC27 dependencies."""
import json, os, time, math, urllib.parse, urllib.request, statistics, datetime
from pathlib import Path
BASE='https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer/5/query'
BOUND='https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme_multiCRS/FeatureServer/2/query'
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'land_sqm.json'
def get(url,params,retries=4):
    u=url+'?'+urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            req=urllib.request.Request(u,headers={'User-Agent':'SydneyPropertyIntelligence/1.0 (public NSW valuation research)','Accept':'application/json'})
            with urllib.request.urlopen(req,timeout=65) as r: obj=json.load(r)
            if 'error' in obj: raise ValueError(f"NSW API rejected query at {url}: {obj['error']}; parameters: {params}")
            return obj
        except Exception as exc:
            if isinstance(exc, ValueError) or attempt==retries-1: raise
            print('Retry',attempt+1,str(exc)[:130],flush=True);time.sleep(2**attempt)
def area(x):
    import re
    if x is None:return None
    s=str(x).lower().replace(',','').strip()
    m=re.search(r'\d+(?:\.\d+)?',s)
    if not m:return None
    a=float(m.group())
    if 'hectare' in s or re.search(r'\bha\b',s):a*=10000
    elif 'acre' in s or re.search(r'\bac\b',s):a*=4046.8564224
    elif 'km²' in s or 'km2' in s:a*=1000000
    elif not (re.search(r'\bm2\b|m²|sqm|square metre',s) or re.fullmatch(r'\d+(?:\.\d+)?',s)):return None
    return a if 25<=a<=1000000 else None
def val(x):
    import re
    try:return float(re.sub('[^0-9.]','',str(x)))
    except:return 0
def year(x):
    import re
    m=re.search(r'(?:19|20)\d{2}',str(x))
    return int(m.group()) if m else None
def inside(x,y,ring):
    hit=False;j=len(ring)-1
    for i in range(len(ring)):
        a,b=ring[i],ring[j]
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:hit=not hit
        j=i
    return hit
def within(pt,geom):
    ringsets=[geom['coordinates']] if geom['type']=='Polygon' else geom['coordinates'] if geom['type']=='MultiPolygon' else []
    return any(inside(*pt,rings[0]) and not any(inside(*pt,hole) for hole in rings[1:]) for rings in ringsets if rings)
def bounds(geom):
    def walk(v):
        if isinstance(v[0],(int,float)):yield v
        else:
            for item in v:yield from walk(item)
    pts=list(walk(geom['coordinates']))
    return min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)
def main():
    env={'xmin':150.45,'ymin':-34.25,'xmax':151.42,'ymax':-33.44,'spatialReference':{'wkid':4326}}
    geo=get(BOUND,{'where':'1=1','geometry':json.dumps(env),'geometryType':'esriGeometryEnvelope','inSR':4326,'spatialRel':'esriSpatialRelIntersects','outFields':'suburbname','returnGeometry':'true','outSR':4326,'geometryPrecision':5,'f':'geojson','resultRecordCount':2000})
    features=[f for f in geo.get('features',[]) if f.get('geometry') and f.get('properties',{}).get('suburbname')]
    print('Found',len(features),'suburbs',flush=True)
    previous={}
    if OUT.exists():
        try:previous={x['suburb']:x for x in json.loads(OUT.read_text())}
        except:pass
    results=previous.copy()
    limit=int(os.getenv('SUBURB_LIMIT','835'))
    target=os.getenv('TARGET_SUBURB','KINCUMBER').upper()
    features=[f for f in features if f['properties']['suburbname'].strip().upper()==target]
    if not features: raise RuntimeError(f'Test suburb {target} not found')
    for idx,f in enumerate(features[:limit],1):
        name=f['properties']['suburbname'].strip()
        if name in results and results[name].get('sample_size',0)>=10:continue
        box=bounds(f['geometry'])
        base={'where':'1=1','geometry':','.join(map(str,box)),'geometryType':'esriGeometryEnvelope','inSR':4326,'spatialRel':'esriSpatialRelIntersects','outFields':'prop_area,val1_lv,val1_bd,val2_lv,val2_bd,val3_lv,val3_bd,val4_lv,val4_bd,val5_lv,val5_bd','returnGeometry':'true','outSR':4326,'f':'json'}
        try:
            total=get(BASE,{**base,'returnCountOnly':'true','returnGeometry':'false'}).get('count',0)
            if not total:continue
            if total>30000:
                print(name,'SKIP large extent',total,flush=True);continue
            observations={}
            offset=0
            while offset<total:
                payload=get(BASE,{**base,'resultRecordCount':100})
                feats=payload.get('features',[])
                if not feats:break
                for item in feats:
                    geom=item.get('geometry',{})
                    if 'x' not in geom or not within((geom['x'],geom['y']),f['geometry']):continue
                    att=item['attributes'];a=area(att.get('prop_area'))
                    if not a:continue
                    for k in range(1,6):
                        v=val(att.get(f'val{k}_lv'));yr=year(att.get(f'val{k}_bd'))
                        if v>0 and yr and 2018<=yr<=2026:
                            observations.setdefault(yr,[]).append(v/a)
                offset+=len(feats)
                break  # Initial one-suburb API compatibility test; not full coverage
            viable=[(yr,vals) for yr,vals in observations.items() if len(vals)>=10]
            if not viable:continue
            yr,vals=max(viable,key=lambda pair:pair[0])
            results[name]={'suburb':name,'metric':'land','median':round(statistics.mean(vals)),'per_sqm':round(statistics.mean(vals)),'sample_size':len(vals),'area_sample_size':len(vals),'year':yr,'bedrooms':'all','source':'NSW Spatial Services, Valuation MapServer/5; individual parcel assessed land value / land area','coverage':'Urban properties only; latest common valuation year. Arithmetic mean of parcel $/m², not vacant land transaction price.'}
            if idx%10==0:
                OUT.write_text(json.dumps(sorted(results.values(),key=lambda x:x['suburb']),indent=2))
            print(idx,name,yr,len(vals),'$',results[name]['per_sqm'],'/m²',flush=True)
        except ValueError as exc:
            raise RuntimeError(f'Invalid NSW API query for {name}: {exc}') from exc
        except Exception as exc:
            print(idx,name,'ERROR',str(exc)[:220],flush=True)
    OUT.write_text(json.dumps(sorted(results.values(),key=lambda x:x['suburb']),indent=2))
    print('COMPLETED',len(results),'verified suburb land values',flush=True)
    if not results:raise RuntimeError('No suburb values extracted; refusing to publish empty data')
if __name__=='__main__':main()
