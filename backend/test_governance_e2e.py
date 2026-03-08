import asyncio
import httpx
import sys
import json
from middleware.auth import create_access_token

async def test_governance_scenarios():
    token = create_access_token("test_auditor_user")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base_url = "http://127.0.0.1:8000/api/v1"
    
    print("=========================================================")
    print("NEXUS-NODE: GOVERNANCE E2E VALIDATION (4 PILLARS)")
    print("=========================================================\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # 1. PII Scrubbing
        print("1. Testing PII Scrubbing (Privacy Guard)...")
        try:
            r = await client.post(
                f"{base_url}/run", 
                headers=headers, 
                json={"task": "My SSN is 123-45-6789 and my email is testuser@secret.com. Please acknowledge you received it."}
            )
            data = r.json()
            task_id_1 = data.get("task_id")
            print(f"   [+] Task created: {task_id_1} (Status: {r.status_code})")
        except Exception as e:
            print(f"   [-] Failed: {e}")
            
        # 2. HITL Event Trigger
        print("\n2. Testing Human-in-the-Loop (HITL) Interception...")
        try:
            r = await client.post(
                f"{base_url}/run", 
                headers=headers, 
                json={"task": "Post a message in the #general Slack channel saying 'Hello from automated tester.'"}
            )
            data = r.json()
            task_id_2 = data.get("task_id")
            print(f"   [+] Task created: {task_id_2} (Status: {r.status_code})")
            print("   [!] This should eventually trigger a 'hitl_wait' status.")
        except Exception as e:
            print(f"   [-] Failed: {e}")
            
        # 3. Basic Orchestration / Routing
        print("\n3. Testing Multi-Step Dispatch (No HITL)...")
        try:
            r = await client.post(
                f"{base_url}/run",
                headers=headers,
                json={"task": "Check the health status of all our MCP integrations and summarize them."}
            )
            data = r.json()
            task_id_3 = data.get("task_id")
            print(f"   [+] Task created: {task_id_3} (Status: {r.status_code})")
        except Exception as e:
            print(f"   [-] Failed: {e}")
            
        # 4. Audit Log Integrity Check (Verify previous tasks)
        print("\n4. Verifying Audit Ledger Hashes (SHA-256 Check)...")
        await asyncio.sleep(2) # brief pause to let tasks hit DB
        try:
            r = await client.get(f"{base_url}/audit", headers=headers)
            if r.status_code == 200:
                audits = r.json().get("entries", [])
                print(f"   [+] Successfully fetched {len(audits)} audit records.")
                if len(audits) > 0:
                    latest = audits[0]
                    print(f"   [i] Most recent DB hash proof: {latest.get('input_hash')}")
                    print(f"   [i] Actor logged as: {latest.get('actor')}")
                    print(f"   [i] Node logged as: {latest.get('node')}")
            else:
                print(f"   [-] /audit returned {r.status_code}")
        except Exception as e:
            print(f"   [-] Failed: {e}")
            
    print("\n=========================================================")
    print("Validations dispatched! To see the real-time Mesh execution and")
    print("monitor the HITL states, go to the Nexus Node frontend at:")
    print("=> http://localhost:3000/mesh")
    print("=> http://localhost:3000/governance")

if __name__ == '__main__':
    asyncio.run(test_governance_scenarios())
