import io, hmac, html, time, math, datetime, csv, re, sqlite3, os, hashlib, secrets
from fastapi.responses import Response
from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DB = os.environ.get("TUTOR_DB") or os.path.join(ROOT, "tutor.db"); ADMIN_USER = os.environ.get("ADMIN_USERNAME","admin").strip().lower(); ADMIN_PASS = os.environ.get("ADMIN_PASSWORD","TutorMatch@Admin26")
app = FastAPI(title="AI Tutor Indore", docs_url=None, redoc_url=None, openapi_url=None)
@app.middleware("http")
async def sec(request, call_next):
    r = await call_next(request)
    r.headers.update({"X-Content-Type-Options":"nosniff","X-Frame-Options":"DENY","Referrer-Policy":"same-origin","Content-Security-Policy":"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'"})
    return r
DAYS = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
FULL = dict(Mon="monday",Tue="tuesday",Wed="wednesday",Thu="thursday",Fri="friday",Sat="saturday",Sun="sunday")
ZONES = {"Vijay Nagar":"A","Scheme 54":"A","Scheme 78":"A","Bengali Square":"A","Palasia":"B","New Palasia":"B","Bhawarkuan":"B","Saket Nagar":"B","AB Road":"B","Rajendra Nagar":"C","Tilak Nagar":"C","Sudama Nagar":"C","Choithram":"C","Rau":"D","Annapurna":"C","Khajrana":"B","Mahalakshmi Nagar":"A","Nipania":"A","South Tukoganj":"B","Geeta Bhawan":"C","Indrapuri":"B","Super Corridor":"D"}
# APPROXIMATE area centres (not exact addresses, not verified against a survey map)
GEO={"Vijay Nagar":(22.753,75.894),"Scheme 54":(22.745,75.893),"Scheme 78":(22.752,75.903),"Bengali Square":(22.730,75.918),"Palasia":(22.724,75.884),"New Palasia":(22.730,75.880),"Bhawarkuan":(22.699,75.869),"Saket Nagar":(22.742,75.872),"Rajendra Nagar":(22.688,75.845),"Sudama Nagar":(22.686,75.826),"Rau":(22.654,75.804)}
def km(a,b):
    p=math.pi/180; x=math.sin((b[0]-a[0])*p/2)**2+math.cos(a[0]*p)*math.cos(b[0]*p)*math.sin((b[1]-a[1])*p/2)**2
    return 12742*math.asin(math.sqrt(x))
SUBJ = {"Accountancy":r"account","Business Studies":r"business stud|\bbst\b","Economics":r"econom","History":r"histor","Geography":r"geograph","Political Science":r"political|polity","Sociology":r"sociolog","Psychology":r"psycholog","Sanskrit":r"sanskrit","Mathematics":r"math|\bmaths?\b","Science":r"(?<!social )(?<!computer )(?<!political )\bscience\b","Physics":r"physics","Chemistry":r"chemistry","Biology":r"biology|\bbio\b","English":r"english","Hindi":r"hindi","Social Science":r"social|sst","Computer Science":r"computer|\bcs\b","EVS":r"\bevs\b"}
SCI = ["Physics","Chemistry","Biology"]
BOARDS=["CBSE","ICSE","MP Board"]; MEDIUMS=["English","Hindi"]; STREAMS=["Science","Commerce","Arts"]
CAT_SUBJ={"Classes 1-5":["English","Hindi","Mathematics","EVS","Sanskrit","Computer Science"],
"Classes 6-10":["English","Hindi","Sanskrit","Mathematics","Science","Social Science","Computer Science","Physics","Chemistry","Biology","History","Geography"],
"Class 11-12 Science":["Physics","Chemistry","Mathematics","Biology","English","Computer Science"],
"Class 11-12 Commerce":["Accountancy","Business Studies","Economics","Mathematics","English","Computer Science"],
"Class 11-12 Arts":["History","Political Science","Geography","Economics","Sociology","Psychology","Hindi","English"]}
ALLSUBJ=sorted({x for v in CAT_SUBJ.values() for x in v}|{"General Science"})
def pick(raw,allowed,what):
    out=[]
    for x in re.split(r"[;,]",raw or ""):
        k=x.strip().lower()
        if not k: continue
        a=next((v for v in allowed if v.lower()==k),None)
        if not a: raise HTTPException(400,f"Unknown {what}: {clean(x,30)}")
        if a not in out: out.append(a)
    return out
def check_profile(classes,subjects,board,medium,stream,strict=True):
    if not re.fullmatch(r"\d+-\d+",classes or ""): raise HTTPException(400,"Choose a class range such as 1-12")
    lo,hi=map(int,classes.split("-"))
    if not 1<=lo<=hi<=12: raise HTTPException(400,"Classes must be between 1 and 12")
    sb=pick(subjects,ALLSUBJ,"subject"); bd=pick(board,BOARDS,"board"); md=pick(medium,MEDIUMS,"medium"); st=pick(stream,STREAMS,"stream")
    if not sb: raise HTTPException(400,"Select at least one subject")
    if strict and (not bd or not md): raise HTTPException(400,"Select at least one board and one medium")
    if hi>=11 and not st: raise HTTPException(400,"Select at least one stream (Science, Commerce or Arts) for Classes 11-12")
    return classes,";".join(sb),", ".join(bd),";".join(md),";".join(st if hi>=11 else [])
W = dict(subject=30, cls=20, location=15, experience=15, budget=10, availability=5, qualification=5)
COLS = ["id","name","gender","qualification","experience","subjects","classes","locality","mode","fee","languages","availability","source"]

