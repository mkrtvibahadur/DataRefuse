from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3, os, re
from datetime import datetime
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'datarefuse-local-prototype')
DB = os.path.join(os.path.dirname(__file__), 'datarefuse.db')

# Categories are intentionally broad discovery prompts, not verified claims about every app.
APPS = [
 {'name':'Swiggy','category':'Food & shopping','purpose':'Food ordering and delivery','collects':['Account and contact details','Delivery address and location-related information','Order and payment activity','Device and app usage information'],'policy':'https://www.swiggy.com/privacy-policy','alternative':'Order directly from a restaurant where possible; compare its own ordering and payment practices.'},
 {'name':'Zomato','category':'Food & shopping','purpose':'Restaurant discovery and food delivery','collects':['Account and contact details','Delivery address and location-related information','Search, order and payment activity','Device and app usage information'],'policy':'https://www.zomato.com/policies/privacy/','alternative':'Order directly from a restaurant where possible; compare its own ordering and payment practices.'},
 {'name':'Blinkit','category':'Food & shopping','purpose':'Quick-commerce grocery and essentials delivery','collects':['Account and contact details','Delivery address and location-related information','Order and payment activity','Device and app usage information'],'policy':'https://blinkit.com/terms','alternative':'Buy from a nearby shop in person or use its direct ordering channel, if available.'},
 {'name':'Zepto','category':'Food & shopping','purpose':'Quick-commerce grocery and essentials delivery','collects':['Account and contact details','Delivery address and location-related information','Order and payment activity','Device and app usage information'],'policy':'https://www.zepto.com/','alternative':'Buy from a nearby shop in person or use its direct ordering channel, if available.'},
 {'name':'Instagram','category':'Social & communication','purpose':'Photo/video sharing and messaging','collects':['Profile and contact details','Content and communications metadata','Interactions, searches and usage activity','Device, network and location-related information'],'policy':'https://privacycenter.instagram.com/policy/','alternative':'Pixelfed for photo sharing; it is a different service with a different feature set.'},
 {'name':'Snapchat','category':'Social & communication','purpose':'Visual messaging and social sharing','collects':['Account and contact details','Snaps, chats and interaction information (subject to product settings)','Device and usage information','Location information when relevant permissions/features are enabled'],'policy':'https://values.snap.com/privacy/privacy-policy','alternative':'Signal for private messaging; it does not replace Snapchat’s social and camera features.'},
 {'name':'WhatsApp','category':'Social & communication','purpose':'Messaging and voice/video calls','collects':['Account and contact details','Messaging and call-related metadata','Device and connection information','Optional location or contact information when shared/permitted'],'policy':'https://www.whatsapp.com/legal/privacy-policy','alternative':'Signal for messaging; compare features, contacts’ adoption and each service’s current policy.'},
 {'name':'Facebook','category':'Social & communication','purpose':'Social networking and content sharing','collects':['Profile and contact details','Posts, interactions and connections','Device, network and usage information','Location-related information depending on settings and use'],'policy':'https://www.facebook.com/privacy/policy/','alternative':'A smaller private group, forum or direct communication channel may avoid a large social network.'},
 {'name':'Uber','category':'Travel & mobility','purpose':'Ride-hailing and delivery services','collects':['Rider account and contact details','Pickup/drop-off and trip information','Location information depending on permissions and trip use','Payment, device and usage information'],'policy':'https://www.uber.com/legal/en/document/?name=privacy-notice','alternative':'Public transport, walking/cycling for suitable trips, or local taxi services; data practices vary.'},
 {'name':'Ola','category':'Travel & mobility','purpose':'Ride-hailing','collects':['Account and contact details','Pickup/drop-off and trip information','Location information depending on permissions and trip use','Payment, device and usage information'],'policy':'https://www.olacabs.com/info/privacy','alternative':'Public transport, walking/cycling for suitable trips, or local taxi services; data practices vary.'},
 {'name':'Rapido','category':'Travel & mobility','purpose':'Bike taxi and mobility services','collects':['Account and contact details','Pickup/drop-off and trip information','Location information depending on permissions and trip use','Payment, device and usage information'],'policy':'https://www.rapido.bike/Privacy','alternative':'Public transport, walking/cycling for suitable trips, or local taxi services; data practices vary.'},
 {'name':'Google Maps','category':'Travel & mobility','purpose':'Navigation, maps and local discovery','collects':['Searches and navigation activity','Location information depending on settings','Device and diagnostic information','Saved places, contributions and account-linked activity'],'policy':'https://policies.google.com/privacy','alternative':'Organic Maps for offline maps; compare coverage and the data required for features you use.'},
 {'name':'Netflix','category':'Entertainment & video','purpose':'Film and television streaming','collects':['Account and billing details','Viewing and search activity','Device and app performance information','Interactions with the service'],'policy':'https://help.netflix.com/legal/privacy','alternative':'Public library media services or locally stored media; catalogues and availability differ.'},
 {'name':'YouTube','category':'Entertainment & video','purpose':'Video hosting and streaming','collects':['Search and viewing activity','Account and interaction information','Device, network and diagnostic information','Location-related information depending on settings'],'policy':'https://policies.google.com/privacy','alternative':'PeerTube instances or public-service video platforms; content availability differs.'},
 {'name':'Spotify','category':'Entertainment & video','purpose':'Music and podcast streaming','collects':['Account and subscription details','Listening and search activity','Device and usage information','Location or payment information where relevant to features'],'policy':'https://www.spotify.com/legal/privacy-policy/','alternative':'Local music library/player; this avoids a streaming profile but requires you to source and store music.'},
 {'name':'Amazon Prime Video','category':'Entertainment & video','purpose':'Film and television streaming','collects':['Account and subscription details','Viewing and search activity','Device and app performance information','Interactions with the service'],'policy':'https://www.amazon.in/gp/help/customer/display.html?nodeId=GX7NJQ4ZB8MHFRNJ','alternative':'Public library media services or locally stored media; catalogues and availability differ.'},
]

