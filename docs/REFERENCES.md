# Framework References

The project structure and showcase deployment behavior were checked against current official LangChain/LangGraph documentation on 2026-08-13.

- LangGraph local Agent Server: https://docs.langchain.com/oss/python/langgraph/local-server
- LangSmith Studio: https://docs.langchain.com/oss/python/langgraph/studio
- LangGraph CLI (`langgraph dev`, host/port options): https://docs.langchain.com/langsmith/cli
- LangGraph interrupts / resume: https://docs.langchain.com/oss/python/langgraph/interrupts
- Human-in-the-loop through Agent Server: https://docs.langchain.com/langsmith/add-human-in-the-loop
- Agent Server persistence behavior: https://docs.langchain.com/oss/python/langgraph/persistence
- Production standalone Agent Server deployment: https://docs.langchain.com/langsmith/deploy-standalone-server

The Kubernetes package intentionally uses the development Agent Server for a lab/showcase because it is directly compatible with Studio and does not require the licensed production standalone deployment stack. See `README.md` and `k8s/README.md`.
