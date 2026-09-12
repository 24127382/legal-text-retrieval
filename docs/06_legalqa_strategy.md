# 06 — Chiến lược LegalQA

## Nền tảng và trạng thái

LegalQA tiêu thụ canonical evidence records theo [00 — Data contract và preprocessing](00_data_contract_and_preprocessing.md) và có thể tái sử dụng LegalIR; không dựng retrieval stack thứ hai nếu không có ablation. Corpus/evidence quality tạo factual ceiling trước cả retrieval và generation:

```text
raw_question → canonical_question ───────────────→ generator_question
                         └→ retrieval_query → LegalIR B2 → candidate evidence
canonical source → C0 ──────────────────────────→ source-preserving evidence
                                                    ↓
                                      G0 → verification → submission answer
```

G0, B2 và QA0–QA4 đều là `Planned`. Code tồn tại ở nơi nào đó chỉ được gọi là `Code present`; không suy ra `Validated` hay `Benchmarked`.

## Internal record khác competition submission

Internal QA artifact có thể giữ:

```text
answer
raw_question / canonical_question / retrieval_query / generator_question provenance
document_id
chunk_id
structural path
source_text
retrieval_text
selected source span + source offsets when reliable
retrieval/reranking scores
verification result
citations/provenance
```

Mỗi selected span phải recover được tối thiểu `chunk_id → document_id → source document`; structural path/source span được giữ khi parser cung cấp đáng tin. Competition submission adapter chỉ emit object keyed theo sample ID, mỗi value có trường `answer`, đúng như `scoring/LegalQA/scoring.py`. Không tự động append citation/provenance vào answer: extra text được chấm và có thể thay `rouge`/`meteor`. Citation và provenance mặc định là research/debug information, không phải trường submission.

## Retrieval representation khác generator evidence representation

```text
retrieval representation ≠ generator evidence representation
```

Retriever có thể index `retrieval_text` đã prepend title/hierarchy để tăng matching. Generator phải nhận `source_text` hoặc selected source span bảo toàn evidence, cộng **chỉ** structural metadata được chọn có chủ đích và đánh dấu riêng. Không được silently feed retrieval-only prefixes/format artifacts vào generator như thể đó là nguyên văn pháp luật.

Tương tự, retriever nhận một hoặc nhiều versioned `retrieval_query` dẫn xuất từ `canonical_question`, trong khi generator mặc định nhận `generator_question` source-preserving từ canonical. Không silently feed legal rewrite, multi-query hoặc PRF expansion vào generator như thể đó là wording của user. Generator-side rewrite, nếu có, là một QA experiment riêng.

Chunk boundary và metadata enrichment cũng phải tách: đổi `source_text` span là corpus-boundary experiment; đổi title/hierarchy đưa vào retriever hoặc generator là context-policy experiment. Mỗi QA run phải log corpus fingerprint, evidence adapter và field nào thực sự vào generator context.

## G0 — fixed generator control

G0 tạo control ổn định để quy thay đổi QA cho evidence/retrieval/selection, không nhằm tìm globally best large language model (LLM — mô hình ngôn ngữ lớn) và không yêu cầu sweep đắt tiền.

G0 phải freeze/version tối thiểu:

- model/provider/model revision; tokenizer revision nếu applicable;
- prompt template và system/instruction prompt;
- decoding parameters, gồm `temperature`, `top-p`/`top-k` nếu dùng, max output tokens và random seed khi supported;
- context budget và evidence serialization;
- answer extraction/parser và retry policy;
- API/runtime/package version khi relevant.

Nếu API không expose exact model revision, ghi provider model identifier, access date và runtime metadata chính xác nhất có thể. Trước khi QA0 là `Benchmarked`, G0 phải pass fixed-fixture sanity checks cho prompt rendering, context budget, answer/parser/schema và retry behavior; repeated calls phải deterministic khi provider hỗ trợ, hoặc có artifact mô tả variance khi không thể bảo đảm.

QA0–QA4 mặc định giữ G0 cố định. Một successor phải có ID/config artifact riêng; generator comparison là research axis riêng. Thay `retriever + generator` trong cùng experiment phá causal attribution.

## Cross-task mapping và oracle granularity

Audit local hiện quan sát train sample IDs rời nhau nhưng có 21 exact-shared question text, với mapping gồm `1:1`, `1:2`, `1:3` và `2:1`; public-official có một exact-shared question và cũng không chung sample ID. Hai task có local `selected-contexts/` directories cùng fingerprint, và các LegalIR gold document IDs quan sát được resolve về corpus LegalIR. Đây là structural relationship, không phải full pairing.

