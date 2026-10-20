import copy
import hashlib
import json
from pathlib import Path
import re
import pytest
from gltest.direct import create_address

ROOT=Path(__file__).parents[1];META=json.loads((ROOT/'fixtures/source.json').read_text());BODY=(ROOT/'fixtures/region.json').read_text()
def deploy(vm,build):
    vm.warp('2026-10-21T00:00:00Z');c=build(str(ROOT/'grid_containment_witness.py'),sdk_version='v0.2.12')
    assert hasattr(c,'register_region'),'GridContainmentWitness API not implemented'
    return c
def register(vm,c,body=BODY,region='region'):
    vm.clear_mocks()
    vm.mock_web(re.escape(META['test_url']),{'status':200,'body':body});c.register_region(region,META['test_url'],hashlib.sha256(body.encode()).hexdigest())
def classify(c,x,y,region='region',query='query'):
    c.request_query(region,query,x,y);return c.classify(region,query,x,y)
@pytest.mark.parametrize('x,y,want',[(2,2,'INSIDE'),(5,5,'OUTSIDE'),(20,5,'OUTSIDE'),(0,5,'BOUNDARY'),(0,0,'BOUNDARY'),(3,5,'BOUNDARY'),(3,3,'BOUNDARY'),(10,10,'BOUNDARY')])
def test_exact_outer_hole_and_vertex_classifications(direct_vm,direct_deploy,x,y,want):
    c=deploy(direct_vm,direct_deploy);register(direct_vm,c);cert=classify(c,x,y)
    q=c.get_query('region','query');assert q['result']['classification']==want and q['point']==[x,y]
    assert direct_vm.run_validator() is True
    c.activate('region','query',1,cert);assert c.is_active('region','query',cert,2) is True
def test_rotation_reversal_and_hole_order_canonicalize_identically(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy);r={'outer':[[0,0],[10,0],[10,10],[0,10]],'holes':[[[1,1],[2,1],[2,2],[1,2]],[[6,6],[8,6],[8,8],[6,8]]]}
    register(direct_vm,c,json.dumps(r),'r1');classify(c,5,5,'r1');first=c.get_query('r1','query')['result']
    r['outer']=list(reversed(r['outer'][1:]+r['outer'][:1]));r['holes']=[list(reversed(h[2:]+h[:2])) for h in reversed(r['holes'])]
    register(direct_vm,c,json.dumps(r),'r2');classify(c,5,5,'r2');second=c.get_query('r2','query')['result']
    assert first['geometry_sha256']==second['geometry_sha256'] and first['geometry']==second['geometry'] and second['classification']=='INSIDE'
@pytest.mark.parametrize('x,y,want',[(3,4,'OUTSIDE'),(1,4,'INSIDE'),(3,1,'INSIDE'),(2,4,'BOUNDARY')])
def test_concave_half_open_integer_ray_crossing(direct_vm,direct_deploy,x,y,want):
    c=deploy(direct_vm,direct_deploy);body=json.dumps({'outer':[[0,0],[6,0],[6,6],[4,6],[4,2],[2,2],[2,6],[0,6]],'holes':[]});register(direct_vm,c,body);classify(c,x,y)
    assert c.get_query('region','query')['result']['classification']==want
def test_negative_large_coordinates_and_no_float_rounding(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy);body=json.dumps({'outer':[[-1000000,-1000000],[1000000,-1000000],[1000000,1000000],[-1000000,1000000]],'holes':[]});register(direct_vm,c,body);classify(c,999999,999999)
    assert c.get_query('region','query')['result']['classification']=='INSIDE'
def test_permissionless_execution_cannot_squat_or_change_reserved_point(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy);register(direct_vm,c);c.request_query('region','q',2,2);other=create_address('other')
    with direct_vm.prank(other):
        with direct_vm.expect_revert('owner only'):c.request_query('region','squat',1,1)
        with direct_vm.expect_revert('point mismatch'):c.classify('region','q',5,5)
        cert=c.classify('region','q',2,2)
        with direct_vm.expect_revert('owner only'):c.activate('region','q',1,cert)
    with direct_vm.expect_revert('stale revision'):c.activate('region','q',0,cert)
    with direct_vm.expect_revert('certificate'):c.activate('region','q',1,'00'*32)
    c.activate('region','q',1,cert);direct_vm.clear_mocks();c.revoke('region','q',2,'Synthetic certificate withdrawn.')
    assert c.is_active('region','q',cert,2) is False and c.get_query('region','q')['revision']==3
    with direct_vm.expect_revert():c.classify('region','q',2,2)
    with direct_vm.expect_revert('already used'):c.request_query('region','q',1,1)
    with direct_vm.expect_revert('already used'):register(direct_vm,c)
