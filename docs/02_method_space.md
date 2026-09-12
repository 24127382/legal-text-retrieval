# 02 — Không gian phương pháp

## Cách đọc taxonomy

**Corpus representation** quyết định evidence unit nào tồn tại; **candidate retrieval** tạo candidate pool rộng; **fusion** hợp nhất nhiều rank/score; **reranking** chấm lại một pool nhỏ; **final selection** quyết định output. Chi phí: `L` thấp, `M` vừa, `H` cao, `VH` rất cao. Priority là thứ tự nghiên cứu tương đối, không phải dự đoán chắc chắn về gain. `Code present` chỉ ghi nhận implementation/prototype quan sát được; không đồng nghĩa `Validated` hoặc `Benchmarked`.

## Method map — Data & Corpus Representation

Các dimensions dưới đây là controllable research axes. Baseline candidate tạo `C0`; research candidate chỉ được promotion sau controlled ablation. Chi tiết invariant nằm tại [00 — Data contract và preprocessing](00_data_contract_and_preprocessing.md).

| Dimension | Baseline candidate | Research candidate | Speculative / conditional | Dependency và rủi ro chính |
|---|---|---|---|---|
| Normalization | NFC/line ending/controlled whitespace, source-preserving | Rule-specific artifact removal đã audit | Learned rewriting/correction | Không xóa numbering, dấu, punctuation hoặc legal wording. |
| Query representation | `raw_question` bất biến; `canonical_question` source-preserving; `retrieval_query` mặc định từ canonical | Versioned citation normalization/rewrite/multi-query/PRF branch, luôn giữ provenance về canonical | Generator-side rewriting | Retrieval transform không overwrite câu hỏi gốc; `generator_question` được kiểm soát độc lập. |
| Legal structure parsing | Conservative headings/boundaries + fallback | Multiple parser rules theo document fingerprint | Learned structure parser | Boundary phải có span/provenance diagnostics; parser hiện chưa được implement lại. |
| Retrieval unit | Một policy deterministic, auditable | Article/clause/point khi meaningful; structure-aware bounded chunks | Learned segmentation | Không có một level phù hợp mọi document. |
| Chunk size/overlap | Fixed config được log | Token-bounded/sliding-window ablation | Query-adaptive chunking | Đo coverage, duplication, truncation; giữ structural policy fixed khi đổi size. |
| Multi-granularity | Single-granularity control | Document + article/clause indexes | Learned routing giữa granularities | Cần dedup/aggregation và cost accounting. |
| Hierarchy/title enrichment | `source_text` không đổi; enrichment tắt hoặc tối thiểu | Prepend/field-weight parent/title vào `retrieval_text` | Learned metadata serialization | Tách boundary khỏi enrichment; đo expansion/truncation. |
| Metadata representation | Chỉ field có source rõ | Soft boost/fielded retrieval | Hard temporal/legal graph filters | Missing khác unknown; không invent metadata. |
| Provenance | Manifest `chunk_id → document_id → source` | Reliable structural unit/source offsets | Claim-level lineage tự động | Hard invariant, không phải optional model feature. |
| Version/temporal metadata | Preserve nếu source có | Normalize/version-link sau validation | Suy đoán hiệu lực từ text | Chỉ dùng khi data/rule có evidence; tránh false filtering. |

`C0` là corpus/preprocessing baseline, không phải model. Khi so retriever, giữ corpus representation fixed; khi so representation, giữ downstream retriever/aggregation fixed.

## Method map — LegalIR