ALL=COLS+["bio","board","phone","verified","stream","medium"]
def ins(c,r):
    c.execute(f"insert into tutors({','.join(ALL)}) values({','.join('?'*len(ALL))})",[(r.get(k) if r.get(k) is not None else ("0" if k=="verified" else "")) for k in ALL])
def legacy(p): return hashlib.pbkdf2_hmac("sha256",p.encode(),b"tm-indore",20000).hex()
def hp(p):
    salt=secrets.token_hex(16); return "pbkdf2$%s$%s"%(salt,hashlib.pbkdf2_hmac("sha256",p.encode(),bytes.fromhex(salt),200000).hex())
def vp(p,h):
    if h and h.startswith("pbkdf2$"):
        _,salt,d=h.split("$"); return hmac.compare_digest(d,hashlib.pbkdf2_hmac("sha256",p.encode(),bytes.fromhex(salt),200000).hex())
    return hmac.compare_digest(h or "",legacy(p))
def clean(x,n=200): return html.escape(str(x or "").strip(),quote=False)[:n]
def admin_setup(c):
    c.execute("delete from users where email=? and role!='admin'",[ADMIN_USER]); a=c.execute("select * from users where role='admin' order by id limit 1").fetchone()
    if a: c.execute("update users set email=?,pw=?,name='Admin' where id=?",[ADMIN_USER,hp(ADMIN_PASS),a["id"]])
    else: c.execute("insert into users(role,email,pw,name) values('admin',?,?,'Admin')",[ADMIN_USER,hp(ADMIN_PASS)])
    c.execute("delete from users where role='admin' and email!=?",[ADMIN_USER])
tcode=lambda i:f"TM-T{int(i):03d}"
CODE_ALPHA="ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
def ch(code,salt): return hashlib.sha256((salt+re.sub(r"[^A-Z0-9]","",str(code).upper())).encode()).hexdigest()
def issue_code(c,tid):
    raw="".join(secrets.choice(CODE_ALPHA) for _ in range(10)); salt=secrets.token_hex(8)
    c.execute("insert or replace into claims(tutor_id,salt,code_hash) values(?,?,?)",[tid,salt,ch(raw,salt)]); c.commit(); return raw[:5]+"-"+raw[5:]
def db():
    c = sqlite3.connect(DB, timeout=10); c.row_factory = sqlite3.Row; return c
def init():
    c = db(); c.execute("create table if not exists tutors(id int,name,gender,qualification,experience int,subjects,classes,locality,mode,fee int,languages,availability,source)")
    c.execute("create table if not exists messages(id integer primary key autoincrement,tutor_id int,uid int,sender,text)")
    c.execute("create table if not exists requests(id integer primary key autoincrement,tutor_id int,kind,parent,cls,subject,date,time,message,status default 'Pending')")
    c.execute("create table if not exists claims(tutor_id integer primary key,salt text,code_hash text)")
    for col in ("bio text default ''","board text default ''","phone text default ''","verified int default 0","stream text default ''","medium text default ''"):
        try: c.execute("alter table tutors add column "+col)
        except sqlite3.OperationalError: pass
    c.execute("create table if not exists reviews(id integer primary key autoincrement,tutor_id int,uid int,name,stars int,text)")
    if not c.execute("select count(*) from tutors").fetchone()[0]:
        for r in csv.DictReader(open(os.path.join(ROOT,"data","tutors.csv"),encoding="utf-8")):
            ins(c,r)
    c.execute("create table if not exists users(id integer primary key autoincrement,role,email unique,pw,name,tutor_id int)")
    for r in csv.DictReader(open(os.path.join(ROOT,"data","tutors.csv"),encoding="utf-8")):   # backfill sample tutors made before Classes 1-12 / medium existed
        if r.get("medium"): c.execute("update tutors set classes=?,subjects=?,board=?,medium=?,stream=?,languages=?,qualification=?,fee=?,experience=? where id=? and source='SAMPLE' and coalesce(board,'')='' and coalesce(medium,'')=''",[r["classes"],r["subjects"],r["board"],r["medium"],r["stream"],r["languages"],r["qualification"],r["fee"],r["experience"],r["id"]])
    try: c.execute("alter table requests add column parent_id int")
    except sqlite3.OperationalError: pass
    c.execute("update requests set parent_id=(select id from users u where u.role='parent' and u.name=requests.parent) where parent_id is null and (select count(*) from users u where u.role='parent' and u.name=requests.parent)=1")
    try: c.execute("alter table messages add column created text")
    except sqlite3.OperationalError: pass
    for ix,n in (("requests(tutor_id)","a"),("requests(parent_id)","b"),("messages(tutor_id,uid)","c"),("reviews(tutor_id)","d")): c.execute(f"create index if not exists ix_{n} on {ix}")
    admin_setup(c)
    for u in c.execute("select id,pw from users where email like '%@demo.com'").fetchall():
        if vp("demo123",u["pw"]): c.execute("delete from users where id=?",[u["id"]])   # remove old predefined demo logins
    new=[]
    for t in c.execute("select id,name,locality from tutors where id not in (select tutor_id from users where tutor_id is not null) and id not in (select tutor_id from claims)").fetchall(): new.append((tcode(t["id"]),t["name"],t["locality"],issue_code(c,t["id"])))
    if new:
        with open(os.path.join(os.path.dirname(DB),"tutor_activation_codes.csv"),"a",encoding="utf-8",newline="") as f:
            w=csv.writer(f)
            if f.tell()==0: w.writerow(["Tutor ID","Name","Area","Activation code"])
            w.writerows(new)
        print(f"*** {len(new)} tutor activation codes saved in tutor_activation_codes.csv ***")
    c.commit(); c.close()
