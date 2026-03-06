import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Load .env manually to avoid dependency
def load_env():
    env_path = os.path.join(os.getcwd(), 'backend', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    if key == "GOOGLE_API_KEY":
                        os.environ["GOOGLE_API_KEY"] = value
                        print("🔑 Loaded GOOGLE_API_KEY from .env")

load_env()

from app.agent.graph import route_query
from app.agent.llm import get_llm

async def main():
    print("🚀 Starting Router Verification...")
    
    try:
        llm = get_llm()
    except Exception as e:
        print(f"❌ Could not initialize LLM: {e}")
        return

    test_cases = [
        ("Hi, how are you?", "conversational"),
        ("Search Notion for 'Mission Protocol'", "notion"),
        ("Send a message to #general on Slack", "slack"),
        ("Check my unread emails", "gmail"),
        ("What's on my calendar today?", "calendar"),
        ("List my GitHub repositories", "github"),
        ("Check email and Slack for updates", "general"),
    ]

    passed = 0
    for query, expected in test_cases:
        print(f"\n❓ Testing: '{query}'")
        try:
            route = await route_query(query, llm)
            print(f"   👉 Got: '{route}' | Expected: '{expected}'")
            
            if route == expected:
                print("   ✅ PASS")
                passed += 1
            elif expected == "general" and route != "conversational":
                 print(f"   ⚠️ ACCEPTABLE (General fallback or specific overlap)")
                 passed += 1
            else:
                print(f"   ❌ FAIL")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

    print(f"\n🎉 Test Complete. {passed}/{len(test_cases)} passed.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