# Official domains permitted for policy retrieval. Redirects to unrelated domains are rejected.
POLICY_HOSTS = {
    'Swiggy': {'swiggy.com'},
    'Zomato': {'zomato.com'},
    'Blinkit': {'blinkit.com'},
    'Zepto': {'zepto.com'},
    'Instagram': {'instagram.com', 'meta.com', 'facebook.com'},
    'Snapchat': {'snap.com', 'values.snap.com'},
    'WhatsApp': {'whatsapp.com', 'meta.com'},
    'Facebook': {'facebook.com', 'meta.com'},
    'Uber': {'uber.com'},
    'Ola': {'olacabs.com'},
    'Rapido': {'rapido.bike'},
    'Google Maps': {'google.com'},
    'Netflix': {'netflix.com'},
    'YouTube': {'youtube.com', 'google.com'},
    'Spotify': {'spotify.com'},
    'Amazon Prime Video': {'amazon.com', 'amazon.in'},
}

# More direct canonical policy URLs where the app's configured URL is only a homepage.
POLICY_URLS = {
    'Swiggy': ['https://www.swiggy.com/privacy-policy'],
    'Instagram': ['https://privacycenter.instagram.com/policy/'],
}

CONCERNS = {
 'location': {'label':'Location tracking or sharing','terms':['location','gps','geolocation','precise location','approximate location','nearby','movement','trip']},
 'advertising': {'label':'Advertising, profiling or targeted recommendations','terms':['advertising','advertisement','ads','personalised ads','personalized ads','marketing','profil','target','inference']},
 'sharing': {'label':'Sharing with third parties or partners','terms':['third partie','third partie','partner','affiliate','service provider','share','disclos','transfer']},
 'retention': {'label':'How long data is retained','terms':['retain','retention','delete','deletion','存','period','duration','backup']},
 'contacts': {'label':'Contacts, address book or social graph','terms':['contact','address book','phonebook','friends','connection']},
 'device': {'label':'Device identifiers and tracking technologies','terms':['device id','identifier','cookie','pixel','sdk','ip address','browser','tracking technolog']},
 'content': {'label':'Access to messages, photos or user content','terms':['message','photo','camera','microphone','content','upload','communication']},
}