SESS={}
def admin(tok, write=False):
    u=user(tok)
    if u["role"]!="admin": raise HTTPException(403,"Admin only")
    return u
def user(tok):
    u=SESS.get(tok)
    if not u or u["exp"]<time.time(): SESS.pop(tok,None); raise HTTPException(401,"Please log in")
    return u
init()

def ratings(c): return {r[0]:(r[1],r[2]) for r in c.execute("select tutor_id,avg(stars),count(*) from reviews group by tutor_id")}
def tut(r, rt=None):
    d = dict(r); d["subjects"]=d["subjects"].split(";"); d["languages"]=d["languages"].split(";"); d["stream"]=[x for x in (d.get("stream") or "").split(";") if x]; d["medium"]=[x for x in (d.get("medium") or "").split(";") if x]; d["tutor_code"]=tcode(d["id"])
    d["classes"]=d["classes"] if re.fullmatch(r'\d+-\d+',d["classes"] or '') else '1-10'
    lo,hi = map(int,d["classes"].split("-")); d["class_range"]=[lo,hi]
    av = {}
    for s in filter(None,(d["availability"] or "").split(";")):
        day,t = s.split(); a,b = map(int,t.split("-")); av[day]=[a,b]
    d["availability"]=av; d["verified"]=bool(d.get("verified")); d["has_phone"]=bool(d.get("phone")); d.pop("phone",None)
    a=(rt or {}).get(d["id"],(None,0)); d["rating"]=round(a[0],1) if a[0] else None; d["reviews"]=a[1]
    return d

def teaches(t, s): return s in t["subjects"] or (s=="Science" and any(x in t["subjects"] for x in SCI))

def parse(text, ctx):
    t = text.lower(); q = dict(ctx or {})
    m = re.search(r"class\s*(\d+)|(\d+)(?:st|nd|rd|th)\s*(?:class|std|grade)|^\s*(\d{1,2})\s*$", t)
    if m: q["cls"] = int(m.group(1) or m.group(2) or m.group(3))
    t2 = re.sub(r"(hindi|english)[\s-]*medium","",t)
    s = [k for k,p in SUBJ.items() if re.search(p,t2)]
    if re.search(r"hindi[\s-]*medium",t): q["medium"] = "Hindi"
    elif re.search(r"english[\s-]*medium",t): q["medium"] = "English"
    if "commerce" in t: q["stream"] = "Commerce"
    elif re.search(r"\barts\b|humanities",t): q["stream"] = "Arts"
    elif re.search(r"science stream|\bpcm\b|\bpcb\b",t): q["stream"] = "Science"
    if s: q["subjects"] = s
    for loc in ZONES:
        if loc.lower() in t: q["location"] = loc
    m = re.search(r"(\d+)\+?\s*(?:years|yrs|year)", t)
    if m: q["min_exp"] = int(m.group(1))
    elif "experienced" in t: q["min_exp"] = 3
    m = re.search(r"(?:under|below|within|upto|up to|max|budget[^\d]{0,15}|₹|rs\.?)\s*(?:₹|rs\.?)?\s*(\d{3,5})", t) or re.search(r"(\d{3,5})\s*(?:/|per)\s*h", t)
    if m: q["budget"] = int(m.group(1))
    m = re.search(r"cbse|icse|mp board|state board", t)
    if m: q["board"] = m.group(0).upper()
    if re.search(r"female|woman|women|lad(?:y|ies)|daughter|madam|ma'am", t): q["gender"]="F"
    elif re.search(r"\bmale\b|\bsir\b", t): q["gender"]="M"
    days = [d for d in DAYS if re.search(FULL[d], t)]
    if days: q["days"] = days
    if "weekend" in t: q["days"] = ["Sat","Sun"]
    if "evening" in t: q["after"] = 16
    m = re.search(r"after\s*(\d{1,2})\s*(am|pm)?", t)
    if m:
        h = int(m.group(1)); q["after"] = h+12 if (m.group(2)=="pm" or (not m.group(2) and h<8)) and h<12 else h
    return q