def test_distinct_points_have_independent_certificates(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy);register(direct_vm,c);a=classify(c,2,2,query='a');b=classify(c,5,5,query='b')
    assert a!=b;c.activate('region','a',1,a);c.activate('region','b',1,b);c.revoke('region','a',2,'Withdraw one only.')
    assert c.is_active('region','b',b,2) is True
def test_forged_full_shape_and_fresh_source_drift_rejected(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy);register(direct_vm,c);classify(c,2,2);packet=copy.deepcopy(c.get_query('region','query')['attestation']);packet['result']['classification']='OUTSIDE'
    assert direct_vm.run_validator(leader_result=packet) is False
    direct_vm.clear_mocks();direct_vm.mock_web(re.escape(META['test_url']),{'status':200,'body':BODY+' '});assert direct_vm.run_validator() is False
def test_unavailable_source_preserves_requested_query_and_offline_revoke(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy);register(direct_vm,c);c.request_query('region','q',2,2);direct_vm.clear_mocks();direct_vm.mock_web(re.escape(META['test_url']),{'status':503,'body':'missing'})
    with direct_vm.expect_revert('SOURCE'):c.classify('region','q',2,2)
    assert c.get_query('region','q')['status']=='REQUESTED';c.revoke('region','q',0,'Source unavailable.')
@pytest.mark.parametrize('kind',['bowtie','self-touch','zero-area','closing-duplicate','adjacent-overlap','hole-outside','hole-outer-touch','hole-crosses-outer','holes-cross','holes-touch','holes-nested','concave-hole-edge-outside','boolean','nan','duplicate-key','too-many-vertices','too-many-holes','too-many-hole-vertices','oversized-source'])
def test_invalid_topology_never_certifies(direct_vm,direct_deploy,kind):
    c=deploy(direct_vm,direct_deploy);r=json.loads(BODY)
    if kind=='bowtie':r={'outer':[[0,0],[6,5],[0,5],[5,0]],'holes':[]}
    elif kind=='self-touch':r={'outer':[[0,0],[6,0],[6,6],[3,0],[0,6]],'holes':[]}
    elif kind=='zero-area':r={'outer':[[0,0],[1,1],[2,2]],'holes':[]}
    elif kind=='closing-duplicate':r['outer'].append(r['outer'][0])
    elif kind=='adjacent-overlap':r={'outer':[[0,0],[6,0],[3,0],[6,6],[0,6]],'holes':[]}
    elif kind=='hole-outside':r['holes']=[[[11,1],[12,1],[12,2],[11,2]]]
    elif kind=='hole-outer-touch':r['holes']=[[[0,2],[2,2],[2,4],[0,4]]]
    elif kind=='hole-crosses-outer':r['holes']=[[[8,2],[12,2],[12,4],[8,4]]]
    elif kind=='holes-cross':r['holes']=[[[2,2],[6,2],[6,6],[2,6]],[[4,4],[8,4],[8,8],[4,8]]]
    elif kind=='holes-touch':r['holes']=[[[1,1],[4,1],[4,4],[1,4]],[[4,2],[6,2],[6,3],[4,3]]]
    elif kind=='holes-nested':r['holes']=[[[1,1],[9,1],[9,9],[1,9]],[[2,2],[3,2],[3,3],[2,3]]]
    elif kind=='concave-hole-edge-outside':r={'outer':[[0,0],[6,0],[6,6],[4,6],[4,2],[2,2],[2,6],[0,6]],'holes':[[[1,5],[5,5],[3,1]]]}
    elif kind=='boolean':r['outer'][0][0]=True
    elif kind=='nan':r['outer'][0][0]=float('nan')
    elif kind=='too-many-vertices':r['outer']=[[i,0] for i in range(17)]
    elif kind=='too-many-holes':r['holes']=[[[1,1],[2,1],[1,2]],[[3,1],[4,1],[3,2]],[[5,1],[6,1],[5,2]]]
    elif kind=='too-many-hole-vertices':r['holes']=[[[1,1],[2,1],[3,1],[4,1],[4,4],[3,4],[2,4],[1,4],[1,3]]]
    body='{"outer":[],"outer":[],"holes":[]}' if kind=='duplicate-key' else (' '*16385 if kind=='oversized-source' else json.dumps(r))
    register(direct_vm,c,body);c.request_query('region','q',2,2)
    with direct_vm.expect_revert():c.classify('region','q',2,2)
    assert c.get_query('region','q')['certificate_id']==''
def test_point_bounds_and_finite_owner_reserved_history(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy);register(direct_vm,c)
    with direct_vm.expect_revert('integer coordinate'):c.request_query('region','bad',True,0)
    with direct_vm.expect_revert('integer coordinate'):c.request_query('region','bad',1000001,0)
    for i in range(32):c.request_query('region','q'+str(i),0,i)
    with direct_vm.expect_revert('capacity'):c.request_query('region','overflow',1,1)