def init_db():
    with sqlite3.connect(DB) as con:
        con.execute('''CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY AUTOINCREMENT, app TEXT, action TEXT, email TEXT, draft TEXT, status TEXT DEFAULT 'Draft', created TEXT)''')
init_db()

def get_app(name):
    return next((a for a in APPS if a['name']==name), APPS[0])


def _host_allowed(host, allowed):
    host = (host or '').lower().split(':')[0]
    return any(host == d or host.endswith('.' + d) for d in allowed)

def extract_document(app_name):
    """Retrieve a policy only if the final URL remains on an app-approved official domain."""
    selected = next((a for a in APPS if a['name'] == app_name), None)
    if not selected:
        raise ValueError('Unknown app.')
    allowed = POLICY_HOSTS.get(app_name, set())
    urls = POLICY_URLS.get(app_name, []) + [selected['policy']]
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; DataRefusePolicyResearch/1.0; educational prototype)',
        'Accept': 'text/html,application/pdf,application/xhtml+xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    max_bytes = 8 * 1024 * 1024
    errors = []
    seen = set()

    def parse(data, content_type, page_url):
        if 'pdf' in content_type or page_url.lower().endswith('.pdf') or data[:4] == b'%PDF':
            reader = PdfReader(BytesIO(data))
            chunks=[]
            for i, page in enumerate(reader.pages):
                t=(page.extract_text() or '').strip()
                if t: chunks.append(f'PAGE {i+1}\n{t}')
            return '\n\n'.join(chunks), 'PDF'
        soup=BeautifulSoup(data,'html.parser')
        for node in soup(['script','style','noscript','nav','footer','header','svg','form']):
            node.decompose()
        # Prefer semantic policy content, not site chrome or title-only landing pages.
        main=soup.find('main') or soup.find('article') or soup.find(attrs={'role':'main'}) or soup.body or soup
        headings=[]
        for h in main.find_all(['h1','h2','h3','h4']):
            t=h.get_text(' ',strip=True)
            if t: headings.append(t)
        text=main.get_text('\n',strip=True)
        title=soup.title.get_text(' ',strip=True) if soup.title else ''
        if title and title.lower() not in text[:300].lower():
            text=title+'\n'+text
        return text, 'webpage'

    for url in urls:
        if url in seen: continue
        seen.add(url)
        try:
            parsed=urlparse(url)
            if parsed.scheme not in ('http','https') or not _host_allowed(parsed.hostname, allowed):
                errors.append(f'Configured URL is not on an approved domain: {url}')
                continue
            r=requests.get(url,headers=headers,timeout=(10,25),stream=True,allow_redirects=True)
            r.raise_for_status()
            if not _host_allowed(urlparse(r.url).hostname, allowed):
                raise ValueError(f'Redirected to an unapproved domain ({urlparse(r.url).hostname}); rejected to avoid analysing the wrong company policy.')
            data=bytearray()
            for chunk in r.iter_content(65536):
                if not chunk: continue
                data.extend(chunk)
                if len(data)>max_bytes: raise ValueError('Policy document exceeds the 8 MB prototype limit.')
            text,kind=parse(bytes(data),r.headers.get('Content-Type','').lower(),r.url)
            # Follow explicitly labelled same-company policy links from a landing page.
            candidates=[]
            if len(text)<2500 and 'html' in r.headers.get('Content-Type','').lower():
                soup=BeautifulSoup(bytes(data),'html.parser')
                for a in soup.find_all('a',href=True):
                    label=(a.get_text(' ',strip=True)+' '+a['href']).lower()
                    if any(x in label for x in ['privacy policy','privacy notice','terms of use','terms and conditions','consent']):
                        candidate=urljoin(r.url,a['href'])
                        if _host_allowed(urlparse(candidate).hostname,allowed) and candidate not in seen:
                            candidates.append(candidate)
            best=(text,r.url,kind)
            for candidate in candidates[:5]:
                seen.add(candidate)
                try:
                    rr=requests.get(candidate,headers=headers,timeout=(10,25),allow_redirects=True)
                    rr.raise_for_status()
                    if not _host_allowed(urlparse(rr.url).hostname,allowed): continue
                    ctext,ckind=parse(rr.content,rr.headers.get('Content-Type','').lower(),rr.url)
                    if len(ctext)>len(best[0]): best=(ctext,rr.url,ckind)
                except Exception as e:
                    errors.append(str(e))
            text,final_url,kind=best
            if len(text.strip())<700:
                errors.append(f'{url}: only {len(text.strip())} readable characters were extracted (likely a JavaScript shell or blocked page).')
                continue
            # Reject likely generic landing pages.
            if not any(term in text.lower() for term in ['privacy','personal information','personal data','information we collect','data we collect']):
                errors.append(f'{url}: retrieved page did not look like a privacy document.')
                continue
            return text[:250000],final_url,kind
        except Exception as e:
            errors.append(f'{url}: {e}')
    raise ValueError('Could not retrieve a verified readable policy from the app’s approved official domains. ' + ' | '.join(errors[-3:]))

