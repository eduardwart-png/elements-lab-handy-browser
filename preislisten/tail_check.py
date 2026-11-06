import json
r = json.load(open("quellen_extrahiert/ting_pens_zeilen.json"))
print([ (x['code'], x['name'], x['spec'], x['dual_usd'], x['single_usd'], x['flag'][:30]) for x in r[-8:]])
print([x for x in r if 'ada' in x['code'].lower() or 'ada' in x['name'].lower()])
o = json.load(open("merged.json"))
print("dual names", sorted({d['name'] for d in o['dual']}))
print("held", o['dual_held'])
