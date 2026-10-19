"""hf_predict must not wait forever on a Space whose queue is stuck."""
import time

from test_api import main  # noqa: F401


class _StuckJob:
    def result(self, timeout=None):
        time.sleep(min(timeout or 0.2, 0.2))
        raise TimeoutError("queue stuck")

    def cancel(self):
        return True


class _StuckClient:
    def __init__(self, *a, **k):
        pass

    def submit(self, *a, **k):
        return _StuckJob()


def test_hf_predict_gives_up_after_the_deadline(monkeypatch):
    monkeypatch.setattr(main, "Client", _StuckClient)
    main._hf_clients.clear()
    t0 = time.time()
    try:
        main.hf_predict("some/space", "text", api_name="/predict", retries=1, timeout=0.2)
        raised = False
    except TimeoutError:
        raised = True
    assert raised and time.time() - t0 < 5


class _OkJob:
    def result(self, timeout=None):
        return "ok"


class _OkClient(_StuckClient):
    def submit(self, *a, **k):
        return _OkJob()


def test_hf_predict_returns_the_result(monkeypatch):
    monkeypatch.setattr(main, "Client", _OkClient)
    main._hf_clients.clear()
    assert main.hf_predict("some/space", "text", retries=1, timeout=1) == "ok"
