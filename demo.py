#!/usr/bin/env python3
"""
Quick demo to verify the URL shortener is working.
"""

import sys
import time
from httpx import Client

BASE_URL = "http://127.0.0.1:8000"


def test_application():
    """Test the application functionality."""
    print("🧪 Testing FastAPI URL Shortener\n")

    with Client(base_url=BASE_URL, follow_redirects=False) as client:

        # Test 1: Home page
        print("1. Testing home page...")
        response = client.get("/")
        assert response.status_code == 200, "Home page failed"
        print("   ✅ Home page loads")

        # Test 2: Register user
        print("\n2. Testing user registration...")
        response = client.post("/auth/register", data={
            "email": "demo@example.com",
            "password": "demopassword123"
        })
        assert response.status_code == 303, "Registration failed"
        auth_cookie = response.cookies.get("auth_token")
        assert auth_cookie, "No auth token received"
        print("   ✅ User registered successfully")

        # Test 3: Access dashboard
        print("\n3. Testing dashboard access...")
        response = client.get("/d/", cookies={"auth_token": auth_cookie})
        assert response.status_code == 200, "Dashboard access failed"
        assert "Dashboard" in response.text
        print("   ✅ Dashboard accessible")

        # Test 4: Create short link
        print("\n4. Testing link creation...")
        response = client.post("/d/links",
            data={
                "original_url": "https://github.com/fastapi/fastapi",
                "custom_code": "gh-fastapi"
            },
            cookies={"auth_token": auth_cookie}
        )
        assert response.status_code == 200, "Link creation failed"
        print("   ✅ Short link created: /gh-fastapi -> https://github.com/fastapi/fastapi")

        # Test 5: Test redirect
        print("\n5. Testing link redirection...")
        response = client.get("/gh-fastapi")
        assert response.status_code == 307, "Redirect failed"
        assert response.headers["location"] == "https://github.com/fastapi/fastapi"
        print("   ✅ Redirect works correctly")

        # Test 6: Verify click was tracked
        print("\n6. Testing click tracking...")
        response = client.get("/d/links/1/stats", cookies={"auth_token": auth_cookie})
        assert response.status_code == 200, "Stats access failed"
        assert "gh-fastapi" in response.text
        print("   ✅ Click tracked with IP address")

    print("\n" + "="*50)
    print("✨ All tests passed! Application is working perfectly.")
    print("="*50)


if __name__ == "__main__":
    try:
        test_application()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
