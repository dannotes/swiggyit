"""Download detail PDFs from S3 pre-signed URLs to .tmp/ cache."""

from pathlib import Path

import httpx

TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def download_detail_pdfs(
    orders: list,
    order_type: str,
    tmp_dir: Path,
) -> dict[str, Path]:
    """Download detail PDFs for a list of OrderRow objects.

    Returns a dict mapping order_id -> local file path.
    Skips downloads if file already exists (cache).
    """
    out_dir = tmp_dir / f"detail_{order_type}"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    skipped = 0
    downloaded = 0
    failed = 0

    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        for order in orders:
            file_path = out_dir / f"{order.order_id}.pdf"

            if file_path.exists() and file_path.stat().st_size > 0:
                results[order.order_id] = file_path
                skipped += 1
                continue

            if not order.detail_url:
                print(f"  No URL for order {order.order_id}, skipping")
                failed += 1
                continue

            try:
                resp = client.get(order.detail_url)
                resp.raise_for_status()
                file_path.write_bytes(resp.content)
                results[order.order_id] = file_path
                downloaded += 1
            except httpx.HTTPError as e:
                print(f"  Failed to download order {order.order_id}: {e}")
                failed += 1

    print(
        f"  {order_type}: {downloaded} downloaded, "
        f"{skipped} cached, {failed} failed"
    )
    return results
