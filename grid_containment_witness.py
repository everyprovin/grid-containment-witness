# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import hashlib
import json
import re
from datetime import datetime, timezone


def _require(ok: bool,message: str) -> None:
    if not ok:
        raise gl.vm.UserError('[EXPECTED] '+message)


def _canon(value) -> str:
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)


def _hash(value) -> str:
    return hashlib.sha256(_canon(value).encode()).hexdigest()


def _now() -> int:
    t=datetime.fromisoformat(gl.message_raw['datetime'].replace('Z','+00:00'))
    if t.tzinfo is None:
        t=t.replace(tzinfo=timezone.utc)
    d=t.astimezone(timezone.utc)-datetime(1970,1,1,tzinfo=timezone.utc)
    return d.days*86400+d.seconds


def _id(value: str) -> None:
    _require(isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,32}',value) is not None,'invalid ASCII identifier')


def _point(x: int,y: int) -> None:
    _require(type(x) is int and type(y) is int and -1000000<=x<=1000000 and -1000000<=y<=1000000,'integer coordinate outside +/-1e6')


def _source(url: str,digest: str) -> None:
    m=re.fullmatch(r'https://raw\.githubusercontent\.com/[A-Za-z0-9-]{1,39}/[A-Za-z0-9_.-]{1,100}/[0-9a-f]{40}/([A-Za-z0-9_.~/-]+)',url) if isinstance(url,str) and len(url)<=512 else None
    _require(m is not None and all(p not in ('','.','..') for p in url.split('/')[3:]),'commit-pinned public source required')
    _require(isinstance(digest,str) and re.fullmatch(r'[0-9a-f]{64}',digest) is not None,'invalid SHA256')


def _pairs(pairs: list) -> dict:
    out={}
    for key,value in pairs:
        _require(key not in out,'duplicate JSON key');out[key]=value
    return out


def _constant(value: str):
    raise gl.vm.UserError('[SOURCE] non-finite JSON literal')


def _cross(a: list,b: list,c: list) -> int:
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def _on(a: list,b: list,p: list) -> bool:
    return _cross(a,b,p)==0 and min(a[0],b[0])<=p[0]<=max(a[0],b[0]) and min(a[1],b[1])<=p[1]<=max(a[1],b[1])


def _intersects(a: list,b: list,c: list,d: list) -> bool:
    x1=_cross(a,b,c);x2=_cross(a,b,d);x3=_cross(c,d,a);x4=_cross(c,d,b)
    if x1==0 and _on(a,b,c) or x2==0 and _on(a,b,d) or x3==0 and _on(c,d,a) or x4==0 and _on(c,d,b):
        return True
    return x1*x2<0 and x3*x4<0


def _area(ring: list) -> int:
    return sum(ring[i][0]*ring[(i+1)%len(ring)][1]-ring[(i+1)%len(ring)][0]*ring[i][1] for i in range(len(ring)))


def _ring(value,limit: int) -> list:
    _require(isinstance(value,list) and 3<=len(value)<=limit,'ring vertex capacity')
    for p in value:
        _require(isinstance(p,list) and len(p)==2,'vertex must have two coordinates');_point(p[0],p[1])
    _require(len(set(tuple(p) for p in value))==len(value),'duplicate or closing vertex')
    _require(_area(value)!=0,'zero area ring')
    n=len(value)
    for i in range(n):
        previous=value[(i-1)%n];current=value[i];following=value[(i+1)%n]
        dot=(previous[0]-current[0])*(following[0]-current[0])+(previous[1]-current[1])*(following[1]-current[1])
        _require(not (_cross(previous,current,following)==0 and dot>0),'adjacent overlapping edges')
        for j in range(i+1,n):
            if j==i+1 or i==0 and j==n-1:
                continue
            _require(not _intersects(value[i],value[(i+1)%n],value[j],value[(j+1)%n]),'non-adjacent self crossing or touch')
    return value


def _locate(ring: list,p: list) -> str:
    inside=False
    for i,a in enumerate(ring):
        b=ring[(i+1)%len(ring)]
        if _on(a,b,p):
            return 'BOUNDARY'
        if (a[1]>p[1])!=(b[1]>p[1]):
            # x_intersection - px = orientation(a,b,p)/(by-ay).
            # Compare signs instead of dividing or using floating point.
            if _cross(a,b,p)*(b[1]-a[1])>0:
                inside=not inside
    return 'INSIDE' if inside else 'OUTSIDE'


def _rings_touch(a: list,b: list) -> bool:
    return any(_intersects(a[i],a[(i+1)%len(a)],b[j],b[(j+1)%len(b)]) for i in range(len(a)) for j in range(len(b)))


