#!/usr/bin/env python3
"""Phase 2 checks for national source registry expansion."""
import json, pathlib, sys, collections
ROOT = pathlib.Path(__file__).resolve().parents[1]
required = [
    "index.html", "kenya_public_sector_viewer.html", "data/public_sector_feed.json",
    "data/source_registry.json", "data/source_status.json", "data/coverage_registry.json",
    "data/ministry_registry.json", "data/national_institution_registry.json", "PUSH_TO_GITHUB.cmd"
]
errors=[]
for rel in required:
    if not (ROOT/rel).exists(): errors.append(f"missing {rel}")
feed=json.loads((ROOT/'data/public_sector_feed.json').read_text(encoding='utf-8'))
reg=json.loads((ROOT/'data/source_registry.json').read_text(encoding='utf-8'))
sources=reg.get('sources',[])
if feed.get('meta',{}).get('scope')!='national_government_and_government_related_only': errors.append('feed meta scope is not national-only')
if feed.get('meta',{}).get('role_scope')!='all_job_families': errors.append('feed role_scope is not all_job_families')
if len(sources) < 150: errors.append(f'expected at least 150 national sources after Phase 2, found {len(sources)}')
for s in sources:
    blob=' '.join(str(s.get(k,'')) for k in ('source_id','source_group','owner_type','name')).lower()
    if any(x in blob for x in ('county_psb','county_assembly','county_government')):
        errors.append('county source in registry: '+str(s.get('source_id')))
for group in ['ministries','state_departments','sagas_state_corporations','regulators','public_universities','constitutional_commissions']:
    if not any(s.get('source_group')==group for s in sources):
        errors.append('missing source group: '+group)
if 'https://github.com/dansamuka/PS_2.git' not in (ROOT/'PUSH_TO_GITHUB.cmd').read_text(encoding='utf-8'):
    errors.append('PUSH_TO_GITHUB.cmd does not default to PS_2')
missing_links=[v.get('id','<missing>') for v in feed.get('vacancies',[]) if not v.get('links',{}).get('view_original_url')]
if missing_links: errors.append('vacancies missing view_original_url: '+', '.join(missing_links[:10]))
if errors:
    for e in errors: print('ERROR:',e)
    sys.exit(1)
print('OK: Phase 2 national source registry checks passed.')
print('Vacancies:', len(feed.get('vacancies',[])))
print('Sources registered:', len(sources))
print('Groups:', dict(collections.Counter(s.get('source_group') for s in sources)))
