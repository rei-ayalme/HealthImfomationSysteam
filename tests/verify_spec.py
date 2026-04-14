from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

r1 = client.get('/api/chart/trend', params={'region':'global','metric':'dalys','start_year':2010,'end_year':2024})
r2 = client.get('/api/chart/trend', params={'region':'east_asia','metric':'dalys','start_year':2010,'end_year':2024})
for name, r in [('global', r1), ('east_asia', r2)]:
    data = r.json()
    x = data.get('xAxis', [])
    y = (data.get('series') or [{}])[0].get('data', [])
    print(f'trend {name}: status={r.status_code}, points={len(x)}, y_points={len(y)}')

r3 = client.get('/api/map/world-metrics', params={'region':'global','metric':'dalys','year':2024})
d3 = r3.json()
print('world global:', r3.status_code, 'count=', len(d3.get('data', [])))
if d3.get('data'):
    keys = sorted(list(d3['data'][0].keys()))
    print('world sample keys:', keys)

r4 = client.get('/api/map/world-metrics', params={'region':'east_asia','metric':'dalys','year':2024})
d4 = r4.json()
fallback_count = sum(1 for i in d4.get('data', []) if i.get('is_fallback'))
print('world east_asia:', r4.status_code, 'count=', len(d4.get('data', [])), 'fallback=', fallback_count)