QUERY_SYNONYMS = {
    'location': ['location','gps','geolocation','precise location','approximate location','coordinates','latitude','longitude','nearby','where you are','device location','ip address','ip-based location','movement','trip','physical location'],
    'tracking': ['tracking','track','monitor','collect','gather','access','process'],
    'sharing': ['share','disclose','transfer','provide to','third party','partner','affiliate','service provider','business partner'],
    'advertising': ['advertising','advertisement','ads','marketing','personalised','personalized','targeted','profiling','profile','recommendation','interests'],
    'retention': ['retain','retention','store','storage','keep','delete','deletion','erase','preserve','period','duration','backup'],
    'contacts': ['contacts','address book','phonebook','friends','connections','social graph'],
    'device': ['device identifier','device id','cookie','pixel','sdk','browser','identifier','online identifier','log data'],
    'messages': ['message','chat','communication','photo','video','camera','microphone','content','upload'],
    'ai': ['artificial intelligence','machine learning','ai model','training data','train models','generative ai','automated systems'],
}


def expand_user_query(query):
    q=(query or '').lower().strip()
    terms=set()
    # Keep meaningful user words only; generic words such as "data", "information",
    # "use", "policy" and "app" must never count as a hit by themselves.
    stop={'data','information','use','using','used','policy','app','the','what','about','for','and','with','from','does','how','my','their','your'}
    words=re.findall(r'[a-z0-9]+',q)
    terms.update(w for w in words if len(w)>3 and w not in stop)
    if any(x in q for x in ['location','gps','where','geolocation','tracking my location']):
        terms.update(['location','gps','geolocation','precise location','approximate location','coordinates','latitude','longitude','nearby','device location','location information','location data','ip address','physical location'])
    if any(x in q for x in ['track','tracking','monitor']):
        terms.update(['tracking','track','monitoring','device identifiers','online identifiers','cookies','pixels'])
    if any(x in q for x in ['sharing','share','third party','partner','disclosure','disclose']):
        terms.update(['share','sharing','disclose','disclosure','third party','service provider','business partner','affiliate','merchant','restaurant','vendor','transfer','provide to'])
    if any(x in q for x in ['advert','ads','marketing','profil','recommend']):
        terms.update(['advertising','advertisement','marketing','personalised ads','personalized ads','targeted advertising','profiling','interests','recommendations'])
    if any(x in q for x in ['retain','retention','delete','deletion','store','storage','keep']):
        terms.update(['retain','retention','delete','deletion','erase','storage','store','preserve','period'])
    if any(x in q for x in ['contact','address book','phonebook','social graph']):
        terms.update(['contacts','address book','phonebook','friends','connections'])
    if any(x in q for x in ['device','identifier','cookie','pixel','ip address']):
        terms.update(['device identifier','device id','cookie','pixel','sdk','browser','online identifier','ip address'])
    if any(x in q for x in ['message','chat','photo','video','camera','microphone','content']):
        terms.update(['message','chat','communication','photo','video','camera','microphone','content'])
    if any(x in q for x in ['ai','artificial intelligence','machine learning','model training']):
        terms.update(['artificial intelligence','machine learning','ai model','training data','train models','generative ai'])
    return sorted((t for t in terms if t not in stop and len(t)>2),key=len,reverse=True)

