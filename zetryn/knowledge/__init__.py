"""Static knowledge injection at agent build time.

A `KnowledgePack` loads markdown (becomes system-prompt context) and JSON
(structured lookups) from a directory, so a deployment can ship its own
playbook without editing Python.
"""

from .pack import KnowledgePack, KnowledgePackError

__all__ = ["KnowledgePack", "KnowledgePackError"]
