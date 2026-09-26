from luibui_api.settings import get_settings


def test_database_url_is_masked_in_repr() -> None:
    settings = get_settings()
    assert "not-the-password" not in repr(settings)
    assert "not-the-password" not in str(settings.model_dump())
    assert "not-the-password" in settings.database_url.get_secret_value()