def _canonical(ring: list,ccw: bool) -> list:
    values=ring if (_area(ring)>0)==ccw else list(reversed(ring))
    first=min(range(len(values)),key=lambda i:tuple(values[i]))
    return values[first:]+values[:first]


def _region(url: str,digest: str) -> dict:
    response=gl.nondet.web.get(url,headers={'Accept':'application/json'})
    if response.status!=200 or response.body is None or not 1<=len(response.body)<=16384:
        raise gl.vm.UserError('[SOURCE] unavailable or oversized region')
    if hashlib.sha256(response.body).hexdigest()!=digest:
        raise gl.vm.UserError('[SOURCE] region byte digest mismatch')
    try:
        data=json.loads(response.body.decode('utf-8'),object_pairs_hook=_pairs,parse_constant=_constant)
    except (ValueError,UnicodeError,RecursionError):
        raise gl.vm.UserError('[SOURCE] invalid region JSON')
    _require(isinstance(data,dict) and set(data)=={'outer','holes'},'region fields')
    outer=_ring(data['outer'],16)
    _require(isinstance(data['holes'],list) and len(data['holes'])<=2,'hole count capacity')
    holes=[_ring(hole,8) for hole in data['holes']]
    _require(len(outer)+sum(len(h) for h in holes)<=32,'total vertex capacity')
    for hole in holes:
        _require(all(_locate(outer,p)=='INSIDE' for p in hole),'hole not strictly inside outer')
        _require(not _rings_touch(outer,hole),'hole crosses or touches outer')
    for i in range(len(holes)):
        for j in range(i+1,len(holes)):
            _require(not _rings_touch(holes[i],holes[j]),'holes cross or touch')
            _require(_locate(holes[i],holes[j][0])=='OUTSIDE' and _locate(holes[j],holes[i][0])=='OUTSIDE','holes nested')
    return {'outer':_canonical(outer,True),'holes':sorted([_canonical(h,False) for h in holes],key=lambda h:tuple(tuple(p) for p in h))}


def _classification(geometry: dict,point: list) -> str:
    outer=_locate(geometry['outer'],point);holes=[_locate(h,point) for h in geometry['holes']]
    if outer=='BOUNDARY' or 'BOUNDARY' in holes:
        return 'BOUNDARY'
    if outer=='OUTSIDE' or 'INSIDE' in holes:
        return 'OUTSIDE'
    return 'INSIDE'


def _capture(url: str,digest: str,point: list,binding: dict) -> dict:
    def leader() -> dict:
        geometry=_region(url,digest)
        return {'binding':binding,'source_sha256':digest,'result':{'classification':_classification(geometry,point),'geometry':geometry,'geometry_sha256':_hash(geometry)}}
    def validator(proposed: gl.vm.Result) -> bool:
        if not isinstance(proposed,gl.vm.Return):
            return False
        try:
            # Fresh bytes and complete topology/canonicalization/point derivation.
            return _canon(leader())==_canon(proposed.calldata)
        except Exception:
            return False
    return gl.vm.run_nondet_unsafe(leader,validator)