def score(t, q):
    R = []; sc = 0; subs = q.get("subjects",[])
    hit = [s for s in subs if teaches(t,s)]
    f = len(hit)/len(subs) if subs else 1; sc += W["subject"]*f
    if hit: R.append(("ok","Teaches "+", ".join(hit)+("" if f==1 else f" ({len(hit)}/{len(subs)} requested subjects)")))
    sc += W["cls"]
    if "cls" in q: R.append(("ok",f"Teaches Class {q['cls']} (covers classes {t['classes']})"))
    if "location" in q:
        if t["locality"]==q["location"]: sc += W["location"]; R.append(("ok",f"Located in {t['locality']}"))
        elif ZONES.get(t["locality"])==ZONES.get(q["location"]): sc += W["location"]*.6; R.append(("part",f"Nearby area: {t['locality']}"))
        else: R.append(("no",f"Based in {t['locality']}, farther from {q['location']}"))
    else: sc += W["location"]
    e = t["experience"]
    if "min_exp" in q:
        if e>=q["min_exp"]: sc += W["experience"]; R.append(("ok",f"{e} years experience (needs {q['min_exp']}+)"))
        else: sc += W["experience"]*e/q["min_exp"]*.7; R.append(("no",f"{e} years experience, below {q['min_exp']}+"))
    else: sc += W["experience"]*min(e,8)/8; R.append(("ok",f"{e} years experience"))
    if "budget" in q:
        if t["fee"]<=q["budget"]: sc += W["budget"]; R.append(("ok",f"₹{t['fee']}/hr within ₹{q['budget']} budget"))
        else: sc += W["budget"]*max(0,1-(t["fee"]-q["budget"])/q["budget"]*2); R.append(("no",f"₹{t['fee']}/hr exceeds ₹{q['budget']} budget"))
    else: sc += W["budget"]
    if q.get("days") or q.get("after"):
        if not t["availability"]: R.append(("part","Availability not publicly specified — tutor confirmation required"))
        else:
            days = q.get("days") or list(t["availability"]); ok = []
            for d in days:
                w = t["availability"].get(d)
                if w and (not q.get("after") or w[1]>q["after"]): ok.append(d)
            f = len(ok)/len(days); sc += W["availability"]*f
            if ok: R.append(("ok" if f==1 else "part","Free "+", ".join(ok)+(f" after {q['after']-12} PM" if q.get("after") else "")))
            else: R.append(("no","No matching free slot"))
    else: sc += W["availability"]
    qual = t["qualification"]; qs = .2
    if "B.Ed" in qual: qs += .5
    qs += .5 if re.search(r"M\.|Ph", qual) else .3 if "B." in qual else 0
    sc += W["qualification"]*min(1,qs); R.append(("ok",f"Qualification: {qual}"))
    if q.get("medium"):
        if q["medium"] in t["medium"]: sc += 3; R.append(("ok",q["medium"]+" medium"))
        else: R.append(("part",("Teaches in "+"/".join(t["medium"])) if t["medium"] else "Medium not specified"))
    if q.get("stream"):
        if q["stream"] in t["stream"]: sc += 3; R.append(("ok",q["stream"]+" stream (Classes 11-12)"))
        else: R.append(("part",("Covers "+"/".join(t["stream"])+" stream") if t["stream"] else "Stream not specified"))
    if q.get("board"):
        bs=(t.get("board") or "").upper()
        if q["board"] in bs: sc += 3; R.append(("ok","Teaches "+q["board"]+" board"))
        else: R.append(("part",("Teaches "+t["board"]) if bs else "Board not specified"))
    if t.get("verified"): sc += 3; R.append(("ok","Verified by admin"))
    if t.get("rating"): sc += min(3,t["rating"]*.6); R.append(("ok",f"Rated {t['rating']}/5 by {t['reviews']} parent(s)"))
    if q.get("gender"):
        if t["gender"]==q["gender"]: sc += 3; R.append(("ok","Matches gender preference"))
        else: R.append(("part","Different from preferred gender"))
    return min(99,round(sc)), R

class Chat(BaseModel):
    message: str; context: dict = {}
class Req(BaseModel):
    tutor_id:int; kind:str="Demo"; parent:str=""; cls:str=""; subject:str=""; date:str=""; time:str=""; message:str=""

@app.post("/api/ai/search")
def ai(c: Chat):
    q = parse(c.message, c.context)
    if "cls" not in q: return {"parsed":q,"question":"What class is your child studying in? (Class 1–10)","results":[]}
    if not 1 <= q["cls"] <= 12: return {"parsed":{k:v for k,v in q.items() if k!="cls"},"question":"TutorMatch covers Classes 1-12. Which class is your child in?","results":[]}
    if not q.get("subjects"): return {"parsed":q,"question":"Which subject or subjects would you like help with?","results":[]}
    res = []
    c0 = db(); rt = ratings(c0)
    for r in c0.execute("select * from tutors"):
        t = tut(r, rt)
        if t["class_range"][0]<=q["cls"]<=t["class_range"][1] and any(teaches(t,s) for s in q["subjects"]):
            t["match"],t["reasons"] = score(t,q); res.append(t)
    res.sort(key=lambda x:-x["match"])
    return {"parsed":q,"question":None,"results":res[:6],"total_candidates":len(res)}

@app.get("/api/tutors")
def tutors():
    c = db(); rt = ratings(c); return [tut(r, rt) for r in c.execute("select * from tutors")]
class Login(BaseModel):
    role:str; email:str; password:str
class Sign(BaseModel):
    role:str; name:str=""; email:str; password:str; gender:str="F"; qualification:str=""; experience:int=0; subjects:str=""; classes:str="1-10"; locality:str="Vijay Nagar"; fee:int=300; board:str=""; medium:str=""; stream:str=""
class Msg(BaseModel):
    text:str; uid:int=0; sender:str=""
class Av(BaseModel):
    availability:str

FAIL={}
def throttle(key):
    now=time.time(); a=[t for t in FAIL.get(key,[]) if now-t<600]; FAIL[key]=a
    if len(a)>=5: raise HTTPException(429,"Too many failed attempts. Try again in 10 minutes.")
@app.post("/api/auth/login")
def login(l:Login):
    c=db(); ident=l.email.lower().strip(); throttle(ident); u=None; m=re.fullmatch(r"tm-t0*(\d+)",ident)
    if l.role=="tutor" and m: u=c.execute("select * from users where role='tutor' and tutor_id=?",[int(m.group(1))]).fetchone()
    elif l.role in("parent","tutor","admin"): u=c.execute("select * from users where email=? and role=?",[ident,l.role]).fetchone()
    if not u or not vp(l.password,u["pw"]):
        FAIL.setdefault(ident,[]).append(time.time()); raise HTTPException(401,"Invalid ID/email or password for this account type")
    if not u["pw"].startswith("pbkdf2$"): c.execute("update users set pw=? where id=?",[hp(l.password),u["id"]]); c.commit()
    FAIL.pop(ident,None); tok=secrets.token_hex(24); SESS[tok]=dict(u,exp=time.time()+43200)
    return {"token":tok,"user":{"name":u["name"],"role":u["role"],"tutor_id":u["tutor_id"],"tutor_code":tcode(u["tutor_id"]) if u["tutor_id"] else None}}