Ba khái niệm không được gộp:

```text
gold document         = document ID được label relevant
gold evidence passage = passage/unit cụ thể được xác nhận hỗ trợ answer
gold evidence span    = exact source span/offset được xác nhận hỗ trợ answer
```

Vì vậy `gold-document oracle != gold-passage oracle != gold-span oracle`. LegalIR document-level labels cho exact-matched question chỉ có thể tạo gold-document oracle candidate: chúng không chứng minh passage/span nào hỗ trợ LegalQA answer. Mọi cross-task use còn phụ thuộc competition-rule permission; local overviews không xác nhận quyền này, nên oracle phải unavailable cho đến khi mapping coverage, relevance/support và allowed use có artifact.

Claim hợp lệ theo variant:

- **Gold-document oracle:** generator nhận document đã label relevant; chỉ đo upper/control dưới document selection đã biết, còn passage selection và support localization chưa oracle.
- **Gold-passage oracle:** generator nhận passage đã được verify hỗ trợ; không claim exact offsets nếu chúng chưa được annotate.
- **Gold-span oracle:** generator nhận exact verified source span/offset; đây mới là oracle cho span selection.

## QA baseline ladder

### QA0 — controls

- **Closed-book**: `generator_question + G0`, không evidence; đo parametric-only control, không được gọi là grounded solution và không cần LegalIR.
- **Oracle + same G0**: chỉ dùng gold document/passage/span condition đúng với granularity mapping đã verify và được phép.
- Nếu không có reliable mapping, ghi oracle là unavailable; không thay bằng retrieved evidence rồi gọi là gold.
- G0, `generator_question` và output adapter phải cố định/versioned giữa conditions.

### QA1 — retrieve–rerank–generate

`retrieval_query` đi qua LegalIR B2 trên canonical corpus đã qua D06a và index đã qua D06b. Candidate documents/chunks được deduplicate, aggregate/rerank và chuyển từ retrieval records thành source-preserving generator evidence; `generator_question + G0` tạo answer. So với RAG không rerank trên cùng retrieval output để đo giá trị selection/reranking. Citation/provenance nằm trong internal record.

### QA2 — extract-then-generate

Evidence selector lấy source span/article/clause hỗ trợ trước generation. So với full-`source_text` chunk context trên cùng retrieved evidence và cùng context budget. Mục tiêu giả thuyết là giảm distractor, giữ wording pháp lý và không bỏ điều kiện; selected span phải map lại được về source evidence.

### QA3 — verifier

Tách draft answer thành claims và kiểm tra support từ evidence. Policy có thể giữ/sửa/loại claim hoặc abstain, nhưng phải ablate trên cùng draft candidates. Verifier confidence không phải ground truth; cần domain validation/manual audit riêng.

### QA4 — metric-aware answer realization

Sau khi factual grounding được kiểm soát, ablate concise/canonical wording, terminology preservation và answer length. Tối ưu `rouge`/`meteor` không được thay thế factual verifier hoặc làm rơi điều kiện pháp lý.

## Oracle comparison có điều kiện

Khi reliable mapping ở một granularity cụ thể tồn tại và được phép dùng:

```text
generator_question + gold document/passage/span → same G0 → oracle answer
generator_question + retrieved evidence          → same G0 → end-to-end answer
```

Giữ G0, context policy, canonical corpus/evidence adapter và parser version giống nhau. Gold-document condition vẫn cần một fixed passage-selection/serialization policy và không được diễn giải như gold-span condition.

- Oracle cao, end-to-end thấp: retrieval/evidence selection là candidate bottleneck.
- Oracle cũng thấp: generator/reasoning/realization có thể là bottleneck, hoặc oracle mapping/granularity cần audit lại.
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

Mỗi evidence item nên giữ `document_id`, `chunk_id`, structural path, `source_text`, `retrieval_text`, reliable offsets, retrieval branch, stage scores và selected source spans. Question record giữ riêng canonical/retrieval/generator representations và transform provenance. Đây là internal conceptual contract, không phải competition submission schema. Context budget phải đo theo G0 tokenizer; audit việc enrichment hoặc một document chiếm quá nhiều budget và report truncation riêng.

Báo riêng official `rouge`/`meteor` và internal evidence/support metrics theo [QA experiment matrix](05_experiment_map.md). Không trình bày internal factuality result như competition score.