def plain_language(passage, query):
    """Conservative explanation: describes what the passage appears to say without legal conclusions."""
    low = passage.lower()
    if any(t in low for t in ['gps','geolocation','precise location','coordinates','location data','location information']):
        return "In simpler terms: this passage appears to say the service may collect or use information about where a device or user is located. Check the surrounding text for when this happens, which settings control it, and whether it is shared."
    if any(t in low for t in ['advertis','marketing','personalised','personalized','targeted','profil']):
        return "In simpler terms: this passage appears to describe using information to personalise content, measure advertising, or build interests/profiles. Check which data is used and what controls are available."
    if any(t in low for t in ['third partie','partner','affiliate','service provider','disclos','share']):
        return "In simpler terms: this passage appears to describe information being shared or made available to another organisation or service provider. Check who receives it and for what purpose."
    if any(t in low for t in ['retain','retention','delete','deletion','erase','storage','store']):
        return "In simpler terms: this passage appears to explain how information is stored, kept, or deleted. Look for the retention period and exceptions."
    if any(t in low for t in ['contact','address book','phonebook','friends','connection']):
        return "In simpler terms: this passage appears to relate to contact details or information about a user's connections."
    if any(t in low for t in ['cookie','identifier','device id','ip address','sdk','pixel']):
        return "In simpler terms: this passage appears to describe identifiers or technologies that recognise a device, browser, or activity across sessions."
    if any(t in low for t in ['artificial intelligence','machine learning','training','ai model']):
        return "In simpler terms: this passage appears to describe use of information in automated systems or AI/model development. Check what data, purposes, and opt-outs are specified."
    return "In simpler terms: this passage appears related to your search. Read it with the surrounding section to understand the exact purpose, conditions, and available controls."


def analyse(policy_text, query):
    terms=expand_user_query(query)
    # Parse text into heading-labelled blocks, preserving nearby context.
    lines=[re.sub(r'\s+',' ',x).strip() for x in (policy_text or '').splitlines()]
    blocks=[]; heading='Policy text'
    buf=[]
    heading_re=re.compile(r'^(your consent|information we collect|location information|precise location|disclosure|sharing|how we use|uses of your information|cookies|third parties|service providers|data retention|how long|opt.?out|withdrawal|advertising|personalised|personalized|security|your rights|children|international transfers)\b',re.I)
    for line in lines:
        if not line: continue
        if len(line)<100 and (heading_re.search(line) or (line.isupper() and len(line.split())<12)):
            if buf: blocks.append((heading,' '.join(buf))); buf=[]
            heading=line
        else:
            buf.append(line)
            if sum(len(x) for x in buf)>1200:
                blocks.append((heading,' '.join(buf))); buf=[]
    if buf: blocks.append((heading,' '.join(buf)))
    hits=[]
    for heading,block in blocks:
        low=block.lower()
        matched=[t for t in terms if t in low]
        # A generic word alone is not a match; require at least one specific expanded phrase.
        specific=[t for t in matched if len(t)>4 and t not in {'track','share','store','period','vendor'}]
        if not specific: continue
        # Require multiple meaningful signals for broad "data sharing" queries, or one strong phrase.
        if len(specific)<1: continue
        hits.append({'passage':block[:1800], 'terms':matched[:10], 'score':len(specific), 'explanation':plain_language(block,query), 'section':heading})
    hits.sort(key=lambda h:h['score'],reverse=True)
    return hits[:15],terms

@app.route('/')
def home():
    categories=[]
    for cat in ['Food & shopping','Social & communication','Travel & mobility','Entertainment & video']:
        categories.append({'name':cat,'apps':[a for a in APPS if a['category']==cat]})
    with sqlite3.connect(DB) as con:
        con.row_factory=sqlite3.Row
        requests_list=[dict(r) for r in con.execute('SELECT * FROM requests ORDER BY id DESC LIMIT 12')]
    return render_template('index.html', categories=categories, apps=APPS, requests=requests_list)