| Family | Mechanism | Failure mode giải quyết | Strength | Weakness / risk | Complementarity | Cost | Priority | Repo status |
|---|---|---|---|---|---|---:|---|---|
| Exact/rule-based citation matching | Parse số luật, Điều/Khoản/Điểm, tên văn bản rồi exact/normalized match | Dense làm mờ identifier | Precision cao, debug được | Không bắt implicit concept/paraphrase | Auxiliary feature cho BM25/dense | L | Cao sau B0 | `Research candidate` |
| TF-IDF / n-gram | Sparse lexical vector trên token/character n-gram | Rare terms, OCR/tokenization variants | Rẻ, interpretable | Semantic gap, length sensitivity | Diversity control cho BM25 | L | Trung bình | `Research candidate` |
| BM25 / BM25F | Probabilistic term weighting; BM25F weight theo field | Exact terminology, citations, title | Classical strong baseline | Vocabulary mismatch; field tuning | Core complement của dense | L–M | Rất cao | `Planned` E00 |
| SPLADE | Transformer học sparse term expansion/weight | Vocabulary mismatch nhưng vẫn cần inverted index | Sparse, interpretable phần nào | Train/index phức tạp; có thể correlate BM25 | Chỉ giữ nếu unique-gold/union recall tăng | H | Cao, Phase 7 | `Planned` E09 |
| Dense bi-encoder | Encode query/document độc lập, nearest-neighbor | Paraphrase và semantic mismatch | Retrieval nhanh sau indexing | Nén nuance; identifier yếu | Core complement của lexical | M–H | Rất cao | `Code present`; E01 `Planned` |
| Multilingual dense / multilingual-E5 | Multilingual embedding objective | Cross-lingual/general Vietnamese representation gap | Strong zero-shot candidate | Chưa chắc hiểu legal nuance | Comparison với BGE-M3 | M–H | Trung bình | `Research candidate` |
| BGE-M3 | Multilingual dense; family hỗ trợ sparse/multi-vector | Paraphrase tiếng Việt, multi-granularity | Backbone hiện có; nhiều modes | Modes cùng backbone có correlated errors | Dense core; modes khác cần ablation | M–H | Rất cao | Dense mode `Code present`; E01 `Planned` |
| ColBERT / late interaction | Token embeddings + MaxSim | Single-vector information bottleneck | Fine-grained query–token match | Index lớn, scoring nặng | Potential unique branch so với BM25/dense | H–VH | Cao, Phase 7 | `Planned` E10 |
| Weighted score fusion | Normalize rồi cộng score theo weight | Single-retriever blind spots | Dùng confidence magnitude | Nhạy scale/calibration | So trực tiếp với RRF | L | Rất cao | `Planned` E02 |
| RRF | Cộng reciprocal rank giữa lists | Heterogeneous score scales | Robust, đơn giản | Bỏ score magnitude; `k` cần tune | So trực tiếp với alpha fusion | L | Rất cao | `Planned` E03 |
| Cross-encoder reranking | Joint encode query–candidate | Similar laws bị first-stage misorder | Full interaction, precision tốt | Chậm; không cứu retrieval miss | Sau candidate recall đủ cao | H | Rất cao | `Planned` E04 |
| LLM reranking | Pointwise/pairwise/listwise instruction scoring | Complex legal relevance | Flexible reasoning | Cost, variance, prompt bias | Late-stage challenger cho CE | VH | Thấp ban đầu | `Research candidate` |
| Query rewriting | Viết lay query thành legal-search query | Lay-language và terminology mismatch | Tăng lexical/semantic match | Query drift, fabricated condition | Luôn giữ original branch | M–H | Sau B2 | `Planned` E11 |
| Multi-query retrieval | Sinh facets/paraphrases, retrieve rồi fuse | Query thiếu facet, multi-aspect | Tăng coverage/diversity | Noise và compute | Original + variants, đo overlap | H | Sau B2 | `Planned` E11 |
| HyDE | Sinh hypothetical document rồi embed | Query–document style mismatch zero-shot | Corpus-style representation | Hallucinated legal detail | Auxiliary, không thay query gốc | H | Trung bình–thấp | `Research candidate` |
| PRF / RM3 | Retrieve lần 1, lấy term từ top docs, expand rồi retrieve lần 2 | Vocabulary mismatch dựa trên corpus | Corpus-grounded hơn generative rewrite | Query drift nếu initial results sai | Nhánh phụ giữ original query | M | Phase 7 | `Planned` E12 |
| Neural PRF | Tổng hợp representation từ top candidates | Semantic expansion khó biểu diễn bằng term | Học feedback giàu hơn | Train/cost, feedback drift | Auxiliary dense branch | H | Sau RM3 | `Research candidate` |
| Title enrichment | Prepend/weight document title | Chunk thiếu scope/topic | Rẻ, legal-specific, prior work hỗ trợ | Title noisy/lặp gây score bias | Orthogonal với backbone | L | Rất cao, Phase 4 | `Planned` D05/E05 |
| Legal hierarchy/structure enrichment | Thêm parent law/chapter/article context | Clause bị mất context | Giữ phạm vi pháp lý | Context noise/truncation | Cùng title nhưng ablate riêng | L–M | Cao, Phase 4 | Metadata `Code present`; D05/E05 `Planned` |
| Hierarchical chunking | Chia theo law→chapter→article→clause | Long-document truncation/dilution | Bảo toàn semantic boundary | Cần document aggregation | Corpus-representation axis | M | Core | `Code present` |
| Metadata-aware retrieval | Boost/filter theo loại, cơ quan, ngày, hiệu lực | Temporal/type ambiguity | Structured signal | Hard filter có thể loại gold | Soft feature cho LTR/reranker | M | Data-dependent | `Research candidate` |
| Contrastive retriever fine-tuning | Kéo positive gần, negative xa | General-domain relevance mismatch | Adapt retrieval objective | False negatives/overfit | Sau stable B2 | H | Phase 6 | `Planned` E08 |
| Hard-negative mining | Train trên near-miss candidates | Similar-law decision boundary | Supervision giàu thông tin | Unlabeled relevant bị đẩy xa | Kỹ thuật train, không phải distillation | H | Phase 5–6 | `Planned` E07/E08 |
| DAPT / TAPT | Continued pretraining trên legal/task corpus | Domain vocabulary/style shift | Adapt encoder trước supervised task | Compute, forgetting, gain không chắc | Ablate trước fine-tuning | VH | Sau B2 | `Research candidate` |
| Synthetic query generation | Sinh query cho corpus passages/docs | Thiếu labeled queries | Tăng supervision/coverage | Distribution/label noise | Có thể feed dense/SPLADE | H | Phase 6–8 | `Research candidate` |
| Learning-to-Rank / LambdaMART | Học từ BM25, dense, metadata, rank features | Hand-tuned fusion không tối ưu | Kết hợp heterogeneous features | Cần labels, dễ leakage/overfit | Sau features ổn định | M–H | Sau B2 | `Research candidate` |
| Graph retrieval / GraphRAG | Expand qua dẫn chiếu, sửa đổi, quan hệ văn bản | Multi-hop/cross-reference | Khai thác legal topology | Edge extraction lỗi lan truyền | Auxiliary signal, không thay text | VH | Dài hạn | `Speculative` |
| Direct document-ID prediction | Query encoder trực tiếp score fixed set IDs; extreme multi-label ranking | Retrieval index không học end-to-end trên fixed corpus | Có thể tận dụng corpus nhỏ/cố định | Memorization, không generalize unseen docs | Diversity/ensemble branch | H | Phase 9 | `Planned` E15 |
| Generative retrieval (DSI/NCI) | Seq2seq sinh document identifier; corpus mã hóa trong parameters | Conventional index tách rời objective | Direct ID optimization | Training phức tạp, catastrophic ID errors, cập nhật corpus khó | Alternative formulation, không phải B0 | VH | Phase 9 thấp | `Planned` E16 |
| Teacher–student distillation | Cross-encoder teacher tạo soft relevance/margins cho cheaper retriever | Student thiếu fine-grained relevance | Chuyển signal phong phú, inference rẻ | Teacher bias/false soft labels | Sau teacher đã được validate | H | Phase 8 | `Planned` E13 |
| Pseudo-labeling / self-training | Gán nhãn unlabeled pairs; lặp train–score–filter | Thiếu labels/domain shift | Mở rộng training set | Confirmation bias/false labels | Có thể dùng teacher và synthetic query | H | Phase 8 | `Planned` E13 |
| Final top-k calibration | Threshold, margin, probability hoặc adaptive k | Ranking tốt nhưng quyết định số output kém | Tối ưu decision layer | Có thể mất Recall; calibration shift | So với always-top-5 | L–M | Sau B2 | `Planned` E14 |

