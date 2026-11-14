import pytest

from fintechagent import cli


@pytest.fixture
def env(monkeypatch, db_path, products_dir):
    monkeypatch.setenv("DB_URL", str(db_path))
    monkeypatch.setenv("PRODUCTS_DIR", str(products_dir))
    monkeypatch.delenv("SARVAM_AI_API", raising=False)


def test_no_command_prints_help(capsys):
    assert cli.main([]) == 0
    assert "usage: bulbul" in capsys.readouterr().out


def test_customers(env, capsys):
    assert cli.main(["customers"]) == 0
    out = capsys.readouterr().out
    assert "Akhil" in out and "World Safari Credit Card" in out
    assert "Bhushan" in out and "Movies and More Credit Card" in out


def test_products(env, capsys):
    assert cli.main(["products"]) == 0
    assert "Platinum ValuePlus Credit Card (default)" in capsys.readouterr().out


def test_talk_without_key_fails_cleanly(env, capsys):
    assert cli.main(["talk", "--text"]) == 1
    assert "SARVAM_AI_API is not set" in capsys.readouterr().err


def test_unknown_customer(env, capsys):
    assert cli.main(["talk", "--customer", "Zed"]) == 1
    assert "Known: Akhil, Bhushan" in capsys.readouterr().err


def test_missing_db(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("DB_URL", str(tmp_path / "missing.sqlite"))
    assert cli.main(["customers"]) == 1
    assert "yoyo apply" in capsys.readouterr().err


def test_db_flag_overrides_env(monkeypatch, db_path, products_dir, capsys):
    monkeypatch.setenv("DB_URL", "/nonexistent.sqlite")
    assert cli.main(["--db", str(db_path), "--products-dir", str(products_dir), "customers"]) == 0


def test_text_talk_end_to_end(env, monkeypatch, capsys):
    monkeypatch.setenv("SARVAM_AI_API", "test-key")
    asked: list[str] = []

    def fake_answer(self, context, question, description):
        asked.append(question.question)
        from fintechagent.sarvam import Answer

        return Answer(question, f"reply to {question.question[:10]}", "", "")

    inputs = iter(["What is the annual fee?", "stop"])
    monkeypatch.setattr(cli.Sarvam, "answer", fake_answer)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))
    assert cli.main(["talk", "--text", "--customer", "bhushan"]) == 0
    out = capsys.readouterr().out
    assert "Hi Bhushan" in out and "Movies and More Credit Card" in out
    assert asked[1] == "What is the annual fee?"
    assert "Thank you!" in out


def test_voice_mode_fails_fast_without_audio(env, monkeypatch, capsys):
    import sys

    monkeypatch.setenv("SARVAM_AI_API", "test-key")
    monkeypatch.setitem(sys.modules, "sounddevice", None)
    called = []
    monkeypatch.setattr(cli.Sarvam, "tts", lambda *a: called.append(a))
    assert cli.main(["talk"]) == 1
    assert "--text" in capsys.readouterr().err
    assert called == []


def test_env_file_is_loaded(monkeypatch, tmp_path, db_path, products_dir, capsys):
    monkeypatch.delenv("DB_URL", raising=False)
    monkeypatch.setenv("PRODUCTS_DIR", str(products_dir))
    env_file = tmp_path / "custom.env"
    env_file.write_text(f"DB_URL={db_path}\n")
    assert cli.main(["--env-file", str(env_file), "customers"]) == 0
    assert "Akhil" in capsys.readouterr().out
