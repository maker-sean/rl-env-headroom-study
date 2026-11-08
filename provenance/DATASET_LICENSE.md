# Dataset license verification: CORD v2

Verified 2026-11-05 20:57 EST. Evidence files in this directory were fetched directly, not
summarized. Re-run the commands below to reproduce.

## Dataset

`naver-clova-ix/cord-v2` on Hugging Face. Consolidated Receipt Dataset for
post-OCR parsing, released by NAVER CLOVA IX.

- Hub page: https://huggingface.co/datasets/naver-clova-ix/cord-v2
- Upstream repo: https://github.com/clovaai/cord
- Paper: CORD: A Consolidated Receipt Dataset for Post-OCR Parsing (Park et al., Document Intelligence Workshop at NeurIPS 2019)

## License: CC-BY-4.0, confirmed from two independent sources

### Source 1: Hugging Face dataset metadata API

```
curl -sS "https://huggingface.co/api/datasets/naver-clova-ix/cord-v2"
```

Returned, verbatim:

- `cardData`: `{"license": "cc-by-4.0"}`
- `tags` includes: `license:cc-by-4.0`
- `lastModified`: `2022-07-19T23:43:33.000Z`
- `downloads`: 18732 (at time of check)

Saved: `provenance/cord-v2_hf_api.json`

### Source 2: upstream clovaai/cord repository

```
curl -sS "https://raw.githubusercontent.com/clovaai/cord/master/README.md"
curl -sS "https://raw.githubusercontent.com/clovaai/cord/master/LICENSE-CC-BY"
```

README states, verbatim (lines 3 to 4):

> This work is licensed under a [Creative Commons Attribution 4.0 International
> License][cc-by].

The repository also ships the full license text as `LICENSE-CC-BY`, 395 lines,
matching the Creative Commons Attribution 4.0 International text and opening
with "Attribution 4.0 International".

Saved: `provenance/cord_README.md`, `provenance/cord_LICENSE-CC-BY.txt`

## What CC-BY-4.0 permits for this study

Sharing and adaptation, including commercially, provided attribution is given.
This covers publishing our generation code, our per-document scores, and our
derived analysis in a public repository, with attribution to the CORD authors.

Attribution string to carry in the README and in any derived artifact:

> Receipt documents from CORD v2 (naver-clova-ix/cord-v2), Park et al., NAVER
> CLOVA IX, licensed CC-BY-4.0. https://github.com/clovaai/cord

## Known limitation, recorded before Phase 1

CORD v2 does NOT contain a merchant name or a transaction date. The upstream
README states that `store_info`, `payment_info`, and `etc` fields "have been
removed from the target class to be published". The 42 published subclass
labels contain no store-name or date class.

Consequence for this study: extraction targets are restricted to fields CORD
actually labels, namely line items (name, count, unit price, price), subtotal,
tax, service charge, discount, and total. Merchant and date are out of scope.
No synthetic fields are injected, so every scored target is real ground truth.