class Claim(BaseModel):
    tutor_id:str; code:str; password:str; email:str=""
@app.post("/api/auth/claim")
def claim(b:Claim):
    c=db(); key="claim:"+b.tutor_id.lower().strip(); throttle(key); m=re.fullmatch(r"tm-t0*(\d+)",b.tutor_id.lower().strip())
    row=c.execute("select * from claims where tutor_id=?",[int(m.group(1))]).fetchone() if m else None
    if not row or not hmac.compare_digest(row["code_hash"],ch(b.code,row["salt"])):
        FAIL.setdefault(key,[]).append(time.time()); raise HTTPException(400,"Tutor ID or activation code is not valid")
    if len(b.password)<8: raise HTTPException(400,"Choose a password of 8+ characters")
    tid=row["tutor_id"]; t=c.execute("select * from tutors where id=?",[tid]).fetchone(); u=c.execute("select * from users where role='tutor' and tutor_id=?",[tid]).fetchone()
    if u: c.execute("update users set pw=? where id=?",[hp(b.password),u["id"]])
    else:
        email=b.email.lower().strip()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",email): raise HTTPException(400,"Enter a valid email address")
        if c.execute("select 1 from users where email=?",[email]).fetchone(): raise HTTPException(400,"Email already registered")
        c.execute("insert into users(role,email,pw,name,tutor_id) values('tutor',?,?,?,?)",[email,hp(b.password),t["name"],tid])
    c.execute("delete from claims where tutor_id=?",[tid]); c.commit(); FAIL.pop(key,None)
    return login(Login(role="tutor",email=tcode(tid),password=b.password))

@app.post("/api/auth/signup")
def signup(s:Sign):
    c=db(); email=s.email.lower().strip(); name=clean(s.name,80)
    if s.role not in("parent","tutor") or not name or len(s.password)<8 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",email): raise HTTPException(400,"Enter your name, a valid email and a password of 8+ characters")
    if c.execute("select 1 from users where email=?",[email]).fetchone(): raise HTTPException(400,"Email already registered")
    tid=None
    if s.role=="tutor":
        if s.gender not in("F","M") or not(0<=s.experience<=60) or not(50<=s.fee<=5000) or s.locality not in ZONES: raise HTTPException(400,"Check gender, experience, fee (50-5000) and locality")
        cl,subs,bd,md,st=check_profile(s.classes,s.subjects,s.board,s.medium,s.stream)
        tid=c.execute("select coalesce(max(id),0)+1 from tutors").fetchone()[0]
        ins(c,dict(id=tid,name=name,gender=s.gender,qualification=clean(s.qualification,100) or "Not publicly specified",experience=s.experience,subjects=subs,classes=cl,locality=s.locality,mode="Home Tuition",fee=s.fee,languages=md,availability="",source="Self-registered",board=bd,medium=md,stream=st))
    c.execute("insert into users(role,email,pw,name,tutor_id) values(?,?,?,?,?)",[s.role,email,hp(s.password),name,tid]); c.commit()
    return login(Login(role=s.role,email=email,password=s.password))

def busy(c,tid,date,tm,exclude=0):
    if not date or not tm: return False
    h=lambda x:int(x[:2])*60+int(x[3:5])
    return any(abs(h(r["time"])-h(tm))<60 for r in c.execute("select time from requests where tutor_id=? and date=? and status='Accepted' and id!=? and time!=''",[tid,date,exclude]))
@app.post("/api/requests")
def mk(r:Req, x_token:str=Header(None)):
    u=user(x_token)
    if u["role"]!="parent": raise HTTPException(403,"Only parents can send requests")
    c=db(); t=c.execute("select * from tutors where id=?",[r.tutor_id]).fetchone()
    if not t: raise HTTPException(404,"Tutor not found")
    t=tut(t)
    if r.kind not in("Demo","Tutor"): raise HTTPException(400,"Invalid request type")
    if r.subject not in t["subjects"]: raise HTTPException(400,"This tutor does not list that subject")
    if not re.fullmatch(r"\d{1,2}",r.cls.strip()) or not 1<=int(r.cls)<=12: raise HTTPException(400,"Enter the class as a number from 1 to 12")
    if not t["class_range"][0]<=int(r.cls)<=t["class_range"][1]: raise HTTPException(400,"This tutor does not teach that class")
    try: d=datetime.date.fromisoformat(r.date); tm=datetime.time.fromisoformat(r.time)
    except ValueError: raise HTTPException(400,"Choose a valid date and time")
    if datetime.datetime.combine(d,tm)<=datetime.datetime.now(): raise HTTPException(400,"Choose a future date and time")
    w=t["availability"].get(DAYS[d.weekday()]); mins=tm.hour*60+tm.minute
    if t["availability"] and not(w and w[0]*60<=mins and mins+60<=w[1]*60): raise HTTPException(400,"The tutor is not free at that time. Check their weekly availability")
    ds,ts=d.isoformat(),tm.strftime("%H:%M")
    if busy(c,t["id"],ds,ts): raise HTTPException(409,"That slot is already booked. Pick another time")
    if c.execute("select 1 from requests where tutor_id=? and parent_id=? and date=? and time=? and status in('Pending','Accepted')",[t["id"],u["id"],ds,ts]).fetchone(): raise HTTPException(409,"You already have a request for that slot")
    c.execute("insert into requests(tutor_id,kind,parent,parent_id,cls,subject,date,time,message) values(?,?,?,?,?,?,?,?,?)",[t["id"],r.kind,u["name"],u["id"],r.cls.strip(),r.subject,ds,ts,clean(r.message,500)]); c.commit(); return {"ok":True}
