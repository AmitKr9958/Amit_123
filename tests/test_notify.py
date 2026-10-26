from src import notify


def test_html_in_titles_is_escaped(monkeypatch):
    sent = []
    monkeypatch.setattr(notify, "send_message", lambda text, **kw: sent.append(text))
    notify.notify_run_summary(
        jobs_seen=1,
        jobs_scored=1,
        applied=0,
        skipped=0,
        failed=0,
        top_titles=["BI <Lead> & Analytics"],
    )
    assert "&lt;Lead&gt; &amp;" in sent[0]


def test_token_not_leaked_on_failure(monkeypatch, capsys):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:SECRET")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")

    class Boom:
        def __enter__(self):
            raise RuntimeError("POST https://api.telegram.org/bot123:SECRET/sendMessage failed")

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(notify.httpx, "Client", lambda **kw: Boom())
    assert notify.send_message("hi") is False
    assert "SECRET" not in capsys.readouterr().out
