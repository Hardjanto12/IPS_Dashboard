import os
import sqlite3
import json
import re
import requests
import datetime
import urllib3
import html
import threading
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import sys
from typing import Optional

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(title="Nuctech IPS Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Configuration ---
DB_PATH = r"C:\Nuctech_Services\ServiceBPM\bpm.db"
# Fallback for local testing
if not os.path.exists(DB_PATH):
    DB_PATH = r"d:\Source Codes\Nuctech\Server PC\Nuctech_services\ServiceBPM\bpm.db"

BPM_API_URL = "http://192.111.111.80:997"
IDR_API_URL = "http://192.111.111.80:47361"

def get_db_connection():
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=500, detail="Database file not found")
    # Open in read-only mode to prevent blocking ServiceBPM writes
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn

# --- SOAP Helpers ---
# --- SOAP Session & Caching Helpers ---
soap_session = requests.Session()

# Rate limiting: max 3 concurrent SOAP calls to prevent overloading Nuctech services
soap_semaphore = threading.Semaphore(3)

def get_cache_db_path():
    if getattr(sys, 'frozen', False):
        app_path = os.path.dirname(sys.executable)
    else:
        app_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(app_path, "dashboard_cache.db")

# Persistent cache DB connection with thread-safe locking
_cache_conn = None
_cache_lock = threading.Lock()