@app.get("/api/requests")
def reqs(x_token:str=Header(None), all:int=0):
    u=user(x_token); q="select r.*,t.name tutor from requests r join tutors t on t.id=r.tutor_id"; a=[]
    if all: admin(x_token)
    elif u["role"]=="tutor": q+=" where r.tutor_id=?"; a=[u["tutor_id"]]
    elif u["role"]=="parent": q+=" where r.parent_id=?"; a=[u["id"]]
    else: q+=" where 0"
    return [dict(x) for x in db().execute(q+" order by r.id desc",a)]
@app.post("/api/requests/{rid}/{st}")
def setst(rid:int, st:str, x_token:str=Header(None)):
    u=user(x_token); c=db(); r=c.execute("select * from requests where id=?",[rid]).fetchone()
    if not r: raise HTTPException(404,"Request not found")
    if st not in("Accepted","Rejected","Completed","Cancelled"): raise HTTPException(400,"Invalid status")
    if u["role"]=="parent":
        if r["parent_id"]!=u["id"] or st!="Cancelled" or r["status"] not in("Pending","Accepted"): raise HTTPException(403,"Parents can only cancel their own open requests")
    elif u["role"]=="tutor":
        if r["tutor_id"]!=u["tutor_id"]: raise HTTPException(403,"Not your request")
        if st not in {"Pending":("Accepted","Rejected"),"Accepted":("Completed","Rejected")}.get(r["status"],()): raise HTTPException(409,f"A {r['status']} request cannot become {st}")
        if st=="Accepted" and busy(c,r["tutor_id"],r["date"],r["time"],rid): raise HTTPException(409,"You already have an accepted booking at that time")
    else: raise HTTPException(403,"Not allowed")
    c.execute("update requests set status=? where id=?",[st,rid]); c.commit(); return {"ok":True}
@app.get("/api/conversations")
def conv_list(x_token:str=Header(None)):
    u=user(x_token); c=db()
    if u["role"]=="admin":
        out={}
        for r in c.execute("select m.*,t.name tname,p.name pname from messages m join tutors t on t.id=m.tutor_id join users p on p.id=m.uid order by m.id"):
            k=f'{r["tutor_id"]}-{r["uid"]}'; out.pop(k,None); out[k]={"id":k,"name":f'{r["pname"]} ↔ {r["tname"]}',"last":r["text"]}
        return list(reversed(list(out.values())))
    if u["role"] not in("parent","tutor"): raise HTTPException(403,"Not allowed")
    par=u["role"]=="parent"; out={}
    for r in c.execute("select m.*,t.name tname,p.name pname from messages m join tutors t on t.id=m.tutor_id join users p on p.id=m.uid where "+("m.uid=?" if par else "m.tutor_id=?")+" order by m.id",[u["id"] if par else u["tutor_id"]]):
        k=r["tutor_id"] if par else r["uid"]; out.pop(k,None); out[k]={"id":k,"name":r["tname"] if par else r["pname"],"last":r["text"]}
    return list(reversed(list(out.values())))
@app.get("/api/admin/thread/{tid}/{uid}")
def admin_thread(tid:int,uid:int,x_token:str=Header(None)):
    admin(x_token); c=db()
    rows=c.execute("select m.*,t.name tname,p.name pname from messages m join tutors t on t.id=m.tutor_id join users p on p.id=m.uid where m.tutor_id=? and m.uid=? order by m.id",[tid,uid]).fetchall()
    return [{"text":r["text"],"mine":r["sender"]=="Tutor","who":r["pname"] if r["sender"]=="Parent" else r["tname"],"at":(r["created"] or "")[:16]} for r in rows]
@app.get("/api/thread/{peer}")
def thread_get(peer:int,x_token:str=Header(None)):
    u=user(x_token); c=db()
    if u["role"]=="parent": rows=c.execute("select * from messages where tutor_id=? and uid=? order by id",[peer,u["id"]]).fetchall()
    elif u["role"]=="tutor": rows=c.execute("select * from messages where tutor_id=? and uid=? order by id",[u["tutor_id"],peer]).fetchall()
    else: raise HTTPException(403,"Not allowed")
    me="Parent" if u["role"]=="parent" else "Tutor"
    return [{"text":r["text"],"mine":r["sender"]==me,"at":(r["created"] or "")[:16]} for r in rows]
@app.post("/api/thread/{peer}")
def thread_send(peer:int,m:Msg,x_token:str=Header(None)):
    u=user(x_token); c=db(); text=m.text.strip()[:500]
    if not text: raise HTTPException(400,"Write a message first")
    if u["role"]=="parent":
        if not c.execute("select 1 from tutors where id=?",[peer]).fetchone(): raise HTTPException(404,"Tutor not found")
        tid,uid,snd=peer,u["id"],"Parent"
    elif u["role"]=="tutor":
        tid,uid,snd=u["tutor_id"],peer,"Tutor"
        if not c.execute("select 1 from messages where tutor_id=? and uid=?",[tid,uid]).fetchone(): raise HTTPException(403,"You can reply once a parent has written to you")
    else: raise HTTPException(403,"Not allowed")
    c.execute("insert into messages(tutor_id,uid,sender,text,created) values(?,?,?,?,?)",[tid,uid,snd,text,datetime.datetime.now().strftime("%Y-%m-%d %H:%M")]); c.commit(); return {"ok":True}
