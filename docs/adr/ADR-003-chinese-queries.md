# ADR-003: Chinese requirements reach the model as a human-confirmed English query

Status: **Accepted** for v1 (implemented: `query_en` is mandatory in `set_requirement`). A multilingual
encoder is a Stage II experiment.

## Context
- Scripts and requirements are written in Traditional Chinese. OpenAI CLIP ViT-B/32 was trained on English
  text, and its tokenizer and retrieval quality for Chinese are poor.
- Multilingual options exist, but none is the "same weights" pair of our image encoder:
  - **sentence-transformers `clip-ViT-B-32-multilingual-v1`** (Apache-2.0): a multilingual DistilBERT student
    distilled into the clip-ViT-B-32 text space, with zh-cn and zh-tw in its alignment list. It pairs with the
    unchanged ViT-B/32 image encoder (so it works with the route-A HEF). The card publishes no accuracy.
  - **M-CLIP `XLM-Roberta-Large-Vit-B-32`**: pairs with OpenAI ViT-B/32. Text→image R@10 for Zh is 89.3 vs
    91.8 for En on translated MS-COCO. The card does not state a licence, and its authors say it has not been
    extensively evaluated.
  - **SigLIP2 B/32-256** (Apache-2.0): a multilingual matched pair whose image **and** text HEFs exist for
    Hailo-10H. It needs lowercasing and padding to 64 tokens. It has a different embedding space, so it needs
    a new reference and a new τ.
- Product rule: Chinese goes through a human-confirmed English query unless a **validated** multilingual
  encoder is used.

## Decision
- v1: each requirement stores the user's Chinese `source_text` and an English `query_en` that a person has
  confirmed (a suggested translation may be shown, but it is never used unconfirmed). Only `query_en`
  reaches the encoder. Editing either creates a new revision and marks the old snapshot outdated.
- Stage II experiment: SigLIP2-B/32 (preferred, because the matched pair also runs on the device) and the
  sentence-transformers student, each with its own fingerprint and τ. On the dev split, compare Chinese
  `source_text` queries with confirmed English queries.
- A multilingual path is accepted only if its Chinese-query Recall@5 is no more than 3 points below the
  English-query Recall@5 of the same backend on dev, and it is then confirmed once on test.

## Consequences
- One extra human step per requirement. It also gives an explicit, reviewable statement of what the system
  searched for.
- No silent machine translation: a mistranslation is visible to the person who confirms it.
- A multilingual encoder, if adopted, is a different model with a different fingerprint, so indexes are
  rebuilt.
