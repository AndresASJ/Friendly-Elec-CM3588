#!/usr/bin/env python3
# Sync iCloud contacts (CardDAV) -> a `contacts` table in the n8n Postgres DB,
# so the n8n capture flow can look up name -> phone for tap-to-call/text links.
# Read-only on iCloud. Cred on drive1. Installed by Claude 2026-05-31.
import urllib.request, ssl, re, html, base64, subprocess, json
CRED="/mnt/drive1/AppData/contacts-sync/icloud.cred"
U,P=[x.strip() for x in open(CRED).read().splitlines() if x.strip()][:2]
AUTH="Basic "+base64.b64encode(f"{U}:{P}".encode()).decode()
def dav(method,url,body=None,depth="0"):
    h={"Authorization":AUTH,"Depth":depth,"Content-Type":"text/xml; charset=utf-8"}
    r=urllib.request.Request(url,data=(body.encode() if body else None),headers=h,method=method)
    return urllib.request.urlopen(r,timeout=40).read().decode("utf-8","replace")
# discover
root="https://contacts.icloud.com/"
b=dav("PROPFIND",root,'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:current-user-principal/></d:prop></d:propfind>')
prin=re.search(r'current-user-principal>\s*<href>([^<]+)</href>',b).group(1)
b=dav("PROPFIND","https://contacts.icloud.com"+prin,'<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:carddav"><d:prop><c:addressbook-home-set/></d:prop></d:propfind>')
home=re.search(r'addressbook-home-set[^>]*>\s*<href[^>]*>([^<]+)</href>',b).group(1).strip()
b=dav("PROPFIND",home,'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:resourcetype/></d:prop></d:propfind>',depth="1")
hrefs=re.findall(r'<href>([^<]+/card/)</href>',b)
from urllib.parse import urlparse
host=f"{urlparse(home).scheme}://{urlparse(home).netloc}"
card=host+hrefs[0] if hrefs else home+"card/"
b=dav("REPORT",card,'<?xml version="1.0"?><c:addressbook-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:carddav"><d:prop><c:address-data/></d:prop></c:addressbook-query>',depth="1")
cards=re.findall(r'<address-data[^>]*>(.*?)</address-data>',b,re.S)
rows=[]
for c in cards:
    v=html.unescape(c); fn=None; tels=[]
    for line in v.splitlines():
        up=line.upper()
        if up.startswith("FN") and ":" in line: fn=line.split(":",1)[1].strip()
        elif up.startswith("TEL") and ":" in line: tels.append(line.split(":",1)[1].strip())
    if fn and tels:
        for t in tels:
            tel=re.sub(r'[^\d+]','',t)
            rows.append((fn, fn.lower(), t.strip(), tel))
# write to postgres via docker exec
sql="DROP TABLE IF EXISTS contacts; CREATE TABLE contacts(name text, name_lower text, phone_raw text, phone_tel text);"
for nm,nl,raw,tel in rows:
    e=lambda s: s.replace("'","''")
    sql+=f"INSERT INTO contacts VALUES ('{e(nm)}','{e(nl)}','{e(raw)}','{e(tel)}');"
subprocess.run(["docker","exec","-i","n8n-postgres","psql","-U","n8n","-d","n8n","-q"],input=sql,text=True,check=True)
print(f"contacts-sync: {len(cards)} vCards, {len(rows)} name/number rows written")