### Vị trí riêng của direct ID và generative retrieval

`query → score document IDs` là extreme classification/ranking trên một label set cố định; nó vẫn có explicit score cho từng ID. DSI/NCI-style `query → model → generated document identifier` là generative retrieval: index nằm trong parameters và identifier có thể được sinh sai. Cả hai khác standard inverted/vector retrieval và phù hợp làm ensemble/diversity research hơn là baseline đầu tiên.

### Distillation khác hard-negative training

```text
strong expensive teacher → soft relevance scores/margins → cheaper student
```

Hard-negative mining quyết định **example nào** đưa vào train; distillation quyết định **target signal nào** student bắt chước. Có thể kết hợp nhưng phải ablate riêng. Teacher-generated hard negatives không tự động đồng nghĩa với soft-label distillation.

## Method map — LegalQA

`G0` là fixed generator control, không phải model-family sweep: model/revision, prompt, decoding, context/evidence serialization và parser/retry/runtime được freeze để QA0–QA4 có causal attribution. Đổi generator về sau là một research axis riêng.

| Family | Mechanism | Failure mode giải quyết | Strength | Weakness / risk | Complementarity | Cost | Priority | Repo status |
|---|---|---|---|---|---|---:|---|---|
| Closed-book baseline | LLM chỉ dùng parameters | Đo giá trị tăng thêm của retrieval | Control rẻ, rõ | Không provenance/version guarantee | Negative control cho RAG | M | Bắt buộc đo | `Planned` QA0 |
| Zero/few-shot prompting | Instruction/examples, không update weights | Thiếu task adaptation | Nhanh, dễ ablate | Prompt variance/context limits | Baseline generator | M | Cao | `Planned` QA0 |
| Standard RAG | Retrieve passages rồi generate | Parametric knowledge thiếu/không cập nhật | Grounding external corpus | Noise nếu retrieval yếu | Core QA baseline | H | Rất cao | `Planned` QA1 |
| Retrieve–rerank–generate | Rerank evidence trước generation | Top retrieval chứa distractors | Context precision cao hơn | Ceiling phụ thuộc candidate recall | Dùng trực tiếp LegalIR B2 | H | Cao nhất | `Planned` QA1 |
| Extractive QA | Chọn span từ evidence | Hallucination/free-form drift | Copy fidelity, provenance | Không tổng hợp nhiều evidence tốt | Oracle/evidence diagnostic | H | Cao | `Research candidate` |
| Extract-then-generate | Extract supporting spans rồi synthesize | Long/noisy evidence | Giảm context noise, giữ legal wording | Extractor có thể bỏ điều kiện | Trước generator/verifier | H | Cao | `Planned` QA2 |
| FiD | Encode passages riêng, fuse ở decoder | Multi-evidence synthesis | Tận dụng nhiều passages | Nặng, distractor-sensitive | Khi data xác nhận multi-doc | VH | Có điều kiện | `Research candidate` |
| Multi-query RAG | Nhiều query facets rồi fuse evidence | Evidence phân tán/query thiếu facet | Coverage | Noise/compute | Giữ original query | H | Sau QA1 | `Research candidate` |
| Query rewriting | Legalize/clarify question cho retrieval | Lay-language mismatch | Better evidence recall | Drift/added legal facts | Auxiliary to original | H | Sau QA1 | `Research candidate` |
| HyDE-RAG | Hypothetical answer/document làm retrieval query | Question–law style gap | Zero-shot diversification | Hallucinated premise | Auxiliary evidence branch | H | Thấp–trung bình | `Research candidate` |
| Iterative/multi-hop RAG | Retrieve–reason–retrieve lặp | Evidence chain nhiều bước | Adaptive evidence discovery | Error propagation/cost | Khi multi-hop được xác nhận | VH | Có điều kiện | `Research candidate` |
| IRCoT | Interleave retrieval và chain-of-thought | Multi-step knowledge-intensive QA | Reasoning-guided retrieval | Reasoning drift, latency | Variant của iterative RAG | VH | Có điều kiện | `Research candidate` |
| Self-RAG | Model quyết định retrieve/critique/generate | Retrieval need/quality không đồng đều | Adaptive self-reflection | Train/implementation phức tạp | Sau measurable QA baseline | VH | Dài hạn | `Research candidate` |
| CRAG | Đánh giá retrieval rồi correct/expand | Bad retrieved evidence | Explicit corrective path | Evaluator errors, branching cost | Với verifier | VH | Dài hạn | `Research candidate` |
| Evidence-grounded internal provenance | Gắn claims với evidence/citation trong internal record | Unsupported answer | Auditability | Citation đúng vị trí chưa chắc entailment; không tự append vào submission | Với verifier/extractor | H | Cao | `Planned` QA2 |
| Evidence/NLI verifier | Kiểm tra claim được evidence entail | Hallucination/unsupported condition | Factual gate | NLI domain mismatch | Sau generation, có thể rerank | H | Cao | `Planned` QA3 |
| Long-context QA | Đưa nhiều/full documents vào context | Truncation/missing evidence | Giảm retrieval granularity | Lost-in-the-middle, cost/noise | Diagnostic/auxiliary | VH | Thấp | `Research candidate` |
| Answer reranking / best-of-N | Sinh N answers rồi score support/quality | Generation variance | Tăng chance answer tốt | Cost; verifier bias | Với grounded verifier | VH | Sau QA2 | `Research candidate` |
| Hidden reasoning + concise final | Reasoning nội bộ, output chỉ answer cần thiết | Verbose output làm lệch metric | Giữ reasoning mà giảm noise | Cần kiểm soát không lộ unsupported steps | Output-control axis | M | Cao sau factuality | `Research candidate` |
| SFT | Supervised fine-tuning QA examples | Prompt-only task/style mismatch | Adapt task trực tiếp | Overfit/label quality | Sau retrieval ổn định | VH | Có điều kiện | `Research candidate` |
| LoRA / QLoRA | Parameter-efficient adaptation | Full fine-tuning quá tốn | Compute/memory thấp hơn | Vẫn overfit; base-model ceiling | PEFT alternative cho SFT | H | Có điều kiện | `Research candidate` |
| DAPT | Continued legal-domain pretraining | Domain language gap | Legal vocabulary/style | Expensive; gain không bảo đảm | Trước SFT, ablate riêng | VH | Dài hạn | `Research candidate` |
| Synthetic QA | Teacher sinh question/evidence/answer | Ít supervision | Scale data | Hallucinated labels/style bias | Cần filtering/verifier | H–VH | Có điều kiện | `Research candidate` |
| Metric-aware answer formatting | Học/đặt format ngắn, canonical | Correct answer nhưng low overlap | Có thể cải thiện official `meteor`/`rouge` | Metric gaming, factuality không tăng | Sau verifier/factuality | L–H | Cao nhưng muộn | `Planned` QA4 |
| GraphRAG | Retrieve graph neighborhood + text | Cross-reference/multi-hop | Structured evidence chain | Noisy graph/edge propagation | Chỉ khi graph quality đủ | VH | Dài hạn | `Speculative` |
| Joint IR–QA optimization | Answer/evidence supervision train retriever; QA failures mine negatives | Pipeline stages tối ưu lệch nhau | Align evidence với answer quality | Credit assignment/leakage/instability | Sau IR và QA controls ổn định | VH | Dài hạn | `Research candidate` |

## Compatibility và chọn thí nghiệm

Các combination có lý do rõ: BM25 + dense (lexical/semantic), retriever + cross-encoder (coverage/precision), title enrichment + mọi backbone (context), extractor + generator (noise/fidelity), verifier + metric-aware formatter (factuality/expression).

Các combination chỉ có điều kiện: SPLADE + BM25, ColBERT + dense, multi-query + PRF, FiD + iterative RAG, graph + text. Chỉ chạy khi overlap/error analysis cho thấy tín hiệu bổ sung hoặc data cho thấy multi-hop.

Tránh cartesian product mọi model × mọi fusion × mọi reranker. Áp dụng hai gate:

> A new retriever is valuable primarily if it increases candidate recall or produces complementary retrieval errors.

> A new reranker is valuable primarily if candidate recall is already high but official recall under the maximum-5 output constraint remains substantially lower.

Và luôn giữ invariant: reranker không thể recover gold document chưa vào candidate pool.
