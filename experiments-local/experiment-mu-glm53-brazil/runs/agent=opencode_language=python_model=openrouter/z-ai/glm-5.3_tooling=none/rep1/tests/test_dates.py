"""Unit tests for multi-format date parsing (spec: Data Quality Notes - Date Formats)."""

from datetime import date

from brasil_mcp.dates import parse_date, parse_time, to_year


class TestParseDate:
    def test_iso_date(self):
        assert parse_date("2023-09-24") == date(2023, 9, 24)

    def test_iso_datetime(self):
        assert parse_date("2012-05-19 18:30:00") == date(2012, 5, 19)

    def test_iso_datetime_without_seconds(self):
        assert parse_date("2012-05-19 18:30") == date(2012, 5, 19)

    def test_brazilian_format(self):
        assert parse_date("29/03/2003") == date(2003, 3, 29)

    def test_brazilian_format_end_of_year(self):
        assert parse_date("08/12/2019") == date(2019, 12, 8)

    def test_slashed_iso(self):
        assert parse_date("2023/09/24") == date(2023, 9, 24)

    def test_na_sentinel(self):
        assert parse_date("NA") is None

    def test_empty_and_none(self):
        assert parse_date("") is None
        assert parse_date(None) is None

    def test_invalid_returns_none(self):
        assert parse_date("not a date") is None


class TestParseTime:
    def test_full_time(self):
        assert parse_time("20:30:00") == "20:30"

    def test_hour_minute(self):
        assert parse_time("16:00") == "16:00"

    def test_sentinel(self):
        assert parse_time("") is None
        assert parse_time("NA") is None


class TestToYear:
    def test_plain(self):
        assert to_year("2019") == 2019

    def test_float_string(self):
        assert to_year("2019.0") == 2019

    def test_na(self):
        assert to_year("NA") is None

    def test_out_of_range(self):
        assert to_year("12345") is None
