# Local OCR benchmark model and license notes

Checked on 2026-08-10. This is an engineering shortlist, not legal advice. Keep
the relevant license and copyright notices when distributing a product or model
bundle.

## Included by default

| Benchmark ID | Parameters | Model license | Korean status | Why included |
|---|---:|---|---|---|
| `PaddlePaddle/PaddleOCR-VL-1.6` | 0.9B | Apache-2.0 | Multilingual; benchmark locally | Compact OCR/document VLM and strongest direct successor to the previous PP-OCRv5 test |
| `zai-org/GLM-OCR` | 0.9B | MIT (model); Apache-2.0 (repo/layout pipeline) | Korean is one of its eight advertised languages | Very compact 2026 OCR model; direct text-recognition prompt is used |
| `lightonai/LightOnOCR-2-1B` | 1B | Apache-2.0 | Multilingual, but Korean coverage is not clearly documented | Fast recent OCR specialist; included as an empirical Korean stress test |
| `deepseek-community/DeepSeek-OCR-2` | 3B | Apache-2.0 inherited from the original weights | Tagged multilingual; Korean quality not guaranteed | Transformers-native conversion of DeepSeek's official checkpoint, avoiding a conflicting Transformers 4.46 environment |
| `Qwen/Qwen3-VL-4B-Instruct` | 4B | Apache-2.0 | OCR supports 32 languages; verify Korean handwriting locally | General VLM baseline with a strict no-correction transcription prompt |

All five run locally and do not require an API key. A Hugging Face token is
optional for download rate limits only. There is no per-page model fee, but GPU
infrastructure still costs money.

## Deliberately excluded

| Model | Reason |
|---|---|
| `tencent/HunyuanOCR` / HunyuanOCR 1.5 | Its published community license explicitly excludes South Korea, the EU, and the UK from the licensed territory. Do not use it for this Korean deployment without a separate license. |
| `nanonets/Nanonets-OCR-s` | The official model card does not declare a model license. Excluded until Nanonets supplies clear commercial terms. |
| `rednote-hilab/dots.ocr` | Hugging Face metadata says MIT, but the repository also ships a separate custom model license agreement and notices. Excluded from the low-friction commercial shortlist pending legal review. |
| API-only OCR products | They do not satisfy the local/offline requirement. |

## Evaluation rules

1. Rank only outputs produced from the same manifest and sample count.
2. Use deterministic decoding and no LLM correction.
3. Synthetic font-rendered pages are for screening only.
4. Before production, repeat with at least 30–50 anonymized real handwritten
   fields, including dates, numbers, medication terms, risk phrases, and
   negations.
5. For a counseling record workflow, omissions and altered negations should be
   treated as release blockers even if average CER looks good.

## Primary references

- PaddleOCR-VL 1.6: https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6
- GLM-OCR: https://huggingface.co/zai-org/GLM-OCR
- LightOnOCR-2: https://huggingface.co/lightonai/LightOnOCR-2-1B
- DeepSeek-OCR-2 original: https://huggingface.co/deepseek-ai/DeepSeek-OCR-2
- DeepSeek Transformers-native port: https://huggingface.co/deepseek-community/DeepSeek-OCR-2
- Qwen3-VL-4B-Instruct: https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct
- HunyuanOCR license: https://huggingface.co/tencent/HunyuanOCR/blob/main/LICENSE