# Privacy-oriented alternatives and lower-data ways to complete the same task.
# These are candidates to compare, not certified "low-data" services.
ALTERNATIVES = {
 'Swiggy': [
  {'name':'Order directly from the restaurant','why':'Call, visit, or use the restaurant’s own ordering channel to avoid an additional delivery-platform account where possible.'},
  {'name':'Local restaurant / takeaway','why':'Ordering in person or by phone can reduce app-based tracking and profiling.'}],
 'Zomato': [
  {'name':'Order directly from the restaurant','why':'Use the restaurant’s own website, phone number or in-person counter where available.'},
  {'name':'Local takeaway','why':'A direct transaction may avoid creating another platform-based activity profile.'}],
 'Blinkit': [
  {'name':'Local kirana / neighbourhood shop','why':'Buy in person or contact the shop directly instead of using a quick-commerce app.'},
  {'name':'Direct shop ordering','why':'Where a shop offers phone or web ordering, compare what information it asks you to provide.'}],
 'Zepto': [
  {'name':'Local grocery shop','why':'In-person purchases avoid app-based location and shopping-history collection.'},
  {'name':'Direct shop ordering','why':'Use a shop’s own ordering channel if available; check its privacy practices.'}],
 'Instagram': [
  {'name':'Pixelfed','why':'Decentralised photo-sharing alternative with a different business and data model; review the chosen server’s policy.'},
  {'name':'Mastodon','why':'Decentralised social networking; each server has its own rules and privacy policy.'}],
 'Snapchat': [
  {'name':'Signal','why':'Privacy-focused messaging for direct conversations; it does not reproduce Snapchat’s Stories and camera features.'},
  {'name':'BeReal (feature alternative)','why':'A different social format, not a privacy certification; compare its current permissions and policy before switching.'}],
 'WhatsApp': [
  {'name':'Signal','why':'Privacy-focused messaging with end-to-end encrypted conversations; metadata and account information still matter.'},
  {'name':'SimpleX Chat','why':'Designed to avoid user identifiers such as phone numbers; availability and usability differ.'}],
 'Facebook': [
  {'name':'Mastodon','why':'Decentralised social networking; privacy depends partly on the server you choose.'},
  {'name':'A private forum or group','why':'A small community space may require less public profiling than a large social network; review its provider.'}],
 'Uber': [
  {'name':'Public transport / official transit app','why':'For suitable trips, transit can avoid ride-hailing trip profiles; transit apps still have their own data practices.'},
  {'name':'Local taxi by phone','why':'Booking directly may reduce dependence on a large ride-hailing platform.'}],
 'Ola': [
  {'name':'Public transport / official transit app','why':'For suitable journeys, use transit information and ticketing services instead of ride-hailing.'},
  {'name':'Local taxi by phone','why':'A direct booking can avoid creating another ride-hailing account.'}],
 'Rapido': [
  {'name':'Public transport / official transit app','why':'For suitable journeys, public transport can avoid app-based ride tracking.'},
  {'name':'Local auto or taxi stand','why':'Arranging a ride directly may reduce platform-mediated collection.'}],
 'Google Maps': [
  {'name':'Organic Maps','why':'Open-source, offline-first maps with a smaller account and tracking footprint for basic navigation; online features differ.'},
  {'name':'OsmAnd','why':'Open-source mapping with offline use; review optional online services and app permissions.'}],
 'Netflix': [
  {'name':'Jellyfin','why':'Self-hosted media library software; you control the server and accounts, but setup and content sourcing are your responsibility.'},
  {'name':'Locally stored media + VLC','why':'Offline playback avoids a streaming service’s viewing-history profile.'}],
 'YouTube': [
  {'name':'PeerTube','why':'Federated video hosting; privacy practices depend on the instance you use.'},
  {'name':'NewPipe (Android)','why':'Open-source YouTube client that can reduce account-linked use; Android only and not an official YouTube app.'}],
 'Spotify': [
  {'name':'Local music player + files','why':'Offline playback avoids streaming-platform listening profiles; you manage your own music library.'},
  {'name':'Funkwhale','why':'Federated music hosting; server choice and its privacy policy matter.'}],
 'Amazon Prime Video': [
  {'name':'Jellyfin','why':'Self-hosted media library; you control the server, but need your own legally obtained media.'},
  {'name':'Locally stored media + VLC','why':'Offline playback avoids a streaming platform’s viewing-history profile.'}]
}

