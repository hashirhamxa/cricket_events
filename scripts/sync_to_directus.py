"""
sync_cricket_matches_to_directus.py
Automated script to sync Cricket Events (Today, Tomorrow, Upcoming) from Cricket Events repo into Directus backend.
Mirrors the architecture of football's sync_today_matches_to_directus.py.
"""

import os
import sys
import json
import re
import requests
from concurrent.futures import ThreadPoolExecutor
import urllib3.util.connection as urllib_connection

ORIGINAL_CREATE_CONNECTION = urllib_connection.create_connection
HOST_MAP = {
    'db.thebicodes.com': '212.47.78.210',
    'db-v2.thebicodes.com': '212.47.78.210'
}

def patched_create_connection(address, *args, **kwargs):
    host, port = address
    if host in HOST_MAP:
        return ORIGINAL_CREATE_CONNECTION((HOST_MAP[host], port), *args, **kwargs)
    return ORIGINAL_CREATE_CONNECTION(address, *args, **kwargs)

urllib_connection.create_connection = patched_create_connection

V1_URL = 'https://db.thebicodes.com'
TOKEN = 'sejIPmFpuArDUcb5xUV6fXTgQTT9D2DX'
HEADERS = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json; charset=utf-8'
}

SESSION = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
SESSION.mount('https://', adapter)
SESSION.mount('http://', adapter)
SESSION.headers.update(HEADERS)

RAW_BASE_URL = 'https://raw.githubusercontent.com/hashirhamxa/cricket_events/master'
LOCAL_REPO_DIR = r'C:\Users\GM\Desktop\Bicodes\Cricket Events'

def norm_name(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())

ALL_STREAMING_IDS = []

def get_all_streaming_ids(base_url):
    global ALL_STREAMING_IDS
    if not ALL_STREAMING_IDS:
        try:
            r = SESSION.get(f"{base_url}/items/streaming?limit=-1", timeout=15)
            if r.status_code == 200:
                ALL_STREAMING_IDS = [s['id'] for s in r.json().get('data', [])]
        except Exception:
            pass
    return ALL_STREAMING_IDS

def link_tournament_to_all_streamings(base_url, tournament_id):
    s_ids = get_all_streaming_ids(base_url)
    for s_id in s_ids:
        try:
            payload = {"streaming_id": s_id, "tournaments_id": tournament_id}
            SESSION.post(f"{base_url}/items/streaming_tournaments_1", json=payload, timeout=10)
        except Exception:
            pass

def get_tournament_mapping(base_url):
    """Fetch all tournaments from Directus and map name to tournament ID."""
    r = SESSION.get(f"{base_url}/items/tournaments?limit=-1", timeout=25)
    tourneys = r.json().get('data', [])
    name_to_id = {}
    for t in tourneys:
        t_id = t['id']
        name = (t.get('name') or '').strip()
        if name:
            name_to_id[norm_name(name)] = (t_id, name)
    return name_to_id, tourneys

def safe_request(method, url, **kwargs):
    for attempt in range(4):
        try:
            return SESSION.request(method, url, timeout=25, **kwargs)
        except Exception as ex:
            if attempt == 3:
                raise ex
            import time
            time.sleep(1.5 * (attempt + 1))

