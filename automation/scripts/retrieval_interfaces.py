"""可替换的嵌入、向量召回和重排契约；本模块不加载模型、不发网络请求。

这些 Protocol 描述未来替换后端的契约；当前具体实现位于 qdrant_backend.py，
直接组合 Qdrant local 与 FastEmbed，并未使用 Protocol 插件加载器。
接口携带内容指纹和模型标识，禁止把不同模型空间或旧内容静默混用。
"""

from typing import Any, Protocol, Sequence


class EmbeddingProvider(Protocol):
    """可使用成熟模型/API，无需本地训练；实现者负责批量、长度与授权边界。"""

    model_id: str
    dimensions: int

    def embed_documents(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...

    def embed_query(self, text: str) -> Sequence[float]: ...


class VectorStore(Protocol):
    """点 payload 至少含 source_id、chunk_id、digest、model_id 和 project。

后端返回的 payload 必须对照当前源注册与指纹检查后才能加入上下文；相似度不是
科学可信度。删除某来源的向量不删除正式来源或反馈历史。
    """

    def upsert(self, points: Sequence[dict[str, Any]]) -> None: ...

    def delete_source(self, source_id: str) -> None: ...

    def search(self, vector: Sequence[float], *, limit: int,
               filters: dict[str, Any]) -> Sequence[dict[str, Any]]: ...


class Reranker(Protocol):
    """可选相关性重排；输出每份候选的分数，不改写候选文本或复核状态。"""

    def score(self, query: str, texts: Sequence[str]) -> Sequence[float]: ...
