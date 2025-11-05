#!/usr/bin/env python3
"""
Test HTMX delete behavior.
"""

from httpx import Client

BASE_URL = "http://127.0.0.1:8000"

with Client(base_url=BASE_URL, follow_redirects=False) as client:
    # Register and login
    response = client.post("/auth/register", data={
        "email": "delete-test@example.com",
        "password": "testpass123"
    })
    auth_cookie = response.cookies.get("auth_token")

    # Create a link
    response = client.post("/d/links",
        data={
            "original_url": "https://example.com/test",
            "custom_code": "test-delete-htmx"
        },
        cookies={"auth_token": auth_cookie}
    )
    print("✅ Link created")
    print(f"   Response contains HTML: {len(response.text) > 0}")

    # Delete the link
    response = client.delete("/d/links/1", cookies={"auth_token": auth_cookie})
    print(f"\n✅ Link deleted")
    print(f"   Status: {response.status_code}")
    print(f"   Response body: '{response.text}'")
    print(f"   Response is empty: {response.text == ''}")

    if response.text == "":
        print("\n✨ Perfect! Empty response will properly remove element in HTMX")
    else:
        print(f"\n❌ Problem: Response should be empty but got: {response.text}")
