"""Tests for src/downloader.py."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from downloader import download_detail_pdfs


class TestDownloadDetailPdfs:
    def _make_order(self, order_id, url="https://example.com/pdf"):
        return SimpleNamespace(order_id=order_id, detail_url=url)

    def test_cache_hit(self, tmp_path):
        """Already-downloaded PDFs should be skipped."""
        out_dir = tmp_path / "detail_food"
        out_dir.mkdir()
        cached = out_dir / "111111111111111.pdf"
        cached.write_bytes(b"%PDF-1.4 cached")

        orders = [self._make_order("111111111111111")]

        with patch("downloader.httpx.Client") as mock_client:
            result = download_detail_pdfs(orders, "food", tmp_path)

        assert "111111111111111" in result
        assert result["111111111111111"] == cached
        # Should not have made any HTTP calls
        mock_client.return_value.__enter__.return_value.get.assert_not_called()

    def test_missing_url(self, tmp_path, capsys):
        """Orders with no URL should be skipped."""
        orders = [self._make_order("222222222222222", url="")]

        with patch("downloader.httpx.Client") as mock_client:
            mock_ctx = MagicMock()
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            result = download_detail_pdfs(orders, "food", tmp_path)

        assert "222222222222222" not in result
        assert "No URL" in capsys.readouterr().out

    def test_successful_download(self, tmp_path):
        """Successful HTTP download should save file."""
        orders = [self._make_order("333333333333333")]

        with patch("downloader.httpx.Client") as mock_client:
            mock_ctx = MagicMock()
            mock_resp = MagicMock()
            mock_resp.content = b"%PDF-1.4 downloaded content"
            mock_ctx.get.return_value = mock_resp
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = download_detail_pdfs(orders, "food", tmp_path)

        assert "333333333333333" in result
        saved = tmp_path / "detail_food" / "333333333333333.pdf"
        assert saved.exists()
        assert saved.read_bytes() == b"%PDF-1.4 downloaded content"

    def test_http_error(self, tmp_path, capsys):
        """HTTP errors should be handled gracefully."""
        import httpx

        orders = [self._make_order("444444444444444")]

        with patch("downloader.httpx.Client") as mock_client:
            mock_ctx = MagicMock()
            mock_ctx.get.side_effect = httpx.HTTPError("500 Server Error")
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = download_detail_pdfs(orders, "food", tmp_path)

        assert "444444444444444" not in result
        assert "Failed to download" in capsys.readouterr().out
