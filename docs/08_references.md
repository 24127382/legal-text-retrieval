# 08 — Tài liệu tham khảo

Danh mục giữ các nguồn của research document gốc và bổ sung PRF, generative retrieval, distillation/pseudo-labeling. Link ưu tiên publisher, conference hoặc ACL Anthology. Thông tin competition có thể thay đổi; luôn đối chiếu rules/scorer hiện hành.

## Competition và Vietnamese legal/IR

1. CITD, ĐHQG-HCM. “Cuộc thi UIT Data Science Challenge 2026.” 2026. <https://www.citd.edu.vn/cuoc-thi-uit-data-science-challenge-2026/>
2. UIT Data Science Challenge 2026. “Subtask 1: Legal Information Retrieval (LegalIR).” Codabench forum. <https://www.codabench.org/forums/17405/>
3. UIT Data Science Challenge 2026. “Subtask 2: Legal Question Answering (LegalQA).” Codabench. <https://www.codabench.org/competitions/17716/>; forum <https://www.codabench.org/forums/17406/>
4. Xuan Duong Hieu, Thanh Dat Do. “DRiLL at VLSP 2025: A Simple Two-Stage Retrieval Framework for Vietnamese Legal Document Retrieval.” VLSP 2025. <https://aclanthology.org/2025.vlsp-1.20/>
5. Long S. T. Nguyen, Tho T. Quan. “Which Works Best for Vietnamese? A Practical Study of Information Retrieval Methods across Domains.” Findings of EACL 2026. <https://aclanthology.org/2026.findings-eacl.110/>

## Retrieval, fusion và adaptation

6. Stephen Robertson, Hugo Zaragoza. “The Probabilistic Relevance Framework: BM25 and Beyond.” *Foundations and Trends in Information Retrieval*, 2009. <https://doi.org/10.1561/1500000019>
7. Vladimir Karpukhin et al. “Dense Passage Retrieval for Open-Domain Question Answering.” EMNLP 2020. <https://aclanthology.org/2020.emnlp-main.550/>
8. Thibault Formal, Benjamin Piwowarski, Stéphane Clinchant. “SPLADE v2: Sparse Lexical and Expansion Model for Information Retrieval.” 2021. <https://arxiv.org/abs/2107.05720>
9. Omar Khattab, Matei Zaharia. “ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT.” SIGIR 2020. <https://arxiv.org/abs/2004.12832>
10. Jianlv Chen et al. “BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation.” 2024. <https://arxiv.org/abs/2402.03216>
11. Gordon V. Cormack, Charles L. A. Clarke, Stefan Büttcher. “Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods.” SIGIR 2009. <https://doi.org/10.1145/1571941.1572114>
12. Luyu Gao, Xueguang Ma, Jimmy Lin, Jamie Callan. “Precise Zero-Shot Dense Retrieval without Relevance Labels.” ACL 2023. <https://aclanthology.org/2023.acl-long.99/>
13. Yingqi Qu et al. “RocketQA: An Optimized Training Approach to Dense Passage Retrieval for Open-Domain Question Answering.” 2020. <https://arxiv.org/abs/2010.08191>
14. Suchin Gururangan et al. “Don’t Stop Pretraining: Adapt Language Models to Domains and Tasks.” ACL 2020. <https://aclanthology.org/2020.acl-main.740/>
15. Gautier Izacard et al. “Unsupervised Dense Information Retrieval with Contrastive Learning” (Contriever). 2021. <https://arxiv.org/abs/2112.09118>

## PRF, distillation và pseudo-labeling

16. Victor Lavrenko, W. Bruce Croft. “Relevance-Based Language Models.” SIGIR 2001, pp. 120–127. <https://doi.org/10.1145/383952.383972>
17. Nasreen Abdul-Jaleel et al. “UMass at TREC 2004: Novelty and HARD.” TREC 2004. Nguồn thường được dùng cho RM3 interpolation. **TODO: verify citation và stable publisher URL trước khi dùng trong paper.**
18. Sebastian Hofstätter, Sophia Althammer, Michael Schröder, Mete Sertkan, Allan Hanbury. “Improving Efficient Neural Ranking Models with Cross-Architecture Knowledge Distillation.” 2020. <https://arxiv.org/abs/2010.02666>
19. Kexin Wang, Nandan Thakur, Nils Reimers, Iryna Gurevych. “GPL: Generative Pseudo Labeling for Unsupervised Domain Adaptation of Dense Retrieval.” NAACL 2022. <https://aclanthology.org/2022.naacl-main.168/>
20. Chao-Wei Huang, Chen-An Li, Tsu-Yuan Hsu, Chen-Yu Hsu, Yun-Nung Chen. “Unsupervised Multilingual Dense Retrieval via Generative Pseudo Labeling.” Findings of EACL 2024. <https://aclanthology.org/2024.findings-eacl.49/>