def sync_single_event(args):
    base_url, env_name, ev, name_to_id, slug_to_event, te_pairs = args
    
    event_slug = str(ev.get('id') or ev.get('sourceMatchId') or '')
    home_name = ev.get('teamAName', '').strip()
    away_name = ev.get('teamBName', '').strip()
    event_name = f"{home_name} vs {away_name}".strip()
    
    series_name = ev.get('seriesName', '').strip()
    match_desc = ev.get('matchDesc', '').strip()
    
    # Description formatting
    if series_name and match_desc:
        description = f"Competition: {series_name} • {match_desc}"
    elif series_name:
        description = f"Competition: {series_name}"
    else:
        description = match_desc or "Live Cricket Match"
        
    # Determine start time
    start_time_raw = ev.get('startTimeUtc') or ev.get('start_time_utc') or ''
    if start_time_raw.endswith('Z'):
        start_time_clean = start_time_raw[:-1]
    elif '+' in start_time_raw:
        start_time_clean = start_time_raw.split('+')[0]
    else:
        start_time_clean = start_time_raw

    # Team logos
    team_a_img = ev.get('teamALogo')
    if team_a_img and not team_a_img.startswith('http'):
        team_a_img = f"{RAW_BASE_URL}/{team_a_img.lstrip('/')}"
    elif not team_a_img and ev.get('teamAId'):
        team_a_img = f"{RAW_BASE_URL}/images/teams/{ev['teamAId']}.png"

    team_b_url = ev.get('teamBLogo')
    if team_b_url and not team_b_url.startswith('http'):
        team_b_url = f"{RAW_BASE_URL}/{team_b_url.lstrip('/')}"
    elif not team_b_url and ev.get('teamBId'):
        team_b_url = f"{RAW_BASE_URL}/images/teams/{ev['teamBId']}.png"

    # Match image / Thumbnail
    thumb_url = ev.get('matchImageUrl')
    if not thumb_url and ev.get('matchImage'):
        thumb_url = f"{RAW_BASE_URL}/{ev['matchImage'].lstrip('/')}"

    event_payload = {
        "event_name": event_name,
        "event_slug": event_slug,
        "event_thumb_url": thumb_url,
        "is_highlight": False,
        "is_visible": True,
        "start_time": start_time_clean,
        "description": description,
        "team_a_name": home_name,
        "team_a_image": team_a_img,
        "team_b_name": away_name,
        "team_b_url": team_b_url,
        "is_live": False,
        "sort": 100
    }
    
    event_db_id = None
    action = None
    
    # Check if event already exists
    if event_slug in slug_to_event:
        existing_ev = slug_to_event[event_slug]
        event_db_id = existing_ev['id']
        res_up = safe_request('PATCH', f"{base_url}/items/events/{event_db_id}", json=event_payload)
        if res_up.status_code in [200, 204]:
            action = f"[{env_name}] [UPDATED] Event #{event_db_id}: {event_name} (Slug: {event_slug})"
        else:
            action = f"[{env_name}] [FAIL UPDATE] Event #{event_db_id}: {res_up.status_code}"
    else:
        res_cr = safe_request('POST', f"{base_url}/items/events", json=event_payload)
        if res_cr.status_code in [200, 204]:
            created_ev = res_cr.json().get('data', {})
            event_db_id = created_ev.get('id')
            action = f"[{env_name}] [CREATED] Event #{event_db_id}: {event_name} (Slug: {event_slug})"
        else:
            return f"[{env_name}] [FAIL CREATE] '{event_name}': {res_cr.status_code} - {res_cr.text}"

    # Link to tournament
    linked_msg = ""
    if event_db_id:
        c_norm = norm_name(series_name)
        t_id = None
        matched_name = series_name
        
        # 1. Exact normalized match
        if c_norm in name_to_id:
            t_id, matched_name = name_to_id[c_norm]
        else:
            # 2. Substring fallback match
            for t_norm, (tid, tname) in name_to_id.items():
                if c_norm in t_norm or t_norm in c_norm:
                    t_id = tid
                    matched_name = tname
                    break
                    
        if not t_id and series_name.strip():
            # Auto-create missing tournament on the fly
            new_t_payload = {
                "name": series_name.strip(),
                "thumb_url": thumb_url,
                "is_visible": True,
                "sport_type": "cricket",
                "status": "published",
                "description": f"Live stream for {series_name.strip()}"
            }
            res_new_t = safe_request('POST', f"{base_url}/items/tournaments", json=new_t_payload)
            if res_new_t.status_code in [200, 204]:
                created_t = res_new_t.json().get('data', {})
                t_id = created_t.get('id')
                name_to_id[c_norm] = (t_id, series_name.strip())
                linked_msg += f" -> [AUTO-CREATED Tournament #{t_id} '{series_name}']"
                link_tournament_to_all_streamings(base_url, t_id)
                linked_msg += " -> [LINKED TO ALL STREAMINGS]"

        if t_id:
            if (t_id, event_db_id) not in te_pairs:
                te_payload = {"tournaments_id": t_id, "events_id": event_db_id}
                res_te = safe_request('POST', f"{base_url}/items/tournaments_events", json=te_payload)
                if res_te.status_code in [200, 204]:
                    linked_msg += f" -> Linked to Tournament #{t_id} ('{matched_name}')"
                    te_pairs.add((t_id, event_db_id))
            else:
                linked_msg += f" -> Already linked to Tournament #{t_id}"
        else:
            linked_msg += f" -> [WARN] Tournament '{series_name}' could not be created or linked"
            
    return f"{action}{linked_msg}"

