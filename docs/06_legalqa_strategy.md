# 06 — Chiến lược LegalQA

## Nền tảng và trạng thái

LegalQA có thể tái sử dụng LegalIR; không dựng retrieval stack thứ hai nếu không có ablation. Evidence quality tạo factual ceiling:

```text
question → LegalIR B2 → candidate evidence → reranking/selection
         → generator → internal verification → submission answer
```

B2 và QA0–QA4 đều là `Planned`. Code tồn tại ở nơi nào đó chỉ được gọi là `Code present`; không suy ra `Validated` hay `Benchmarked`.

## Internal record khác competition submission

Internal QA artifact có thể giữ:

```text
answer
evidence
document_id
chunk_id
selected spans
retrieval/reranking scores
verification result
citations/provenance
```

Competition submission adapter chỉ emit object keyed theo sample ID, mỗi value có trường `answer`, đúng như `scoring/LegalQA/scoring.py`. Không tự động append citation/provenance vào answer: extra text được chấm và có thể thay `rouge`/`meteor`. Citation và provenance mặc định là research/debug information, không phải trường submission.

## QA baseline ladder

### QA0 — controls

- **Closed-book**: cùng generator chỉ dùng question; đo parametric-only control, không được gọi là grounded solution.
- **Gold evidence + same generator**: oracle control **chỉ khi** dataset hoặc artifact dẫn xuất cung cấp mapping gold evidence đáng tin và đã được audit.
- Nếu không có reliable mapping, ghi oracle là unavailable; không thay bằng retrieved evidence rồi gọi là gold.
- Prompt, decoding, generator revision và output parser phải cố định/versioned.

### QA1 — retrieve–rerank–generate

Question đi qua LegalIR B2, candidate documents/chunks được deduplicate, aggregate/rerank và chọn cho context; cùng generator tạo answer. So với RAG không rerank trên cùng retrieval output để đo giá trị selection/reranking. Citation/provenance nằm trong internal record.

### QA2 — extract-then-generate

Evidence selector lấy span/article/clause hỗ trợ trước generation. So với full-chunk context trên cùng retrieved evidence và cùng context budget. Mục tiêu giả thuyết là giảm distractor, giữ wording pháp lý và không bỏ điều kiện.

### QA3 — verifier

Tách draft answer thành claims và kiểm tra support từ evidence. Policy có thể giữ/sửa/loại claim hoặc abstain, nhưng phải ablate trên cùng draft candidates. Verifier confidence không phải ground truth; cần domain validation/manual audit riêng.

### QA4 — metric-aware answer realization

Sau khi factual grounding được kiểm soát, ablate concise/canonical wording, terminology preservation và answer length. Tối ưu `rouge`/`meteor` không được thay thế factual verifier hoặc làm rơi điều kiện pháp lý.

## Oracle comparison có điều kiện

Khi reliable gold-evidence mapping tồn tại:

```text
question + gold evidence      → same generator/prompt → oracle answer
question + retrieved evidence → same generator/prompt → end-to-end answer
```

Giữ generator, decoding, prompt, context policy và parser giống nhau.

- Oracle cao, end-to-end thấp: retrieval/evidence selection là candidate bottleneck.
- Oracle cũng thấp: generator/reasoning/realization có thể là bottleneck, hoặc gold mapping cần audit lại.
- Oracle factual nhưng official metric thấp: kiểm tra reference variability/tokenizer/format trước khi thay retrieval.
- Retrieved context đã có gold nhưng answer sai: không gọi là retrieval miss; inspect selection/grounding.

Các diễn giải này là decision rules cho experiment, không phải validated results.

## Official evaluation

Scorer trả macro `rouge` (bundled ROUGE-L F-measure) và `meteor` (NLTK METEOR trên whitespace tokens). Không có artifact trong repository xác nhận metric priority. Faithful local evaluation phải reuse organizer scorer/tokenizer; đặc biệt bundled ROUGE tokenizer chỉ giữ ASCII `[a-z0-9]`. Xem contract đầy đủ tại [04 — Evaluation và diagnostics](04_evaluation_and_diagnostics.md).

Factuality, evidence coverage, citation validity, provenance completeness và claim-support là internal diagnostics, không phải official score.

## Advanced research theo failure mode

| Direction | Chỉ GO khi | Câu hỏi kiểm chứng | Status |
|---|---|---|---|
| Extractive QA | Reference map được về source spans | Copy span đủ answer coverage? | `Research candidate` |
| FiD | Nhiều sample thật sự cần nhiều passages | Multi-passage fusion hơn concat ở cùng budget? | `Research candidate` |
| Multi-query/rewrite | Retrieval miss do lay language/missing facet | Unique evidence tăng mà drift được kiểm soát? | `Research candidate` |
| HyDE-RAG | Query–law style gap rõ | Auxiliary branch recover evidence ngoài original? | `Research candidate` |
| Iterative RAG / IRCoT | Multi-hop subset đủ lớn | Bước retrieve mới thêm necessary evidence? | `Research candidate` |
| Self-RAG / CRAG | Retrieval quality biến thiên mạnh | Controller chọn đúng khi retrieve/correct? | `Research candidate` |
| Answer best-of-N | Generator variance là lỗi lớn | Verifier chọn answer tốt hơn ổn định? | `Research candidate` |
| SFT / LoRA / QLoRA | QA labels và split đủ tin cậy | Gain là support hay chỉ lexical style? | `Research candidate` |
| DAPT | Domain gap được chứng minh | Continued pretraining giúp cả oracle/retrieved QA? | `Research candidate` |
| Synthetic QA | Có filtering/provenance | False-label rate và target similarity chấp nhận được? | `Research candidate` |
| GraphRAG | Graph precision cao và multi-hop có thật | Graph thêm unique support hay noise? | `Speculative` |
| Joint IR–QA | IR/QA controls đã benchmark và leakage guard rõ | Feedback cải thiện evidence hay học shortcut? | `Speculative` |

Long-context QA là diagnostic/candidate; context lớn có thể tăng distractor và không bảo đảm model dùng evidence ở mọi vị trí.

## Evidence representation và reporting

Mỗi evidence item nên giữ `document_id`, `chunk_id`, title/parent hierarchy, offsets, retrieval branch, stage scores và selected spans. Đây là internal schema hypothesis, không phải competition submission schema. Context budget phải đo theo tokenizer generator; audit việc một document chiếm quá nhiều budget.

Báo riêng official `rouge`/`meteor` và internal evidence/support metrics theo [QA experiment matrix](05_experiment_map.md). Không trình bày internal factuality result như competition score.
