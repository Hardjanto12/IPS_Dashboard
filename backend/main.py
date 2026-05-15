from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os
from typing import List

app = FastAPI(title="IPS Integration Dashboard API")

# Setup CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = r"C:\Nuctech_Services\ServiceBPM\bpm.db"

@app.get("/api/tasks")
def get_tasks(limit: int = 100, status: str = "all"):
    if not os.path.exists(DB_PATH):
        return {"error": "Database file not found"}
        
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Ambil daftar task (Object) beserta status terakhirnya
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
        if status != "all":
            query += " AND s.state = ?"
            params.append(status)
            
        query += " ORDER BY o.createTime DESC"
        
        if limit > 0:
            query += f" LIMIT {limit}"
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        tasks = []
        for row in rows:
            tasks.append({
                "id": row["id"],
                "task_id": row["task_id"],
                "model": row["model"],
                "create_time": row["createTime"],
                "state": row["state"]
            })
            
        conn.close()
        return {"tasks": tasks}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/tasks/{obj_id}/details")
def get_task_details(obj_id: int):
    if not os.path.exists(DB_PATH):
        return {"error": "Database file not found"}
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Object info
        cursor.execute("SELECT * FROM Object WHERE id = ?", (obj_id,))
        obj = cursor.fetchone()
        if not obj:
            conn.close()
            return {"error": "Object not found"}
        
        task_info = {
            "id": obj["id"],
            "task_id": obj["_id"],
            "model": obj["model"],
            "create_time": obj["createTime"],
            "modify_time": obj["modifyTime"],
        }
        
        # 2. Object properties (result, etc)
        cursor.execute("SELECT name, value FROM ObjProp WHERE objId = ?", (obj_id,))
        props = {row["name"]: row["value"] for row in cursor.fetchall()}
        
        # 3. State history
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
        
        # 4. Linked container (if truck)
        container = None
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
        
        conn.close()
        return {
            "task": task_info,
            "properties": props,
            "state_history": states,
            "container": container,
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
def read_root():
    return {"message": "API is running. Go to /api/tasks to view the data."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
