"""Security tests for link editing and password-protected links."""


def test_hash_never_rendered(authenticated_client):
    from app.db.database import execute_query
    from app.utils.auth import hash_password

    h = hash_password("mypassword")
    link_id = execute_query(
        "INSERT INTO links (user_id, short_code, original_url, password_hash) VALUES (?, ?, ?, ?)",
        (authenticated_client.user_id, "sec-a", "https://example.com", h)
    )
    for url in ("/d/", f"/d/links/{link_id}/edit", f"/d/links/{link_id}/row",
                f"/d/links/{link_id}/stats"):
        body = authenticated_client.get(url).text
        assert h not in body, url
        assert "$argon2" not in body, url


def test_edit_and_row_ownership(authenticated_client):
    from app.db.database import execute_query
    from app.utils.auth import hash_password

    other = execute_query(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        ("o@e.com", hash_password("password123"))
    )
    link_id = execute_query(
        "INSERT INTO links (user_id, short_code, original_url) VALUES (?, ?, ?)",
        (other, "sec-b", "https://example.com")
    )
    assert authenticated_client.get(f"/d/links/{link_id}/edit").status_code == 404
    assert authenticated_client.get(f"/d/links/{link_id}/row").status_code == 404
    assert authenticated_client.delete(f"/d/links/{link_id}").status_code == 403
    assert authenticated_client.get(f"/d/links/{link_id}/stats").status_code == 404


def test_unauthenticated_cannot_edit(client):
    from app.db.database import execute_query

    link_id = execute_query(
        "INSERT INTO links (user_id, short_code, original_url) VALUES (?, ?, ?)",
        (1, "sec-c", "https://example.com")
    )
    assert client.get(f"/d/links/{link_id}/edit").status_code == 401
    assert client.get(f"/d/links/{link_id}/row").status_code == 401
    assert client.put(f"/d/links/{link_id}",
                      data={"original_url": "https://evil.com"}).status_code == 401
    assert execute_query("SELECT original_url FROM links WHERE id = ?", (link_id,),
                         fetch_one=True)["original_url"] == "https://example.com"


def test_short_code_not_editable(authenticated_client):
    from app.db.database import execute_query

    link_id = execute_query(
        "INSERT INTO links (user_id, short_code, original_url) VALUES (?, ?, ?)",
        (authenticated_client.user_id, "sec-d", "https://example.com")
    )
    authenticated_client.put(f"/d/links/{link_id}", data={
        "original_url": "https://new.com", "short_code": "hijacked", "user_id": "999"})
    row = execute_query("SELECT short_code, user_id FROM links WHERE id = ?",
                        (link_id,), fetch_one=True)
    assert row["short_code"] == "sec-d"
    assert row["user_id"] == authenticated_client.user_id


def test_edit_preserves_password_when_blank(authenticated_client, client):
    from app.db.database import execute_query
    from app.utils.auth import hash_password

    link_id = execute_query(
        "INSERT INTO links (user_id, short_code, original_url, password_hash) VALUES (?, ?, ?, ?)",
        (authenticated_client.user_id, "sec-e", "https://old.com", hash_password("pw1234"))
    )
    authenticated_client.put(f"/d/links/{link_id}",
                             data={"original_url": "https://new.com", "password": ""})
    assert client.get("/sec-e", follow_redirects=False).status_code == 401
    r = client.post("/sec-e", data={"password": "pw1234"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "https://new.com"


def test_javascript_url_rejected_on_edit(authenticated_client):
    from app.db.database import execute_query

    link_id = execute_query(
        "INSERT INTO links (user_id, short_code, original_url) VALUES (?, ?, ?)",
        (authenticated_client.user_id, "sec-f", "https://example.com")
    )
    for bad in ("javascript:alert(1)", "data:text/html,<script>alert(1)</script>", "//evil.com"):
        assert authenticated_client.put(
            f"/d/links/{link_id}", data={"original_url": bad}).status_code == 400


def test_xss_in_url_is_escaped(authenticated_client):
    from app.db.database import execute_query

    payload = 'https://e.com/"><script>alert(1)</script>'
    link_id = execute_query(
        "INSERT INTO links (user_id, short_code, original_url) VALUES (?, ?, ?)",
        (authenticated_client.user_id, "sec-g", payload)
    )
    for url in ("/d/", f"/d/links/{link_id}/edit", f"/d/links/{link_id}/row"):
        assert "<script>alert(1)</script>" not in authenticated_client.get(url).text, url


def test_password_min_length_enforced(authenticated_client):
    from app.db.database import execute_query

    link_id = execute_query(
        "INSERT INTO links (user_id, short_code, original_url) VALUES (?, ?, ?)",
        (authenticated_client.user_id, "sec-h", "https://example.com")
    )
    assert authenticated_client.put(f"/d/links/{link_id}", data={
        "original_url": "https://example.com", "password": "ab"}).status_code == 400
    assert authenticated_client.post("/d/links", data={
        "original_url": "https://example.com", "custom_code": "sec-i",
        "password": "ab"}).status_code == 400


def test_malformed_hash_denies_access(authenticated_client, client):
    from app.db.database import execute_query

    execute_query(
        "INSERT INTO links (user_id, short_code, original_url, password_hash) VALUES (?, ?, ?, ?)",
        (authenticated_client.user_id, "sec-j", "https://example.com", "not-a-real-hash")
    )
    assert client.post("/sec-j", data={"password": "anything"}).status_code == 401
    assert client.post("/sec-j", data={"password": "not-a-real-hash"}).status_code == 401