@app.route('/app/<name>')
def app_detail(name):
    a=get_app(name)
    return render_template('app.html', a=a, alternatives=ALTERNATIVES.get(name, []))


@app.route('/analyzer', methods=['GET','POST'])
def analyzer():
    hits=[]; query=''; policy_text=''; app_name=request.args.get('app','')
    source_url=''; source_kind=''; fetched_at=''; expanded_terms=[]
    selected_app=next((a for a in APPS if a['name']==app_name), None)
    if request.method=='POST':
        app_name=request.form.get('app','')
        query=request.form.get('query','').strip()
        policy_text=request.form.get('policy_text','')
        source_url=request.form.get('source_url','')
        source_kind=request.form.get('source_kind','')
        fetched_at=request.form.get('fetched_at','')
        action=request.form.get('action','analyse')
        selected_app=next((a for a in APPS if a['name']==app_name), None)
        if not selected_app:
            flash('Choose an app first.','error')
        elif action in ('fetch','analyse') and not policy_text.strip():
            try:
                policy_text, source_url, source_kind=extract_document(app_name)
                fetched_at=datetime.now().strftime('%Y-%m-%d %H:%M')
            except Exception as exc:
                flash(f'Could not retrieve readable policy text automatically: {exc}','error')
        if action=='fetch':
            if policy_text.strip():
                flash('Policy text retrieved. Now enter an everyday-language concern (for example, “location tracking”) and analyse it.','success')
        elif action=='analyse':
            if not query:
                flash('Type what you want to investigate, for example “location tracking”.','error')
            elif not policy_text.strip():
                flash('No readable policy text was retrieved. Try again later or use the manual text option.','error')
            else:
                hits, expanded_terms=analyse(policy_text,query)
                if not hits:
                    flash('No relevant passages were found in the text retrieved. Try a related phrase or check whether the complete policy was retrieved.','warning')
    return render_template('analyzer.html', apps=APPS, app_name=app_name, hits=hits, query=query, policy_text=policy_text, source_url=source_url, source_kind=source_kind, fetched_at=fetched_at, expanded_terms=expanded_terms)

@app.route('/rights', methods=['GET','POST'])
def rights():
    draft=None
    if request.method=='POST':
        platform=request.form.get('app','')
        action=request.form.get('action','')
        details=request.form.get('details','').strip()
        email=request.form.get('email','').strip()
        action_text={'delete':'request deletion of personal data that is eligible for erasure','withdraw':'withdraw consent for the specified processing purpose','refuse':'object to or refuse the specified permission or optional data use'}.get(action,'make a privacy request')
        draft=f'''Subject: Request to {action_text.title()}\n\nDear Privacy Team,\n\nI am a user of {platform}. I would like to {action_text}.\n\nDetails of my request: {details or '[Describe the data or purpose here]'}\n\nPlease let me know the steps required to process this request, any applicable limitations or legal retention requirements, and provide confirmation of the outcome.\n\nRegards,\n{email or '[Your name / registered email]'}'''
        with sqlite3.connect(DB) as con:
            con.execute('INSERT INTO requests(app,action,email,draft,status,created) VALUES(?,?,?,?,?,?)',(platform,action,email,draft,'Draft',datetime.now().strftime('%Y-%m-%d %H:%M')))
    return render_template('rights.html', apps=APPS, draft=draft)

@app.route('/status/<int:req_id>', methods=['POST'])
def status(req_id):
    new_status=request.form.get('status','Draft')
    if new_status not in ['Draft','Submitted by user','Response received','Closed']: new_status='Draft'
    with sqlite3.connect(DB) as con: con.execute('UPDATE requests SET status=? WHERE id=?',(new_status,req_id))
    flash('Tracker updated. This status is self-reported, not verified by the platform.','success')
    return redirect(url_for('home'))

if __name__=='__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT',5001)))