@app.get("/api/messages/{tid}")
def gm(tid:int, x_token:str=Header(None)):
    u=user(x_token)
    if u["role"]=="tutor" and u["tutor_id"]!=tid: raise HTTPException(403,"Not your inbox")
    q="select m.*,u.name pname from messages m join users u on u.id=m.uid where m.tutor_id=?"; a=[tid]
    if u["role"]=="parent": q+=" and m.uid=?"; a.append(u["id"])
    return [dict(x) for x in db().execute(q+" order by m.id",a)]
@app.post("/api/messages/{tid}")
def pm(tid:int, m:Msg, x_token:str=Header(None)):
    u=user(x_token)
    if u["role"]=="tutor":
        if u["tutor_id"]!=tid or not m.uid: raise HTTPException(403,"Not allowed")
        uid,snd=m.uid,"Tutor"
    elif u["role"]=="parent": uid,snd=u["id"],"Parent"
    else: raise HTTPException(403,"Not allowed")
    if not m.text.strip() or not db().execute("select 1 from tutors where id=?",[tid]).fetchone() or (u["role"]=="tutor" and not db().execute("select 1 from users where id=? and role='parent'",[uid]).fetchone()): raise HTTPException(400,"Invalid message")
    c=db(); c.execute("insert into messages(tutor_id,uid,sender,text,created) values(?,?,?,?,?)",[tid,uid,snd,m.text[:500],datetime.datetime.now().strftime("%Y-%m-%d %H:%M")]); c.commit(); return {"ok":True}
@app.post("/api/tutors/{tid}/availability")
def sa(tid:int, a:Av, x_token:str=Header(None)):
    u=user(x_token)
    if u["role"]!="tutor" or u["tutor_id"]!=tid: raise HTTPException(403,"You can only edit your own availability")
    c=db(); c.execute("update tutors set availability=? where id=?",[a.availability,tid]); c.commit(); return {"ok":True}
class Prof(BaseModel):
    bio:str=""; board:str=""; phone:str=""; fee:int=300; classes:str=""; subjects:str=""; medium:str=""; stream:str=""
class Rev(BaseModel):
    stars:int; text:str=""
class Imp(BaseModel):
    csv_text:str
def accepted(c,tid,u): return u["role"]=="parent" and c.execute("select 1 from requests where tutor_id=? and parent_id=? and status in('Accepted','Completed')",[tid,u["id"]]).fetchone()
@app.post("/api/admin/claim/{tid}")
def newcode(tid:int,x_token:str=Header(None)):
    admin(x_token); c=db(); t=c.execute("select name from tutors where id=?",[tid]).fetchone()
    if not t: raise HTTPException(404,"Tutor not found")
    return {"tutor_id":tcode(tid),"name":t["name"],"code":issue_code(c,tid)}
@app.get("/api/admin/stats")
def astats(x_token:str=Header(None)):
    admin(x_token); c=db(); n=lambda q:c.execute(q).fetchone()[0]; rows=lambda q:[dict(r) for r in c.execute(q)]; rv=c.execute("select count(*),avg(stars) from reviews").fetchone()
    return {"tutors":n("select count(*) from tutors"),"verified":n("select count(*) from tutors where verified=1"),"parents":n("select count(*) from users where role='parent'"),"requests":n("select count(*) from requests"),"reviews":rv[0],"avg_rating":round(rv[1],1) if rv[1] else None,
      "by_status":rows("select status k,count(*) n from requests group by status order by n desc"),"by_locality":rows("select locality k,count(*) n from tutors group by locality order by n desc limit 8"),"by_class":rows("select cls k,count(*) n from requests where cls!='' group by cls order by n desc limit 6"),"claimed":[r[0] for r in c.execute("select tutor_id from users where tutor_id is not null")]}
@app.get("/api/requests/{rid}/ics")
def ics(rid:int,x_token:str=Header(None)):
    u=user(x_token); c=db(); r=c.execute("select r.*,t.name tutor from requests r join tutors t on t.id=r.tutor_id where r.id=?",[rid]).fetchone()
    mine=r and ((u["role"]=="parent" and r["parent_id"]==u["id"]) or (u["role"]=="tutor" and r["tutor_id"]==u["tutor_id"]))
    if not r or not mine or r["status"]!="Accepted" or not r["date"] or not r["time"]: raise HTTPException(404,"Accepted session not found")
    st=datetime.datetime.fromisoformat(r["date"]+"T"+r["time"]); fm=lambda d:d.strftime("%Y%m%dT%H%M%S")
    body="\r\n".join(["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//TutorMatch Indore//EN","BEGIN:VEVENT",f"UID:tm-{rid}@tutormatch.local","DTSTAMP:"+fm(datetime.datetime.now(datetime.timezone.utc))+"Z","DTSTART:"+fm(st),"DTEND:"+fm(st+datetime.timedelta(hours=1)),("SUMMARY:"+r["subject"]+" class with "+r["tutor"]).replace(",",";"),"END:VEVENT","END:VCALENDAR"])+"\r\n"
    return Response(body,media_type="text/calendar",headers={"Content-Disposition":f'attachment; filename="tutor-session-{rid}.ics"'})
@app.get("/api/catalog")
def catalog(): return {"boards":BOARDS,"mediums":MEDIUMS,"streams":STREAMS,"subjects":CAT_SUBJ,"all_subjects":ALLSUBJ,"localities":sorted(ZONES)}
@app.get("/api/nearby")
def nearby(lat:float,lng:float,limit:int=12):
    if not(22.4<=lat<=23.1 and 75.5<=lng<=76.2): raise HTTPException(400,"Your location is outside the Indore area")
    c=db(); rt=ratings(c); out=[]
    for r in c.execute("select * from tutors"):
        t=tut(r,rt); g=GEO.get(t["locality"])
        if g: t["distance_km"]=round(km((lat,lng),g),1); out.append(t)
    return sorted(out,key=lambda x:x["distance_km"])[:max(1,min(limit,200))]
