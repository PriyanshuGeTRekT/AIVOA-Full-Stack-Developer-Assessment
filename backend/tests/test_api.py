"""HTTP API tests."""

from app import crud
from app.services.processing import process_complaint


SAMPLE = (
    "Amoxicillin 500mg capsules, batch AMX-2405-118, contain black particles. "
    "Reported by Sunrise Pharmacy, contact: pharmacist@sunrisepharma.com"
)


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["llm_mode"] == "heuristic"


def test_create_and_list_complaint(client):
    res = client.post("/api/complaints", json={"source_text": SAMPLE})
    assert res.status_code == 201
    created = res.json()
    assert created["reference"].startswith("CMP-")
    assert created["processing_state"] == "done"
    assert created["batch_number"] == "AMX-2405-118"
    assert created["risk_level"] in {"Critical", "Major", "Minor"}

    listed = client.get("/api/complaints")
    assert listed.status_code == 200
    page = listed.json()
    assert page["total"] >= 1
    assert len(page["items"]) >= 1
    assert page["items"][0]["id"] == created["id"]


def test_filter_by_risk(client):
    client.post("/api/complaints", json={"source_text": SAMPLE})
    res = client.get("/api/complaints", params={"risk_level": "Critical"})
    assert res.status_code == 200
    for row in res.json()["items"]:
        assert row["risk_level"] == "Critical"


def test_status_transition_and_conflict(client):
    created = client.post("/api/complaints", json={"source_text": SAMPLE}).json()
    cid = created["id"]

    ok = client.patch(f"/api/complaints/{cid}/status", json={"status": "under_review"})
    assert ok.status_code == 200
    assert ok.json()["status"] == "under_review"

    # open -> closed is allowed from open only; from under_review closed is fine
    closed = client.patch(f"/api/complaints/{cid}/status", json={"status": "closed"})
    assert closed.status_code == 200

    # closed -> open is not allowed
    bad = client.patch(f"/api/complaints/{cid}/status", json={"status": "open"})
    assert bad.status_code == 409


def test_risk_override_survives_reprocess(client, db_session):
    created = client.post("/api/complaints", json={"source_text": SAMPLE}).json()
    cid = created["id"]

    overridden = client.patch(
        f"/api/complaints/{cid}/risk",
        json={"risk_level": "Minor", "reason": "Confirmed cosmetic only"},
    )
    assert overridden.status_code == 200
    assert overridden.json()["risk_level"] == "Minor"
    assert overridden.json()["risk_overridden"] is True

    # Force sync reprocess through the service (background would use another session).
    complaint = crud.get_complaint(db_session, cid)
    process_complaint(db_session, complaint)
    detail = client.get(f"/api/complaints/{cid}").json()
    assert detail["risk_level"] == "Minor"
    assert detail["risk_overridden"] is True
    assert detail["ai_risk_level"] is not None


def test_get_missing_complaint(client):
    res = client.get("/api/complaints/99999")
    assert res.status_code == 404


def test_search_query(client):
    client.post("/api/complaints", json={"source_text": SAMPLE})
    res = client.get("/api/complaints", params={"q": "AMX-2405"})
    assert res.status_code == 200
    assert res.json()["total"] >= 1


def test_stats_shape(client):
    client.post("/api/complaints", json={"source_text": SAMPLE})
    res = client.get("/api/stats")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert "processing" in body


def test_upload_rejects_bad_extension(client):
    res = client.post(
        "/api/complaints/upload",
        files={"file": ("malware.exe", b"not a real file", "application/octet-stream")},
    )
    assert res.status_code == 422
