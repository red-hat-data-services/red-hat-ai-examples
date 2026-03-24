#!/usr/bin/env bash
# Requires Bash 4+ (macOS ships Bash 3.2; install newer bash via Homebrew if needed).
# Download all 1000 PDFs from the Open RAG Benchmark dataset.
#
# Source: https://huggingface.co/datasets/deepmatics/open_ragbench
# License: CC-BY-NC-4.0
# Papers are arXiv PDFs distributed under arXiv's non-exclusive license.
#
# Usage:
#   ./fetch_sample_pdfs.sh                       # downloads to ./sample_pdfs/
#   ./fetch_sample_pdfs.sh /mnt/data/input/pdfs  # downloads to PVC path
#
# The script fetches pdf_urls.json from the dataset, then downloads each PDF
# with up to MAX_PARALLEL concurrent downloads. Existing files are skipped.
set -euo pipefail

DEST="${1:-./sample_pdfs}"
MAX_PARALLEL="${MAX_PARALLEL:-8}"
PDF_URLS_JSON="https://huggingface.co/datasets/deepmatics/open_ragbench/resolve/main/pdf/arxiv/pdf_urls.json"

mkdir -p "$DEST"

echo "Fetching PDF URL list from Open RAG Benchmark..."
urls_file=$(mktemp)
trap 'rm -f "$urls_file"' EXIT
curl -sL "$PDF_URLS_JSON" -o "$urls_file"

total=$(python3 -c "import json; print(len(json.load(open('$urls_file'))))")
echo "Found $total PDFs in dataset"

downloaded=0
skipped=0
failed=0

python3 -c "
import json, sys
with open('$urls_file') as f:
    urls = json.load(f)
for paper_id, url in urls.items():
    print(f'{paper_id}\t{url}')
" | while IFS=$'\t' read -r paper_id url; do
    dest_file="$DEST/${paper_id}.pdf"
    if [ -f "$dest_file" ]; then
        skipped=$((skipped + 1))
        continue
    fi

    while [ "$(jobs -r | wc -l)" -ge "$MAX_PARALLEL" ]; do
        wait -n 2>/dev/null || true
    done

    (
        if curl -sL --fail --retry 2 --retry-delay 2 "$url" -o "$dest_file" 2>/dev/null; then
            echo "  fetched $paper_id.pdf"
        else
            rm -f "$dest_file"
            echo "  FAILED  $paper_id.pdf" >&2
            failed=$((failed + 1))
        fi
    ) &

    downloaded=$((downloaded + 1))
    if [ $((downloaded % 50)) -eq 0 ]; then
        echo "  progress: $downloaded queued..."
    fi
done

wait
echo ""

actual=$(find "$DEST" -name "*.pdf" -type f | wc -l | tr -d ' ')
echo "Done. $actual PDFs in ${DEST}/"
