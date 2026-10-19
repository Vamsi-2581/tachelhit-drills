"""A capture processed on another backend (agent --process-at) is reported done with its
drill count; the foreign job id is never looked up here."""
from test_api import client


def test_done_with_drills_created_closes_the_request_without_a_job():
    rid = client.post("/capture/request", json={"url": "https://www.youtube.com/watch?v=abc123def45", "tag": "t"}).json()["request_id"]
    client.get("/capture/pending")  # the agent claims it
    r = client.post(f"/capture/{rid}/done", json={"job_id": 41, "drills_created": 12})
    assert r.status_code == 200
    s = client.get(f"/capture/{rid}").json()
    assert s["status"] == "done" and s["drills_created"] == 12 and s["job_id"] is None and s["job_status"] is None


def test_done_without_drill_count_keeps_the_old_contract():
    rid = client.post("/capture/request", json={"url": "https://www.youtube.com/watch?v=abc123def46"}).json()["request_id"]
    client.get("/capture/pending")
    client.post(f"/capture/{rid}/done", json={"job_id": 999999})
    s = client.get(f"/capture/{rid}").json()
    assert s["status"] == "processing" and s["job_id"] == 999999
