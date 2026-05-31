#!/usr/bin/env python3
# One-way mirror: AndresASJ/FlacPlayer TODO.md (open items) -> Todoist (label "FlacPlayer").
# File = source of truth. Matching is by a stable fpid hash stored in each task's
# description (Todoist mangles @/# in titles, so we never match on title text).
# @ and # in titles are backslash-escaped so they display intact and don't create
# junk labels/projects. Read-only on the repo. Installed by Claude 2026-05-31.
import json, subprocess, base64, re, hashlib, urllib.request, urllib.error
TOK=open("/root/.config/flac-sync/todoist.token").read().strip()
API="https://api.todoist.com/api/v1"; H={"Authorization":"Bearer "+TOK,"Content-Type":"application/json"}
REPO="AndresASJ/FlacPlayer"; LABEL="FlacPlayer"
def td(method,path,body=None):
    r=urllib.request.Request(API+path,data=(json.dumps(body).encode() if body is not None else None),headers=H,method=method)
    try:
        with urllib.request.urlopen(r,timeout=30) as resp:
            t=resp.read().decode(); return resp.status,(json.loads(t) if t else {})
    except urllib.error.HTTPError as e: return e.code,e.read().decode()
def label_tasks():
    out=[];c=None
    while True:
        s,d=td("GET","/tasks?label="+LABEL+(("&cursor="+c) if c else ""))
        if not isinstance(d,dict): break
        out+=d.get("results",[]); c=d.get("next_cursor")
        if not c: break
    return out
def parse():
    raw=subprocess.run(["gh","api",f"repos/{REPO}/contents/TODO.md","-q",".content"],capture_output=True,text=True).stdout
    md=base64.b64decode(raw).decode("utf-8","replace"); L=md.splitlines()
    cl=lambda s: re.sub(r'\[(.*?)\]\(.*?\)',r'\1',re.sub(r'`([^`]*)`',r'\1',re.sub(r'\*\*(.*?)\*\*',r'\1',s))).strip()
    items=[]; sec=None; i=0
    while i<len(L):
        h=re.match(r'^##\s+(.*)',L[i])
        if h: sec=h.group(1).strip(); i+=1; continue
        m=re.match(r'^(\s*)-\s\[ \]\s+(.*)',L[i])
        if m:
            ind=len(m.group(1)); body=cl(m.group(2)); j=i+1; cont=[]
            while j<len(L) and L[j].strip() and not re.match(r'^\s*-\s\[[ xX]\]',L[j]) and (len(L[j])-len(L[j].lstrip()))>ind:
                cont.append(cl(L[j])); j+=1
            full=body+((' '+' '.join(cont)) if cont else '')
            mm=re.match(r'(.+?[.:])(\s+|$)(.*)',full,re.S)
            if mm and len(mm.group(1))<=80: title=mm.group(1).rstrip('.:').strip(); desc=(mm.group(3) or '').strip()
            else: title=full[:80].strip(); desc=full[80:].strip()
            items.append({"section":sec,"title":title[:400],"desc":desc}); i=j; continue
        i+=1
    return items
def fpid(title): return hashlib.md5(" ".join(title.lower().split()).encode()).hexdigest()[:12]
def esc(s): return s.replace("@","\\@").replace("#","\\#")
items=parse()
want={fpid(it["title"]):it for it in items}
existing={}
for t in label_tasks():
    m=re.search(r'fpid:([0-9a-f]{12})',t.get("description") or "")
    if m: existing[m.group(1)]=t
created=completed=0
for fid,it in want.items():
    if fid in existing: continue
    desc=("["+it["section"]+"]\n"+it["desc"]).strip() if it.get("section") else (it.get("desc") or "")
    desc=(desc+"\n\nfpid:"+fid).strip()
    s,_=td("POST","/tasks",{"content":esc(it["title"]),"labels":[LABEL],"description":desc[:9000]})
    if s==200: created+=1
for fid,t in existing.items():
    if fid not in want:
        s,_=td("POST","/tasks/"+t["id"]+"/close")
        if s in (200,204): completed+=1
print(f"flac-sync: open_in_file={len(items)} created={created} completed={completed}")
