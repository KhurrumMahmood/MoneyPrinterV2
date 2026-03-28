"""
Input normalization for transcripts, source docs, and topic briefs.
"""

from .sources import build_source_registry, build_topic_brief

__all__ = ["build_source_registry", "build_topic_brief"]
