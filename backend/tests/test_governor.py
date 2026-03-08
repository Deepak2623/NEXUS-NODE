"""Tests for the GovernorNode and PII scrubber."""

from __future__ import annotations

from governance.pii_scrubber import scrub_dict, scrub_json_str, scrub_text


class TestPIIScrubber:
    """Tests for PII scrubbing functions."""

    def test_email_redacted(self) -> None:
        result = scrub_text("Contact user@example.com for help")
        assert "[REDACTED:EMAIL]" in result.text
        assert "user@example.com" not in result.text
        assert "EMAIL" in result.flags

    def test_ssn_redacted(self) -> None:
        result = scrub_text("SSN: 123-45-6789")
        assert "[REDACTED:SSN]" in result.text
        assert "123-45-6789" not in result.text
        assert "SSN" in result.flags

    def test_phone_redacted(self) -> None:
        result = scrub_text("Call me at (415) 555-1234")
        assert "[REDACTED:PHONE]" in result.text
        assert "PHONE" in result.flags

    def test_ip_redacted(self) -> None:
        result = scrub_text("Request from 192.168.1.100")
        assert "[REDACTED:IP_ADDRESS]" in result.text
        assert "IP_ADDRESS" in result.flags

    def test_no_pii_unchanged(self) -> None:
        result = scrub_text("Hello, world! Everything is fine.")
        assert result.text == "Hello, world! Everything is fine."
        assert result.flags == []

    def test_dict_scrub(self) -> None:
        data = {"user": "admin@corp.com", "note": "no PII here", "nested": {"ip": "10.0.0.1"}}
        scrubbed, flags = scrub_dict(data)
        assert "admin@corp.com" not in str(scrubbed)
        assert "10.0.0.1" not in str(scrubbed)
        assert "EMAIL" in flags
        assert "IP_ADDRESS" in flags

    def test_json_str_scrub(self) -> None:
        raw = '{"email": "test@example.org", "data": "clean"}'
        scrubbed, flags = scrub_json_str(raw)
        assert "test@example.org" not in scrubbed
        assert "EMAIL" in flags