@app.post("/api/tutors/{tid}/profile")
def sp(tid:int,p:Prof,x_token:str=Header(None)):
    u=user(x_token)
    if u["role"]!="tutor" or u["tutor_id"]!=tid: raise HTTPException(403,"You can only edit your own profile")
    c=db(); cur=tut(c.execute("select * from tutors where id=?",[tid]).fetchone())
    if p.subjects or p.classes or p.board or p.medium or p.stream:
        cl,sb,bd,md,st=check_profile(p.classes or cur["classes"],p.subjects or ";".join(cur["subjects"]),p.board or cur["board"],p.medium or ";".join(cur["medium"]),p.stream or ";".join(cur["stream"]),strict=False)
        c.execute("update tutors set classes=?,subjects=?,board=?,medium=?,stream=?,languages=? where id=?",[cl,sb,bd,md,st,md,tid])
    c.execute("update tutors set bio=?,phone=coalesce(nullif(?,''),phone),fee=? where id=?",[clean(p.bio,400),re.sub(r"[^\d+]","",p.phone)[:15],max(50,min(5000,p.fee)),tid]); c.commit(); return {"ok":True}
@app.get("/api/tutors/{tid}/contact")
def contact(tid:int,x_token:str=Header(None)):
    u=user(x_token); c=db()
    if not accepted(c,tid,u): raise HTTPException(403,"Phone is shared once the tutor accepts your request")
    return {"phone":c.execute("select phone from tutors where id=?",[tid]).fetchone()[0] or ""}
@app.get("/api/reviews/{tid}")
def gr(tid:int): return [dict(x) for x in db().execute("select name,stars,text from reviews where tutor_id=? order by id desc",[tid])]
@app.post("/api/reviews/{tid}")
def pr(tid:int,r:Rev,x_token:str=Header(None)):
    u=user(x_token); c=db()
    if not accepted(c,tid,u): raise HTTPException(403,"Only parents with an accepted request can review")
    if c.execute("select 1 from reviews where tutor_id=? and uid=?",[tid,u["id"]]).fetchone(): raise HTTPException(400,"You already reviewed this tutor")
    c.execute("insert into reviews(tutor_id,uid,name,stars,text) values(?,?,?,?,?)",[tid,u["id"],u["name"],max(1,min(5,r.stars)),r.text[:300]]); c.commit(); return {"ok":True}
@app.post("/api/admin/verify/{tid}")
def ver(tid:int,x_token:str=Header(None)):
    admin(x_token); c=db(); c.execute("update tutors set verified=1-coalesce(verified,0) where id=?",[tid]); c.commit(); return {"ok":True}
@app.post("/api/admin/import")
def imp(i:Imp,x_token:str=Header(None)):
    admin(x_token,True); c=db(); n=0; bad=[]; codes=[]
    for k,r in enumerate(list(csv.DictReader(io.StringIO(i.csv_text[:500000])))[:500],2):
        try:
            g=(r.get("gender") or "F").strip().upper()[:1]; cl=(r.get("classes") or "1-10").strip(); lo,hi=map(int,cl.split("-"))
            av=(r.get("availability") or "").strip()
            assert g in("F","M") and 1<=lo<=hi<=12 and 0<=int(r.get("experience") or 0)<=60 and 50<=int(r.get("fee") or 0)<=5000 and (r.get("name") or "").strip()
            assert not av or re.fullmatch(r"[A-Z][a-z]{2} \d{1,2}-\d{1,2}(;[A-Z][a-z]{2} \d{1,2}-\d{1,2})*",av)
            o={f:clean(r.get(f),400 if f=="bio" else 120) for f in ("name","qualification","locality","languages","bio")}
            o["subjects"]=";".join(pick(r.get("subjects"),ALLSUBJ,"subject")); o["board"]=", ".join(pick(r.get("board"),BOARDS,"board")); o["medium"]=";".join(pick(r.get("medium"),MEDIUMS,"medium")); o["stream"]=";".join(pick(r.get("stream"),STREAMS,"stream")); assert o["subjects"]
            src=clean(r.get("source") or "Public listing",40); o.update(id=c.execute("select coalesce(max(id),0)+1 from tutors").fetchone()[0],gender=g,classes=cl,experience=int(r.get("experience") or 0),fee=int(r.get("fee") or 0),mode="Home Tuition",availability=av,source="Public listing" if src.upper()=="SAMPLE" else src,phone=re.sub(r"[^\d+]","",r.get("phone") or "")[:15],verified=0)
            ins(c,o); n+=1; codes.append({"tutor_id":tcode(o["id"]),"name":o["name"],"code":issue_code(c,o["id"])})
        except Exception: bad.append(k)
    c.commit(); return {"imported":n,"skipped_rows":bad,"codes":codes}
@app.post("/api/admin/clear-demo")
def cd(x_token:str=Header(None)):
    admin(x_token,True); c=db(); c.execute("delete from tutors where source='SAMPLE'"); c.execute("delete from users where role='tutor' and tutor_id not in (select id from tutors)")
    for tb in ("requests","messages","reviews","claims"): c.execute(f"delete from {tb} where tutor_id not in (select id from tutors)")
    c.commit(); return {"ok":True}
app.mount("/", StaticFiles(directory=os.path.join(ROOT,"frontend"), html=True), name="f")