def _get_cache_conn():
    global _cache_conn
    if _cache_conn is None:
        _cache_conn = sqlite3.connect(get_cache_db_path(), check_same_thread=False)
        _cache_conn.execute("PRAGMA journal_mode=WAL")
        _cache_conn.execute("""
            CREATE TABLE IF NOT EXISTS container_cache (
                obj_id INTEGER PRIMARY KEY,
                container_no TEXT NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        _cache_conn.commit()
    return _cache_conn

# Initialize cache on startup
try:
    _get_cache_conn()
except Exception as e:
    print(f"Error initializing cache database: {e}")

def get_cached_container_no(obj_id: int) -> Optional[str]:
    try:
        with _cache_lock:
            cursor = _get_cache_conn().cursor()
            cursor.execute("SELECT container_no FROM container_cache WHERE obj_id = ?", (obj_id,))
            row = cursor.fetchone()
            if row:
                return row[0]
    except Exception as e:
        print(f"Error reading cache: {e}")
    return None

def set_cached_container_no(obj_id: int, container_no: str):
    if not container_no or (len(container_no.strip()) < 3 and container_no != "-"):
        return
    if container_no == "-":
        container_no = "NOT_FOUND"
    try:
        with _cache_lock:
            conn = _get_cache_conn()
            conn.execute("INSERT OR REPLACE INTO container_cache (obj_id, container_no) VALUES (?, ?)", (obj_id, container_no))
            conn.commit()
    except Exception as e:
        print(f"Error writing cache: {e}")

def send_soap(url, payload):
    headers = {'Content-Type': 'text/xml; charset=utf-8', 'SOAPAction': '""'}
    # Acquire semaphore to limit concurrent SOAP calls (max 3)
    soap_semaphore.acquire()
    try:
        res = soap_session.post(url, data=payload, headers=headers, timeout=5)
        return res.text
    except Exception as e:
        print(f"SOAP Request Error to {url}: {e}")
        return ""
    finally:
        soap_semaphore.release()

def extract_xml_value(xml_str, tag_name):
    match = re.search(f'<{tag_name}>(.*?)</{tag_name}>', xml_str, re.IGNORECASE | re.DOTALL)
    if match:
        val = match.group(1).strip()
        cdata_match = re.search(r'<!\[CDATA\[(.*?)\]\]>', val, re.DOTALL)
        if cdata_match:
            return cdata_match.group(1).strip()
        return val
    return None

def fetch_ips_realtime_data(container_picno):
    ips_data = {
        "scan_time": "-", "operator_id": "-", "conclusion": "-", "submit_time": "-",
        "scan_direction": "-", "energy_mode": "-", "images": []
    }
    manifest_data = {
        "container_no": "-", "container_type": "-", "container_weight": "-",
        "vehicle_type": "-", "vehicle_serial": "-",
        "driver_name": "-", "country_of_origin": "-", "exit_time": "-", 
        "remark": "-", "rear_vehicle_no": "-"
    }
    
    if not container_picno:
        return ips_data, manifest_data
        
    # 1. Get CheckUnitId
    req_unit = f"""<?xml version="1.0" encoding="UTF-8"?>
    <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:Idr="urn:NuctechIdrService">
    <SOAP-ENV:Body><Idr:GetCheckUnitId><wstrCheckUnit>{container_picno}</wstrCheckUnit></Idr:GetCheckUnitId></SOAP-ENV:Body></SOAP-ENV:Envelope>"""
    
    res_unit = send_soap(IDR_API_URL, req_unit)
    check_unit_id = extract_xml_value(res_unit, "wstrCheckUnitId")
    
    if not check_unit_id:
        return ips_data, manifest_data
        
    # 2. Get ImageId
    req_img_id = f"""<?xml version="1.0" encoding="UTF-8"?>
    <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:Idr="urn:NuctechIdrService">
    <SOAP-ENV:Body><Idr:GetImageId><wstrCheckUnitId>{check_unit_id}</wstrCheckUnitId></Idr:GetImageId></SOAP-ENV:Body></SOAP-ENV:Envelope>"""
    
    res_img_id = send_soap(IDR_API_URL, req_img_id)
    image_id = extract_xml_value(res_img_id, "wstrImageId")
    
    if not image_id:
        return ips_data, manifest_data
        
    # 3. Get IdrRdbXml (Full Details)
    req_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:Idr="urn:NuctechIdrService">
    <SOAP-ENV:Body><Idr:GetIdrRdbXml><wstrImageId>{image_id}</wstrImageId></Idr:GetIdrRdbXml></SOAP-ENV:Body></SOAP-ENV:Envelope>"""
    
    res_xml = send_soap(IDR_API_URL, req_xml)
    full_xml_encoded = extract_xml_value(res_xml, "wstrIdrRdbXml")
    
    full_xml = html.unescape(full_xml_encoded) if full_xml_encoded else ""
    
    if full_xml:
        # === Parse Manifest from <inputinfo> block ===
        # Nuctech uses non-standard XML tags for manifest data:
        #   <container_no>       -> Container Number
        #   <tax_number>         -> Front Vehicle NO (plate)
        #   <fyco_present>       -> Rear Vehicle NO (plate)
        #   <number_of_colli>    -> Loadometer Weight
        #   <name_official>      -> Driver's Name
        #   <appointment_date>   -> Vehicle Exit Time (approx)
        
        c_no = extract_xml_value(full_xml, "container_no")
        if c_no: manifest_data["container_no"] = c_no
        
        # Front Vehicle = <tax_number>, fallback to <g_v_no>
        front_v = extract_xml_value(full_xml, "tax_number") or extract_xml_value(full_xml, "g_v_no")
        if front_v: manifest_data["vehicle_serial"] = front_v
        
        # Rear Vehicle = <fyco_present>
        rear_v = extract_xml_value(full_xml, "fyco_present")
        if rear_v: manifest_data["rear_vehicle_no"] = rear_v
        
        # Loadometer Weight = <number_of_colli>
        weight = extract_xml_value(full_xml, "number_of_colli")
        if weight: manifest_data["container_weight"] = weight
        
        # Driver's Name = <name_official>
        driver = extract_xml_value(full_xml, "name_official")
        if driver: manifest_data["driver_name"] = driver
        
        # Country of Origin = <office> (customs office code)
        country = extract_xml_value(full_xml, "office")
        if country: manifest_data["country_of_origin"] = country
        
        # Vehicle Exit Time = <appointment_date> in <planning>
        exit_time = extract_xml_value(full_xml, "appointment_date")
        if exit_time: manifest_data["exit_time"] = exit_time
        
        # Remark / Goods Description
        remark = extract_xml_value(full_xml, "consignee") or extract_xml_value(full_xml, "name_vessel")
        if remark: manifest_data["remark"] = remark
        
        # === Parse Image & Scan Info ===
        scan_time = extract_xml_value(full_xml, "SCANTIME")
        if scan_time: ips_data["scan_time"] = scan_time
        
        dir_match = extract_xml_value(full_xml, "ScanDirection")
        if dir_match: ips_data["scan_direction"] = "Forward" if dir_match == "1" else "Backward"
        
        energy_match = extract_xml_value(full_xml, "EnergyMode")
        if energy_match: ips_data["energy_mode"] = energy_match
        
        # Vehicle Enter Time (unix timestamp in XML)
        veh_enter = extract_xml_value(full_xml, "Time_Veh_Enter")
        if veh_enter:
            try:
                ips_data["vehicle_enter_time"] = datetime.datetime.fromtimestamp(int(veh_enter)).strftime("%Y-%m-%d %H:%M:%S")
            except: pass
        
        # Find all images
        img_matches = re.findall(r'<img>(.*?)</img>', full_xml)
        ips_data["images"] = [img.strip() for img in img_matches if img.strip().endswith('.jpg')]
        
        ccr_matches = re.findall(r'<SCANIMG>.*?<TYPE>CCR</TYPE>.*?<PATH>(.*?)</PATH>.*?</SCANIMG>', full_xml, re.IGNORECASE | re.DOTALL)
        ips_data["ccr_images"] = [f"http://192.111.111.80:6688{path.strip()}" for path in ccr_matches]
        
        cam_matches = re.findall(r'<SCANIMG>.*?<TYPE>Camera</TYPE>.*?<PATH>(.*?)</PATH>.*?</SCANIMG>', full_xml, re.IGNORECASE | re.DOTALL)
        ips_data["camera_images"] = [f"http://192.111.111.80:6688{path.strip()}" for path in cam_matches]
        
    return ips_data, manifest_data

# --- API Endpoints ---
@app.get("/api/tasks")
def get_tasks(limit: int = 100, status: str = "all"):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT 
            o.id,
            o._id as task_id, 
            o.model, 
            o.createTime, 
            s.state 
        FROM Object o 
        LEFT JOIN State s ON o.id = s.objId 
        WHERE s.seq = (SELECT MAX(seq) FROM State WHERE objId = o.id)
        """
        
        params = []
        if status == "safe":
            # Hanya ambil 'container', abaikan 'truck' (TASKIDAUTOBIND)
            query += " AND lower(o.model) = 'container'"
            # Hanya tampilkan data dengan state check.ready
            query += " AND lower(s.state) = 'check.ready'"
        elif status != "all":
            query += " AND s.state = ?"
            params.append(status)
            
        query += " ORDER BY o.createTime DESC"
        
        if limit > 0:
            query += f" LIMIT {limit}"
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        tasks = []
        for row in rows:
            obj_id = row["id"]
            cached_container = get_cached_container_no(obj_id)
            display_container = cached_container if cached_container and cached_container != "NOT_FOUND" else "-"
            tasks.append({
                "id": obj_id,
                "task_id": row["task_id"],
                "model": row["model"],
                "create_time": row["createTime"],
                "state": row["state"],
                "container_no": display_container
            })
            
        conn.close()
        return {"tasks": tasks}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/tasks/{obj_id}/details")
def get_task_details(obj_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Object Info
        cursor.execute("SELECT * FROM Object WHERE id = ?", (obj_id,))
        obj = cursor.fetchone()
        if not obj:
            conn.close()
            raise HTTPException(status_code=404, detail="Task not found")
            
        task_info = {
            "id": obj["id"],
            "task_id": obj["_id"],
            "model": obj["model"],
            "create_time": obj["createTime"],
            "modify_time": obj["modifyTime"],
        }
        
        # 2. Properties
        cursor.execute("SELECT name, value FROM ObjProp WHERE objId = ?", (obj_id,))
        props = {p['name']: p['value'] for p in cursor.fetchall()}
        
        # 3. State History
        cursor.execute("""
            SELECT s.seq, s.state, s.setTime, sp.name as prop_name, sp.value as prop_value
            FROM State s
            LEFT JOIN StateProp sp ON s.id = sp.stateId
            WHERE s.objId = ?
            ORDER BY s.seq
        """, (obj_id,))
        
        states = []
        for row in cursor.fetchall():
            states.append({
                "seq": row["seq"],
                "state": row["state"],
                "set_time": row["setTime"],
                "operator": row["prop_value"] if row["prop_name"] == "operator" else None,
            })
            
        # 4. Container Link (if Truck)
        container = None
        container_picno = None
        
        if obj["model"].lower() == 'container':
            container_picno = obj["_id"]
        else:
            cursor.execute("""
                SELECT o._id as container_id, o.model, o.createTime
                FROM Link l
                JOIN Object o ON l.objId2 = o.id
                WHERE l.objId1 = ? AND l.model2 = 'container'
            """, (obj_id,))
            linked = cursor.fetchone()
            if linked:
                container = {
                    "container_id": linked["container_id"],
                    "model": linked["model"],
                    "create_time": linked["createTime"],
                }
                container_picno = linked["container_id"]
                
        conn.close()
        
        # 5. Fetch IPS Data via SOAP
        ips_data, manifest_data = fetch_ips_realtime_data(container_picno)
        
        return {
            "task": task_info,
            "properties": props,
            "state_history": states,
            "container": container,
            "ips_data": ips_data,
            "manifest_data": manifest_data,
            "container_picno": container_picno
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks/{obj_id}/manifest")
def get_task_manifest(obj_id: int):
    """Fast endpoint just to get Container No for the table view."""
    cached_val = get_cached_container_no(obj_id)
    if cached_val:
        return {"container_no": "-" if cached_val == "NOT_FOUND" else cached_val}
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM Object WHERE id = ?", (obj_id,))
        obj = cursor.fetchone()
        if not obj:
            conn.close()
            raise HTTPException(status_code=404, detail="Task not found")
            
        container_picno = None
        if obj["model"].lower() == 'container':
            container_picno = obj["_id"]
        else:
            cursor.execute("""
                SELECT o._id as container_id FROM Link l 
                JOIN Object o ON l.objId2 = o.id 
                WHERE l.objId1 = ? AND l.model2 = 'container'
            """, (obj_id,))
            linked = cursor.fetchone()
            if linked:
                container_picno = linked["container_id"]
                
        conn.close()
        
        if not container_picno:
            return {"container_no": "-"}
            
        # We only need manifest data, we can reuse fetch_ips_realtime_data
        _, manifest_data = fetch_ips_realtime_data(container_picno)
        container_no = manifest_data.get("container_no", "-")
        
        if container_no:
            set_cached_container_no(obj_id, container_no)
            
        return {"container_no": container_no}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from pydantic import BaseModel
import json

class InspectionData(BaseModel):
    container_no: str
    front_vehicle: str
    rear_vehicle: str
    driver: str
    weight: str
    country: str
    remark: str
    conclusion: str
    contents: str

@app.post("/api/tasks/{obj_id}/update_and_submit")
def update_and_submit_task(obj_id: int, data: InspectionData):
    """Updates the container data via SetSiinfo and then submits it."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM Object WHERE id = ?", (obj_id,))
        obj = cursor.fetchone()
        if not obj:
            conn.close()
            raise HTTPException(status_code=404, detail="Task not found")
            
        container_picno = None
        if obj["model"].lower() == 'container':
            container_picno = obj["_id"]
        else:
            cursor.execute("""
                SELECT o._id as container_id FROM Link l 
                JOIN Object o ON l.objId2 = o.id 
                WHERE l.objId1 = ? AND l.model2 = 'container'
            """, (obj_id,))
            linked = cursor.fetchone()
            if linked:
                container_picno = linked["container_id"]
                
        conn.close()
        if not container_picno:
            raise HTTPException(status_code=400, detail="No container PICNO linked to this task.")
            
        # 1. Fetch current Siinfo
        req_unit = f"""<?xml version="1.0" encoding="UTF-8"?>
        <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:Idr="urn:NuctechIdrService">
        <SOAP-ENV:Body><Idr:GetCheckUnitId><wstrCheckUnit>{container_picno}</wstrCheckUnit></Idr:GetCheckUnitId></SOAP-ENV:Body></SOAP-ENV:Envelope>"""
        res_unit = send_soap(IDR_API_URL, req_unit)
        check_unit_id = extract_xml_value(res_unit, "wstrCheckUnitId")
        if not check_unit_id:
            raise HTTPException(status_code=400, detail="Container is not active in IDR (maybe already submitted?)")

        req_siinfo = f"""<?xml version="1.0" encoding="UTF-8"?>
        <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:Idr="urn:NuctechIdrService">
        <SOAP-ENV:Body><Idr:GetSiinfo><wstrCheckUnitId>{check_unit_id}</wstrCheckUnitId></Idr:GetSiinfo></SOAP-ENV:Body></SOAP-ENV:Envelope>"""
        res_siinfo = send_soap(IDR_API_URL, req_siinfo)
        
        # Extract <Siinfo> block
        siinfo_match = re.search(r'<Siinfo>(.*?)</Siinfo>', res_siinfo, re.IGNORECASE | re.DOTALL)
        if not siinfo_match:
            raise HTTPException(status_code=500, detail="Failed to fetch Siinfo from IDR")
            
        siinfo_content = siinfo_match.group(1)
        
        # 2. Modify inputinfo XML inside Siinfo
        # The inputinfo is HTML encoded inside <m-vTYPEVALUE> where <m-vTYPE> is inputinfo.
        # But wait! <m-vTYPEVALUE> tags are ordered corresponding to <m-vTYPE>.
        # We can just decode the whole Siinfo, replace what we need, and re-encode.
        siinfo_un = html.unescape(siinfo_content)
        
        # Replace container_no (escape backslashes for re.sub replacement)
        safe_container_no = data.container_no.replace('\\', '\\\\')
        siinfo_un = re.sub(r'<container_no>.*?</container_no>', f'<container_no>{safe_container_no}</container_no>', siinfo_un, count=1)
        
        # Replace g_v_no (Front Vehicle)
        safe_front_vehicle = data.front_vehicle.replace('\\', '\\\\')
        if '<g_v_no>' in siinfo_un:
            siinfo_un = re.sub(r'<g_v_no>.*?</g_v_no>', f'<g_v_no>{safe_front_vehicle}</g_v_no>', siinfo_un, count=1)
        else:
            # If not present, try to inject it into <container>
            siinfo_un = siinfo_un.replace('</container>', f'<g_v_no>{data.front_vehicle}</g_v_no></container>')
            
        # You can add more replacements here (rear_vehicle, driver, etc.) if their tags are known.
        
        # Re-encode only the XML parts inside m-vTYPEVALUE
        # Actually, if we just send the whole thing wrapped in <Siinfo>, we MUST re-encode the values inside <m-vTYPEVALUE>
        # A quick hack: IDR usually accepts it even if we just encode < and > as &lt; and &gt;
        
        # Let's extract all m-vTYPEVALUEs and encode their inner content
        def encode_typevalue(match):
            inner = match.group(1)
            # Only encode if it contains actual tags
            if '<' in inner:
                return f"<m-vTYPEVALUE>{html.escape(inner)}</m-vTYPEVALUE>"
            return match.group(0)
            
        siinfo_encoded = re.sub(r'<m-vTYPEVALUE>(.*?)</m-vTYPEVALUE>', encode_typevalue, siinfo_un, flags=re.DOTALL)
        
        # 3. Send SetSiinfo
        req_set = f"""<?xml version="1.0" encoding="UTF-8"?>
        <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:Idr="urn:NuctechIdrService">
        <SOAP-ENV:Body><Idr:SetSiinfo><Siinfo>{siinfo_encoded}</Siinfo></Idr:SetSiinfo></SOAP-ENV:Body></SOAP-ENV:Envelope>"""
        
        res_set = send_soap(IDR_API_URL, req_set)
        
        # 4. Now perform the conclusion workflow
        conclusion = data.conclusion if data.conclusion else "No Suspect"
        
        # setProperty check_result
        req_prop1 = f"""<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:H986BPM="http://www.nuctech.com/BPMServer/">
<SOAP-ENV:Body SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
<H986BPM:setProperty><model>container</model><id>{container_picno}</id><name>check_result</name><value>{conclusion}</value></H986BPM:setProperty>
</SOAP-ENV:Body></SOAP-ENV:Envelope>"""
        send_soap(BPM_API_URL, req_prop1)
        
        # CommitConclusion (using conclusioninfo format to fill Inspector/Conclusion fields)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        contents_escaped = html.escape(data.contents) if data.contents else ""
        req_commit = f"""<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:Idr="urn:NuctechIdrService">
<SOAP-ENV:Body><Idr:CommitConclusion><wstrCheckUnitId>{check_unit_id}</wstrCheckUnitId><conclusioninfo><m-strID></m-strID><m-strCHECKUNITID>{container_picno}</m-strCHECKUNITID><m-strOPERATORID>Ips1</m-strOPERATORID><m-strAPPID>check</m-strAPPID><m-strTYPE>{conclusion}</m-strTYPE><m-strCONTENT>&lt;CONTENT&gt;{contents_escaped}&lt;/CONTENT&gt;</m-strCONTENT><m-strOPERATIONTIME>{now_str}</m-strOPERATIONTIME></conclusioninfo></Idr:CommitConclusion></SOAP-ENV:Body></SOAP-ENV:Envelope>"""
        send_soap(IDR_API_URL, req_commit)
        
        # setState check.end
        req_state2 = f"""<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:H986BPM="http://www.nuctech.com/BPMServer/">
<SOAP-ENV:Body SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
<H986BPM:setState><model>container</model><id>{container_picno}</id><stage>check</stage><substate>end</substate><stateProps><item><name>operator</name><value>Ips1</value></item></stateProps></H986BPM:setState>
</SOAP-ENV:Body></SOAP-ENV:Envelope>"""
        send_soap(BPM_API_URL, req_state2)
        
        return {"status": "success", "message": f"Task updated and submitted as {conclusion}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/{obj_id}/submit")
