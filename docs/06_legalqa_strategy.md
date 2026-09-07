# 06 — Chiến lược LegalQA

## Nền tảng

LegalQA tái sử dụng LegalIR; không dựng retrieval stack thứ hai mà không có ablation. Evidence quality tạo factual ceiling:

```text
question → LegalIR B2 → reranked evidence → evidence selection
         → LLM → concise grounded answer → verification → final answer
```

Baseline này là `Planned`; `main` chưa có generator, evidence selector hay verifier.

## QA baseline ladder

### QA0 — controls

- Closed-book zero-shot: đo parametric-only floor, không dùng làm grounded solution.
- Gold evidence + zero/few-shot generator: oracle control.
- Prompt phải cố định, versioned; output không chứa chain-of-thought dài.

### QA1 — retrieve–rerank–generate

Question đi qua LegalIR B2, deduplicate/rerank evidence, rồi LLM sinh câu trả lời ngắn kèm citation/trace tới `document_id` và chunk. So sánh với standard RAG không rerank để đo giá trị của evidence ordering.

### QA2 — extract-then-generate

Evidence extractor chọn span/article/clause hỗ trợ trước generation. So với full-chunk context trên cùng retrieved evidence. Mục tiêu là giảm distractor, giữ wording pháp lý và tránh bỏ sót điều kiện.

### QA3 — verifier

Tách answer thành claims, kiểm tra mỗi claim có evidence support bằng citation rule hoặc NLI-style verifier. Unsupported claim bị loại, sửa hoặc chuyển answer sang trạng thái thiếu bằng chứng. Verifier model cũng cần domain validation; confidence của verifier không phải ground truth.

### QA4 — metric-aware realization

Sau khi factuality ổn định, ablate concise canonical formatting, terminology preservation và output length. METEOR/ROUGE-L alignment không được thay factual verifier.

## Oracle experiment bắt buộc

```text
question + gold evidence      → same generator/prompt → oracle answer
question + retrieved evidence → same generator/prompt → end-to-end answer
```

- Oracle mạnh, end-to-end yếu: retrieval/evidence selection là bottleneck.
- Oracle cũng yếu: generator, reasoning hoặc output realization là bottleneck.
- Oracle factual nhưng metric thấp: kiểm tra reference variability/format trước khi đổi retrieval.
- Retrieved evidence có gold nhưng answer sai: đây không phải retrieval miss; inspect selection/grounding.

Giữ generator, decoding, prompt và output parser giống nhau để comparison có ý nghĩa.

## Advanced research theo failure mode

| Direction | Chỉ GO khi | Câu hỏi kiểm chứng |
|---|---|---|
| Extractive QA | Reference có thể map đáng kể về source spans | Copy span có đủ answer coverage không? |
| FiD | Nhiều query thật sự cần nhiều passages | Multi-passage fusion hơn concat ở cùng evidence budget? |
| Multi-query/query rewrite | Retrieval miss do lay language/missing facet | Unique evidence có tăng mà drift được kiểm soát? |
| HyDE-RAG | Query–law style gap rõ | Auxiliary HyDE có recover evidence ngoài original? |
| Iterative RAG / IRCoT | Multi-hop/compositional subset đủ lớn | Bước retrieve mới có thêm necessary evidence? |
| Self-RAG / CRAG | Retrieval quality thay đổi mạnh theo query | Controller/evaluator có chọn đúng khi retrieve/correct? |
| Answer best-of-N | Generator variance là lỗi lớn | Verifier có chọn answer tốt hơn ổn định? |
| SFT / LoRA / QLoRA | QA labels chất lượng và split đủ | Gain là factuality hay chỉ style overlap? |
| DAPT | Domain language gap được chứng minh | Continued pretraining giúp oracle và retrieved QA? |
| Synthetic QA | Có filtering và provenance | Synthetic distribution có giống target, false labels bao nhiêu? |
| GraphRAG | Cross-reference graph precision cao, multi-hop có thật | Graph evidence thêm unique support hay thêm noise? |

Long-context QA là diagnostic/auxiliary: context lớn không bảo đảm model dùng evidence ở mọi vị trí và có thể tăng distractors.

## Evidence representation

Mỗi evidence item giữ: `document_id`, `chunk_id`, title/parent hierarchy, char offsets, retrieval branch, stage scores và selected span. Context budget phải tính theo tokenizer của generator. Khi một document có nhiều chunks, tránh để một document chiếm hết budget nếu query cần multi-document evidence.

## Joint IR–QA optimization — dài hạn

```text
retrieval ↔ evidence supervision ↔ answer generation
```

Các hướng: train retriever từ answer/evidence supervision; jointly optimize evidence relevance và QA quality; dùng QA failures để mine retrieval negatives. Đây không phải baseline đầu tiên vì credit assignment khó và dễ leakage: trước hết cần B2, oracle QA và end-to-end QA ổn định để biết feedback cải thiện retrieval thật hay học shortcut từ answer/reference.

## Báo cáo QA

Ngoài METEOR/ROUGE-L official, báo: gold-evidence coverage, selected-evidence precision/recall nếu labels cho phép, citation validity, claim support rate, abstention/unsupported rate, answer length và error split retrieval miss / selection error / generation-grounding error / formatting error.
