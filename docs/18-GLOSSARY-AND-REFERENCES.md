# 18 — Glossary and References

## Glossary

| Term | Meaning in IP Lens |
|---|---|
| Claim | A numbered statement describing an invention feature or combination of features |
| Chunk / passage | A page-bounded section of an uploaded document stored for retrieval |
| ChromaDB | Local vector database used by the MVP to store and search chunk embeddings |
| Citation | A validated reference to a retrieved chunk, including source filename and page marker |
| Cosine distance | A vector-distance value returned by the configured Chroma collection; lower generally means closer vectors |
| LangGraph | A framework for defining explicit graph nodes, state, and transitions for the analysis flow |
| Novelty-risk triage | A provisional heuristic based on comparison coverage and cited retrieval similarity; not a legal opinion |
| Prior art | Earlier publicly available material that may be relevant under patent law; this MVP does not establish legal status or completeness |
| Retrieval similarity | A transformed vector-distance value used to rank/filter passages; not a probability or legal measure |
| Structured output | Model response constrained to a data shape and then validated by Pydantic |

## Official references

- [FastAPI file uploads](https://fastapi.tiangolo.com/tutorial/request-files/)
- [Pydantic documentation](https://docs.pydantic.dev/latest/)
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [Chroma Python client reference](https://docs.trychroma.com/reference/python)
- [Gemini API libraries](https://ai.google.dev/gemini-api/docs/libraries)
- [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output)
- [Gemini API key guidance](https://ai.google.dev/gemini-api/docs/api-key)
- [Streamlit documentation](https://docs.streamlit.io/)
- [Python in Visual Studio Code](https://code.visualstudio.com/docs/languages/python)
- [Copilot setup in Visual Studio Code](https://code.visualstudio.com/docs/setup/copilot)
- [`uv` installation](https://docs.astral.sh/uv/getting-started/installation/)
- [Managing Python with uv](https://docs.astral.sh/uv/guides/install-python/)

## Keeping the docs current

Check official technical documentation when implementation begins because SDK interfaces can change. Record the versions actually chosen in `pyproject.toml` and `uv.lock`. Record benchmark values only with their dataset, settings, and collection date.

