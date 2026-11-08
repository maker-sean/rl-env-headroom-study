"""Forecast run cost from MEASURED prompt sizes, not from guesses.

Text token counts are measured with tiktoken o200k_base as a provider-neutral
proxy. Each gateway bills with its own tokenizer, so these are forecasts, not
results. The pilot replaces every number here with exact counts from
Trace.num_input_tokens / num_output_tokens.

Image token cost is NOT forecast. It depends on each provider's tiling scheme,
which is not published in Prime's catalog. The image payload size and
resolution are reported so the pilot can calibrate it empirically.
"""
import json, sys
from pathlib import Path
from statistics import mean, median

sys.path.insert(0, "src")
import tiktoken
from datasets import load_dataset

from doc_extraction_study.cord import image_data_url, ocr_text, parse_ground_truth
from doc_extraction_study.prompts import IMAGE_USER_PROMPT, OCR_USER_PROMPT, SYSTEM_PROMPT

# Tiers from provenance/MODEL_TIERS.md, prices per 1M tokens.
TIERS = {
    "qwen/qwen3-vl-8b-instruct":      (0.117, 0.455),
    "qwen/qwen3-vl-30b-a3b-instruct": (0.200, 0.700),
    "anthropic/claude-opus-5.5":      (4.000, 20.000),
}
ENC = tiktoken.get_encoding("o200k_base")
N_DOCS_FULL, SAMPLES = 100, 3
N_DOCS_PILOT = 20


def main():
    ds = load_dataset("naver-clova-ix/cord-v2", split="validation")
    sys_toks = len(ENC.encode(SYSTEM_PROMPT))

    ocr_in, out_toks, img_chars = [], [], []
    for i in range(len(ds)):
        row = ds[i]
        page = ocr_text(row["ground_truth"])
        ocr_in.append(sys_toks + len(ENC.encode(OCR_USER_PROMPT.format(ocr_text=page))))
        # A perfect reply is the tightest honest proxy for output length.
        truth = parse_ground_truth(row["ground_truth"], f"v{i}")
        out_toks.append(len(ENC.encode(truth.to_model_json())))
        if i < 20:
            img_chars.append(len(image_data_url(row["image"])))

    img_in_text = sys_toks + len(ENC.encode(IMAGE_USER_PROMPT))

    print(f"system prompt: {sys_toks} tokens\n")
    print("MEASURED per-document token counts (o200k_base proxy, n=100)")
    print(f"  ocr_text input : mean {mean(ocr_in):6.0f}  median {median(ocr_in):6.0f}"
          f"  min {min(ocr_in):5d}  max {max(ocr_in):5d}")
    print(f"  image input    : {img_in_text} text tokens + 1 image "
          f"(864x1296, JPEG q90, mean {mean(img_chars)/1024:.0f} KiB payload)")
    print(f"  output (gold)  : mean {mean(out_toks):6.0f}  median {median(out_toks):6.0f}"
          f"  min {min(out_toks):5d}  max {max(out_toks):5d}")
    print("\n  Output is measured on the PERFECT reply. A verbose or rambling model")
    print("  costs more, so treat the output column as a floor.\n")

    rows = []
    print(f"FORECAST: ocr_text condition, {N_DOCS_FULL} docs x {SAMPLES} samples "
          f"= {N_DOCS_FULL*SAMPLES} calls per model")
    print(f"  {'model':<34} {'$in':>8} {'$out':>8} {'$total':>9}")
    total_ocr = 0.0
    for m, (pin, pout) in TIERS.items():
        calls = N_DOCS_FULL * SAMPLES
        cin = sum(ocr_in) * SAMPLES / 1e6 * pin
        cout = sum(out_toks) * SAMPLES / 1e6 * pout
        total_ocr += cin + cout
        rows.append({"condition": "ocr_text", "model": m, "calls": calls,
                     "usd_in": round(cin, 4), "usd_out": round(cout, 4),
                     "usd_total": round(cin + cout, 4)})
        print(f"  {m:<34} {cin:>8.3f} {cout:>8.3f} {cin+cout:>9.3f}")
    print(f"  {'SUBTOTAL (3 tiers, ocr_text)':<34} {'':>8} {'':>8} {total_ocr:>9.3f}\n")

    print("FORECAST: image condition, text tokens only (image tokens unknown)")
    print(f"  {'model':<34} {'$in(text)':>10} {'$out':>8} {'$total':>9}")
    total_img_text = 0.0
    for m, (pin, pout) in TIERS.items():
        calls = N_DOCS_FULL * SAMPLES
        cin = img_in_text * calls / 1e6 * pin
        cout = sum(out_toks) * SAMPLES / 1e6 * pout
        total_img_text += cin + cout
        rows.append({"condition": "image_text_only", "model": m, "calls": calls,
                     "usd_in": round(cin, 4), "usd_out": round(cout, 4),
                     "usd_total": round(cin + cout, 4)})
        print(f"  {m:<34} {cin:>10.3f} {cout:>8.3f} {cin+cout:>9.3f}")
    print(f"  {'SUBTOTAL (3 tiers, image text)':<34} {'':>10} {'':>8} {total_img_text:>9.3f}")
    print("\n  Image tokens are the dominant unknown. At a plausible 1k-2k tokens per")
    print("  page, the frontier tier adds roughly $1.20-$2.40 per 300 calls, and the")
    print("  two open tiers well under $0.20 each. The pilot measures it exactly.\n")

    pilot = total_ocr * (N_DOCS_PILOT / N_DOCS_FULL)
    print(f"PILOT ({N_DOCS_PILOT} docs x {SAMPLES} samples, both conditions, 3 tiers)")
    print(f"  forecast: ${pilot*2:.2f} excluding image tokens\n")
    print(f"BOTH CONDITIONS, FULL RUN, 3 tiers, text only: "
          f"${total_ocr + total_img_text:.2f}")
    print(f"  against the $40 cap: {(total_ocr+total_img_text)/40:.1%} of budget")

    Path("results").mkdir(exist_ok=True)
    Path("results/cost_forecast.json").write_text(json.dumps({
        "note": "FORECAST, not measured spend. tiktoken o200k_base proxy. "
                "Image tokens excluded: provider tiling not published.",
        "system_prompt_tokens": sys_toks,
        "n_docs": N_DOCS_FULL, "samples_per_doc": SAMPLES,
        "ocr_input_tokens": {"mean": round(mean(ocr_in), 1), "sum": sum(ocr_in),
                             "min": min(ocr_in), "max": max(ocr_in)},
        "image_input_text_tokens": img_in_text,
        "image_payload_kib_mean": round(mean(img_chars) / 1024, 1),
        "gold_output_tokens": {"mean": round(mean(out_toks), 1), "sum": sum(out_toks)},
        "prices_usd_per_mtok": {k: {"input": v[0], "output": v[1]} for k, v in TIERS.items()},
        "forecast_rows": rows,
        "forecast_total_usd_text_only": round(total_ocr + total_img_text, 4),
        "cap_usd": 40,
    }, indent=2))
    print("\nwrote results/cost_forecast.json")


if __name__ == "__main__":
    main()
