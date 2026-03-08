import asyncio
import httpx
import sys

from middleware.auth import create_access_token

async def test_apis():
    token = create_access_token("test_user")
    headers = {"Authorization": f"Bearer {token}"}
    base_url = "http://127.0.0.1:8000/api/v1"
    
    async with httpx.AsyncClient() as client:
        print("1. Testing GET /health...")
        try:
            r = await client.get(f"{base_url}/health")
            print(f"Status: {r.status_code}, Response: {r.text}")
        except Exception as e:
            print(f"Failed: {e}")
            
        print("\n2. Testing GET /mcp/status...")
        try:
            r = await client.get(f"{base_url}/mcp/status")
            print(f"Status: {r.status_code}, Response: {r.text}")
        except Exception as e:
            print(f"Failed: {e}")
            
        print("\n3. Testing GET /audit...")
        try:
            r = await client.get(f"{base_url}/audit", headers=headers)
            print(f"Status: {r.status_code}, Response: {r.text}")
        except Exception as e:
             print(f"Failed: {e}")
             
        print("\n4. Testing GET /tasks...")
        try:
            r = await client.get(f"{base_url}/tasks", headers=headers)
            print(f"Status: {r.status_code}, Response: {r.text}")
        except Exception as e:
            print(f"Failed: {e}")
            
        print("\n5. Testing POST /run (Creating a test task)...")
        task_id = None
        try:
            r = await client.post(f"{base_url}/run", headers=headers, json={"task": "Find the weather in Tokyo"})
            print(f"Status: {r.status_code}, Response: {r.text}")
            if r.status_code == 200:
                task_id = r.json().get("task_id")
        except Exception as e:
            print(f"Failed: {e}")

        if task_id:
             print(f"\n6. Testing GET /stream/{task_id} (Checking stream API works)...")
             try:
                 # Just testing if endpoint is reachable, stream may hang if we don't consume it correctly so we timeout
                 r = await client.get(f"{base_url}/stream/{task_id}", headers=headers, timeout=5)
                 print(f"Status: {r.status_code}, Response snippet: {r.text[:100]}...")
             except Exception as e:
                 print(f"Stream or network exception (expected if timeout): {e}")

if __name__ == '__main__':
    asyncio.run(test_apis())