class GridContainmentWitness(gl.Contract):
    owner: Address
    regions: TreeMap[str,str]
    queries: TreeMap[str,str]
    region_count: u256

    def __init__(self):
        self.owner=gl.message.sender_address

    def _owner(self) -> None:
        _require(gl.message.sender_address==self.owner,'owner only')

    def _region(self,region_id: str) -> dict:
        _require(region_id in self.regions,'unknown region')
        return json.loads(self.regions[region_id])

    def _query(self,region_id: str,query_id: str) -> dict:
        key=region_id+':'+query_id
        _require(key in self.queries,'unknown query')
        return json.loads(self.queries[key])

    def _save_query(self,region_id: str,query_id: str,q: dict) -> None:
        self.queries[region_id+':'+query_id]=_canon(q)

    def _cas(self,q: dict,expected_revision: int) -> None:
        _require(type(expected_revision) is int and expected_revision==q['revision'],'stale revision')

    def _transition(self,q: dict,status: str) -> None:
        q['status']=status;q['revision']+=1
        _require(len(q['history'])<4,'phase history capacity')
        q['history'].append({'status':status,'revision':q['revision'],'at':_now()})

    @gl.public.write
    def register_region(self,region_id: str,source_url: str,source_sha256: str) -> None:
        self._owner();_id(region_id);_source(source_url,source_sha256)
        _require(region_id not in self.regions,'region ID already used')
        _require(int(self.region_count)<8,'region capacity')
        self.regions[region_id]=_canon({'region_id':region_id,'owner':self.owner.as_hex.lower(),'source_url':source_url,'source_sha256':source_sha256,'registered_at':_now(),'query_ids':[],'geometry_sha256':'','geometry':None})
        self.region_count=u256(int(self.region_count)+1)

    @gl.public.write
    def request_query(self,region_id: str,query_id: str,x: int,y: int) -> None:
        self._owner();_id(query_id);_point(x,y);r=self._region(region_id)
        _require(region_id+':'+query_id not in self.queries,'query ID already used')
        _require(len(r['query_ids'])<32,'query capacity')
        q={'region_id':region_id,'query_id':query_id,'point':[x,y],'owner':r['owner'],'source_sha256':r['source_sha256'],'requested_at':_now(),'status':'REQUESTED','revision':0,'result':None,'attestation':None,'certificate_id':'','classified_at':0,'activated_at':0,'revoked_at':0,'reason':'','history':[{'status':'REQUESTED','revision':0,'at':_now()}]}
        self._save_query(region_id,query_id,q);r['query_ids'].append(query_id);self.regions[region_id]=_canon(r)

    @gl.public.write
    def classify(self,region_id: str,query_id: str,x: int,y: int) -> str:
        _point(x,y);r=self._region(region_id);q=self._query(region_id,query_id)
        _require(q['status']=='REQUESTED' and q['revision']==0,'query not requested for classification')
        _require(q['point']==[x,y],'point mismatch')
        binding={'protocol':'GridContainmentWitness-v1','chain_id':int(gl.message.chain_id),'contract':gl.message.contract_address.as_hex.lower(),'region_id':region_id,'query_id':query_id,'owner':r['owner'],'source_url':r['source_url'],'source_sha256':r['source_sha256'],'point':[x,y],'registered_at':r['registered_at'],'requested_at':q['requested_at'],'classified_at':_now(),'classifier':gl.message.sender_address.as_hex.lower(),'expected_revision':0}
        packet=_capture(r['source_url'],r['source_sha256'],[x,y],binding)
        result=packet['result']
        _require(not r['geometry_sha256'] or (r['geometry_sha256']==result['geometry_sha256'] and _canon(r['geometry'])==_canon(result['geometry'])),'region geometry mismatch')
        r['geometry_sha256']=result['geometry_sha256'];r['geometry']=result['geometry']
        q['attestation']=packet;q['result']=result;q['certificate_id']=_hash(['GridContainmentWitness-certificate-v1',packet]);q['classified_at']=_now()
        self._transition(q,'CERTIFIED');self._save_query(region_id,query_id,q);self.regions[region_id]=_canon(r)
        return q['certificate_id']

    @gl.public.write
    def activate(self,region_id: str,query_id: str,expected_revision: int,certificate_id: str) -> None:
        self._owner();q=self._query(region_id,query_id);self._cas(q,expected_revision)
        _require(q['status']=='CERTIFIED','query certificate not ready')
        _require(isinstance(certificate_id,str) and certificate_id==q['certificate_id'],'certificate mismatch')
        q['activated_at']=_now();self._transition(q,'ACTIVE');self._save_query(region_id,query_id,q)

    @gl.public.write
    def revoke(self,region_id: str,query_id: str,expected_revision: int,reason: str) -> None:
        self._owner();q=self._query(region_id,query_id);self._cas(q,expected_revision)
        _require(q['status']!='REVOKED','query already revoked')
        _require(isinstance(reason,str) and 1<=len(reason)<=200 and reason==reason.strip(),'revocation reason required')
        q['reason']=reason;q['revoked_at']=_now();self._transition(q,'REVOKED');self._save_query(region_id,query_id,q)

    @gl.public.view
    def get_region(self,region_id: str) -> dict:
        return self._region(region_id)

    @gl.public.view
    def get_query(self,region_id: str,query_id: str) -> dict:
        return self._query(region_id,query_id)

    @gl.public.view
    def is_active(self,region_id: str,query_id: str,certificate_id: str,expected_revision: int) -> bool:
        q=self._query(region_id,query_id)
        return q['status']=='ACTIVE' and q['certificate_id']==certificate_id and type(expected_revision) is int and q['revision']==expected_revision

    @gl.public.view
    def get_configuration(self) -> dict:
        return {'protocol':'GridContainmentWitness-v1','owner':self.owner.as_hex.lower(),'max_regions':8,'regions_registered':int(self.region_count),'max_queries_per_region':32,'max_outer_vertices':16,'max_holes':2,'max_hole_vertices':8,'max_total_vertices':32,'max_source_bytes':16384,'coordinate_domain':'synthetic abstract integer grid, not geography'}
