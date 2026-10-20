#!/usr/bin/env python3
"""Generate verified suburb medians from a permitted CSV, without synthetic inputs.
Required CSV: suburb,metric,year,value,source,bedrooms (for house sales).
A run with no eligible rows produces [] rather than fabricated metrics.
"""
import argparse,csv,json,statistics
from collections import defaultdict
from pathlib import Path

def aggregate(path):
    groups=defaultdict(list)
    with open(path,newline='',encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            kind=row.get('metric','').strip().lower()
            if kind not in ('land','house'): continue
            try:
                suburb=row['suburb'].strip().upper()
                year=int(row['year'])
                value=float(row['value'])
                bedroom=row.get('bedrooms','all').strip() or 'all'
                if kind=='land': bedroom='all'
                elif bedroom!='all': bedroom=int(bedroom)
                source=row['source'].strip()
                if not suburb or not source or value<=0 or not 1900<=year<=2100:continue
            except (KeyError,ValueError,TypeError):continue
            groups[(suburb,kind,year,bedroom,source)].append(value)
    result=[]
    for (suburb,kind,year,bedroom,source),values in sorted(groups.items()):
        result.append(dict(suburb=suburb,metric=kind,year=year,bedrooms=bedroom,median=round(statistics.median(values)),sample_size=len(values),source=source,coverage="Eligible source records only"))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('csv',help='Licensed and verified source records')
    parser.add_argument('--output',default='data/metrics.json')
    args=parser.parse_args()
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(aggregate(args.csv),indent=2),encoding='utf-8')
    print('Wrote',output)