def submit_task(obj_id: int):
    """Auto Submit a task as 'No Suspect' via Nuctech SOAP APIs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM Object WHERE id = ?", (obj_id,))
        obj = cursor.fetchone()
        if not obj:
            raise HTTPException(status_code=404, detail="Task not found")
            
        container_picno = None
        if obj["model"].lower() == 'container':
            container_picno = obj["_id"]
        else:
            cursor.execute("""
                SELECT o._id as container_id FROM Link l JOIN Object o ON l.objId2 = o.id 
                WHERE l.objId1 = ? AND l.model2 = 'container'
            """, (obj_id,))
            linked = cursor.fetchone()
            if linked:
                container_picno = linked["container_id"]
                
        if not container_picno:
            raise HTTPException(status_code=400, detail="No container linked to this task.")
            
        # Get CheckUnitId
        req_unit = f"""<?xml version="1.0" encoding="UTF-8"?>
        <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:Idr="urn:NuctechIdrService">
        <SOAP-ENV:Body><Idr:GetCheckUnitId><wstrCheckUnit>{container_picno}</wstrCheckUnit></Idr:GetCheckUnitId></SOAP-ENV:Body></SOAP-ENV:Envelope>"""
        
        res_unit = send_soap(IDR_API_URL, req_unit)
        check_unit_id = extract_xml_value(res_unit, "wstrCheckUnitId")
        
        if not check_unit_id:
            raise HTTPException(status_code=400, detail="Cannot find CheckUnitId in IDR Service. Scan might not be complete.")
            
        # 1. setState check.begin (BPM)
        req_begin = f"""<?xml version="1.0" encoding="UTF-8"?>
        <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:H986BPM="http://www.nuctech.com/BPMServer/">
        <SOAP-ENV:Body><H986BPM:setState><model>container</model><id>{container_picno}</id><stage>check</stage><substate>begin</substate><stateProps><item><name>operator</name><value>Ips1</value></item></stateProps></H986BPM:setState></SOAP-ENV:Body></SOAP-ENV:Envelope>"""
        send_soap(BPM_API_URL, req_begin)
        
        # 2. setProperty check_result = No Suspect (BPM)
        req_prop = f"""<?xml version="1.0" encoding="UTF-8"?>
        <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:H986BPM="http://www.nuctech.com/BPMServer/">
        <SOAP-ENV:Body><H986BPM:setProperty><model>container</model><id>{container_picno}</id><name>check_result</name><value>No Suspect</value></H986BPM:setProperty></SOAP-ENV:Body></SOAP-ENV:Envelope>"""
        send_soap(BPM_API_URL, req_prop)
        
        # 3. CommitConclusion (IDR)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        req_commit = f"""<?xml version="1.0" encoding="UTF-8"?>
        <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:Idr="urn:NuctechIdrService">
        <SOAP-ENV:Body><Idr:CommitConclusion><wstrCheckUnitId>{check_unit_id}</wstrCheckUnitId><conclusioninfo><m-strID></m-strID><m-strCHECKUNITID>{container_picno}</m-strCHECKUNITID><m-strOPERATORID>Ips1</m-strOPERATORID><m-strAPPID>check</m-strAPPID><m-strTYPE>No Suspect</m-strTYPE><m-strCONTENT>&lt;CONTENT&gt;&lt;CONTENT&gt;&lt;/CONTENT&gt;&lt;/CONTENT&gt;</m-strCONTENT><m-strOPERATIONTIME>{now_str}</m-strOPERATIONTIME></conclusioninfo></Idr:CommitConclusion></SOAP-ENV:Body></SOAP-ENV:Envelope>"""
        send_soap(IDR_API_URL, req_commit)
        
        # 4. setState check.end (BPM)
        req_end = f"""<?xml version="1.0" encoding="UTF-8"?>
        <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:H986BPM="http://www.nuctech.com/BPMServer/">
        <SOAP-ENV:Body><H986BPM:setState><model>container</model><id>{container_picno}</id><stage>check</stage><substate>end</substate><stateProps><item><name>operator</name><value>Ips1</value></item></stateProps></H986BPM:setState></SOAP-ENV:Body></SOAP-ENV:Envelope>"""
        send_soap(BPM_API_URL, req_end)
        
        return {"status": "success", "message": f"Successfully submitted {container_picno} as No Suspect."}
        
    finally:
        conn.close()
@app.get("/api/xraydash/no-docs")
def get_xraydash_no_docs(date_range: str = None, module: str = "import"):
    try:
        url = "http://192.111.111.42:3000/api/filtered"
        action = "get_export" if module == "export" else "get_import"
        payload = {
            "module": module,
            "action": action,
            "filterMode": "xcont_only",
            "pageSize": -1
        }
        if date_range:
            payload["date_range"] = date_range
        headers = {'Content-Type': 'application/json'}
        
        # Use a higher timeout because xraydashretriever filtered scan can take ~40 seconds
        res = requests.post(url, json=payload, headers=headers, timeout=120)
        res.raise_for_status()
        data = res.json()
        
        # Extract container numbers missing documents
        missing_docs = set()
        for row in data.get("data", []):
            if row.get("cont_no"):
                missing_docs.add(row["cont_no"].strip())
            if row.get("xcont_no"):
                missing_docs.add(row["xcont_no"].strip())
                
        return {"missing_docs": list(missing_docs), "module": module}
        
    except Exception as e:
        # If xraydashretriever is offline or error occurs, return empty list gracefully
        return {"missing_docs": [], "error": str(e)}

# --- Serve Frontend (Dashboard) ---
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

# Search for frontend folder in multiple locations (works for both .py and .exe)
frontend_path = None
_search_dir = application_path
for _ in range(5):  # search up to 5 levels up
    candidate = os.path.join(_search_dir, "frontend")
    if os.path.isdir(candidate) and os.path.isfile(os.path.join(candidate, "index.html")):
        frontend_path = os.path.abspath(candidate)
        break
    _search_dir = os.path.dirname(_search_dir)

if frontend_path:
    print(f"Frontend found at: {frontend_path}")
else:
    print(f"Warning: Frontend directory not found (searched from {application_path})")

class CachedStaticFiles(StaticFiles):
    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        # Tambahkan instruksi ke browser untuk menyimpan aset (JS/CSS) selama 1 jam
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response

if frontend_path and os.path.exists(frontend_path):
    app.mount("/dashboard", CachedStaticFiles(directory=frontend_path, html=True), name="frontend")
    
    @app.get("/")
    def root():
        return RedirectResponse(url="/dashboard/index.html")


if __name__ == "__main__":
    import uvicorn
    import sys
    
    # Fix for PyInstaller --noconsole 'NoneType' object has no attribute 'isatty'
    if sys.stdout is None:
        class DummyStream:
            def write(self, *args, **kwargs): pass
            def flush(self, *args, **kwargs): pass
            def isatty(self): return False
        sys.stdout = DummyStream()
    if sys.stderr is None:
        sys.stderr = DummyStream()

    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