## Generative retrieval / document identifiers

21. Yi Tay et al. “Transformer Memory as a Differentiable Search Index.” NeurIPS 2022. <https://papers.nips.cc/paper_files/paper/2022/hash/892840a6123b5ec99ebaab8be1530fba-Abstract-Conference.html>
22. Yujing Wang et al. “A Neural Corpus Indexer for Document Retrieval.” NeurIPS 2022. <https://papers.nips.cc/paper_files/paper/2022/hash/a46156bd3579c3b268108ea6aca71d13-Abstract-Conference.html>

## RAG và LegalQA

23. Patrick Lewis et al. “Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.” NeurIPS 2020. <https://arxiv.org/abs/2005.11401>
24. Gautier Izacard, Edouard Grave. “Leveraging Passage Retrieval with Generative Models for Open Domain Question Answering.” EACL 2021. <https://arxiv.org/abs/2007.01282>
25. Harsh Trivedi, Niranjan Balasubramanian, Tushar Khot, Ashish Sabharwal. “Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step Questions.” ACL 2023. <https://arxiv.org/abs/2212.10509>
26. Akari Asai et al. “Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection.” ICLR 2024. <https://arxiv.org/abs/2310.11511>
27. Shi-Qi Yan et al. “Corrective Retrieval Augmented Generation.” 2024. <https://arxiv.org/abs/2401.15884>
28. Nelson F. Liu et al. “Lost in the Middle: How Language Models Use Long Contexts.” TACL 2024. <https://arxiv.org/abs/2307.03172>

## Adaptation và metrics

29. Edward J. Hu et al. “LoRA: Low-Rank Adaptation of Large Language Models.” 2021. <https://arxiv.org/abs/2106.09685>
30. Tim Dettmers, Artidoro Pagnoni, Ari Holtzman, Luke Zettlemoyer. “QLoRA: Efficient Finetuning of Quantized LLMs.” NeurIPS 2023. <https://arxiv.org/abs/2305.14314>
31. Satanjeev Banerjee, Alon Lavie. “METEOR: An Automatic Metric for MT Evaluation with Improved Correlation with Human Judgments.” ACL Workshop 2005. <https://aclanthology.org/W05-0909/>
32. Chin-Yew Lin. “ROUGE: A Package for Automatic Evaluation of Summaries.” ACL Workshop 2004. <https://aclanthology.org/W04-1013/>
33. Long Ouyang et al. “Training Language Models to Follow Instructions with Human Feedback.” 2022. <https://arxiv.org/abs/2203.02155>
34. Rafael Rafailov et al. “Direct Preference Optimization: Your Language Model is Secretly a Reward Model.” 2023. <https://arxiv.org/abs/2305.18290>

## Vietnamese/multilingual encoders, long context và graph

35. Thanh Vu et al. “VnCoreNLP: A Vietnamese Natural Language Processing Toolkit.” NAACL 2018 Demonstrations. <https://aclanthology.org/N18-5012/>
36. Dat Quoc Nguyen, Anh Tuan Nguyen. “PhoBERT: Pre-trained Language Models for Vietnamese.” Findings of EMNLP 2020. <https://aclanthology.org/2020.findings-emnlp.92/>
37. Alexis Conneau et al. “Unsupervised Cross-lingual Representation Learning at Scale” (XLM-R). ACL 2020. <https://aclanthology.org/2020.acl-main.747/>
38. Iz Beltagy, Matthew E. Peters, Arman Cohan. “Longformer: The Long-Document Transformer.” 2020. <https://arxiv.org/abs/2004.05150>
39. Manzil Zaheer et al. “Big Bird: Transformers for Longer Sequences.” NeurIPS 2020. <https://arxiv.org/abs/2007.14062>
40. Will Hamilton, Zhitao Ying, Jure Leskovec. “Inductive Representation Learning on Large Graphs” (GraphSAGE). NeurIPS 2017. <https://arxiv.org/abs/1706.02216>
41. Michael Schlichtkrull et al. “Modeling Relational Data with Graph Convolutional Networks” (R-GCN). ESWC 2018. <https://arxiv.org/abs/1703.06103>

## Citation hygiene

- Không copy claim benchmark giữa datasets như một kỳ vọng trực tiếp cho UIT DSC 2026.
- Ghi model/paper revision và access date trong experiment artifact khi một source có thể thay đổi.
- Mục có `TODO: verify citation` không được dùng làm citation xuất bản cho đến khi metadata được xác minh.