def sync_feed_for_env(base_url, env_name, events_data, feed_label):
    print(f"\n==================================================", flush=True)
    print(f"Syncing {feed_label} Cricket Events to Directus {env_name} ({base_url})", flush=True)
    print(f"==================================================", flush=True)
    
    name_to_id, all_tourneys = get_tournament_mapping(base_url)
    
    # Pre-check and create any missing tournaments sequentially to avoid thread race conditions
    for ev in events_data:
        s_name = (ev.get('seriesName') or '').strip()
        if not s_name:
            continue
        c_norm = norm_name(s_name)
        if c_norm not in name_to_id:
            # Check substring match
            found = False
            for t_norm in name_to_id:
                if c_norm in t_norm or t_norm in c_norm:
                    found = True
                    break
            if not found:
                print(f"[{env_name}] Pre-creating missing tournament: '{s_name}'", flush=True)
                thumb = ev.get('matchImageUrl')
                new_t_payload = {
                    "name": s_name,
                    "thumb_url": thumb,
                    "is_visible": True,
                    "sport_type": "cricket",
                    "status": "published",
                    "description": f"Live stream for {s_name}"
                }
                res_new = safe_request('POST', f"{base_url}/items/tournaments", json=new_t_payload)
                if res_new.status_code in [200, 204]:
                    new_tid = res_new.json().get('data', {}).get('id')
                    name_to_id[c_norm] = (new_tid, s_name)
                    link_tournament_to_all_streamings(base_url, new_tid)
                    print(f"[{env_name}] -> Created & linked Tournament #{new_tid} '{s_name}' to all streamings", flush=True)
    
    # Query only existing events with these slugs
    slugs = [str(ev.get('id') or ev.get('sourceMatchId')) for ev in events_data if ev.get('id') or ev.get('sourceMatchId')]
    slug_to_event = {}
    
    # Batch query in chunks of 25
    chunk_size = 25
    for i in range(0, len(slugs), chunk_size):
        chunk = slugs[i:i + chunk_size]
        url = f"{base_url}/items/events?filter[event_slug][_in]={','.join(chunk)}&fields=id,event_slug,event_name&limit=-1"
        for attempt in range(3):
            try:
                r_ev = SESSION.get(url, timeout=25)
                if r_ev.status_code == 200:
                    for e in r_ev.json().get('data', []):
                        if e.get('event_slug'):
                            slug_to_event[e['event_slug']] = e
                break
            except Exception as ex:
                if attempt == 2:
                    print(f"[{env_name}] Warning: error fetching slug batch: {ex}", flush=True)
                import time
                time.sleep(2)
                
    # Fetch existing tournament links for already existing events
    existing_event_ids = [e['id'] for e in slug_to_event.values()]
    te_pairs = set()
    if existing_event_ids:
        for i in range(0, len(existing_event_ids), chunk_size):
            id_chunk = [str(x) for x in existing_event_ids[i:i + chunk_size]]
            te_url = f"{base_url}/items/tournaments_events?filter[events_id][_in]={','.join(id_chunk)}&limit=-1"
            for attempt in range(3):
                try:
                    r_te = SESSION.get(te_url, timeout=25)
                    if r_te.status_code == 200:
                        for row in r_te.json().get('data', []):
                            te_pairs.add((row.get('tournaments_id'), row.get('events_id')))
                    break
                except Exception as ex:
                    if attempt == 2:
                        print(f"[{env_name}] Warning: error fetching junction batch: {ex}", flush=True)
                    import time
                    time.sleep(2)
                    
    tasks = []
    for ev in events_data:
        tasks.append((base_url, env_name, ev, name_to_id, slug_to_event, te_pairs))
        
    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        for res in executor.map(sync_single_event, tasks):
            print(res, flush=True)
            results.append(res)
    return results

def load_events(feed_name):
    # Try local file first
    local_path = os.path.join(LOCAL_REPO_DIR, 'data', 'matches', feed_name)
    if not local_path.endswith('.json'):
        local_path += '.json'
        
    if os.path.exists(local_path):
        print(f"Loading matches from local repository: {local_path}", flush=True)
        with open(local_path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    # Fallback to GitHub raw
    url = f"{RAW_BASE_URL}/data/matches/{feed_name}"
    if not url.endswith('.json'):
        url += '.json'
    print(f"Fetching matches from GitHub raw: {url}", flush=True)
    r = requests.get(url, timeout=15)
    if r.status_code == 200:
        return r.json()
        
    raise FileNotFoundError(f"Could not load feed '{feed_name}' locally or remotely.")

def sync_matches(feed_name='tomorrow.json'):
    events = load_events(feed_name)
    print(f"Found {len(events)} matches in feed '{feed_name}'.", flush=True)
    
    clean_label = feed_name.replace('.json', '').capitalize()
    results = sync_feed_for_env(V1_URL, 'V1', events, clean_label)
    print(f"\nSync complete for {clean_label} Cricket matches to Directus V1!", flush=True)
    return results

if __name__ == '__main__':
    feeds = sys.argv[1:] if len(sys.argv) > 1 else ['tomorrow.json']
    for feed in feeds:
        sync_matches(feed)
