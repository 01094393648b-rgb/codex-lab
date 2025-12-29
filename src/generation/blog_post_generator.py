"""Blog post generator without external LLMs.

This module produces a structured blog post optimized for readability and
SEO-friendly distribution of keywords. It relies solely on template logic to
craft section headings and paragraphs based on the provided title, keywords,
and comment insights.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Sequence


@dataclass
class CommentSummary:
    """Aggregated information distilled from user comments.

    Attributes:
        highlights: Positive remarks or takeaways repeatedly seen in comments.
        pain_points: Frequent frustrations or obstacles expressed by readers.
        wishes: Suggestions or requests that indicate desired outcomes.
        tone: Optional description of the community's overall tone.
    """

    highlights: List[str] = field(default_factory=list)
    pain_points: List[str] = field(default_factory=list)
    wishes: List[str] = field(default_factory=list)
    tone: str | None = None


class BlogPostGenerator:
    """Generate a structured blog post using rule-based templates.

    The generator creates four sections (introduction, problem framing,
    informative body, and wrap-up). Keywords are sprinkled across the
    paragraphs with natural spacing to avoid repetition. Comment summaries are
    woven into the narrative to align content with reader interests.
    """

    section_order: Sequence[str] = (
        "서론",
        "문제 제기",
        "정보 제공",
        "정리",
    )

    def __init__(self, *, keywords_per_section: int = 2) -> None:
        """Initialize the generator.

        Args:
            keywords_per_section: Maximum number of keywords to apply in each
                section to prevent unnatural repetition.
        """

        self.keywords_per_section = keywords_per_section

    def generate(self, title: str, keywords: Iterable[str], comment_summary: CommentSummary) -> str:
        """Create a full blog post.

        Args:
            title: Blog post title.
            keywords: List of primary keywords to weave into the copy.
            comment_summary: Parsed comment insights to ground the content.

        Returns:
            A composed blog post string containing headings, subheadings, and
            paragraphs.
        """

        keywords = [kw.strip() for kw in keywords if kw.strip()]
        outline = self._build_outline(title, keywords)
        sections = []

        for idx, section_name in enumerate(self.section_order):
            assigned_keywords = self._keywords_for_section(keywords, idx)
            section_body = self._build_section(
                section_name=section_name,
                title=title,
                keywords=assigned_keywords,
                comment_summary=comment_summary,
            )
            sections.append(section_body)

        return "\n\n".join(outline + sections)

    def _build_outline(self, title: str, keywords: Sequence[str]) -> List[str]:
        seo_hint = ", ".join(keywords[:3]) if keywords else "핵심 포인트"
        outline_lines = [
            f"# {title}",
            f"- 주제 키워드: {seo_hint}",
            "- 구성: 서론 → 문제 제기 → 정보 제공 → 정리",
        ]
        return outline_lines

    def _build_section(
        self,
        *,
        section_name: str,
        title: str,
        keywords: Sequence[str],
        comment_summary: CommentSummary,
    ) -> str:
        heading = f"## {section_name}"
        subheading = self._build_subheading(section_name, title, comment_summary)
        paragraph = self._build_paragraph(section_name, keywords, comment_summary)
        return "\n".join([heading, f"### {subheading}", paragraph])

    def _build_subheading(self, section_name: str, title: str, comment_summary: CommentSummary) -> str:
        tone_hint = comment_summary.tone or "독자 의견"
        if section_name == "서론":
            return f"{title}를 살펴보기 위한 첫걸음"
        if section_name == "문제 제기":
            return f"{tone_hint} 속에서 드러난 고민"
        if section_name == "정보 제공":
            return "핵심 정보와 적용 팁"
        return "정리하며 살펴볼 핵심 포인트"

    def _build_paragraph(
        self, section_name: str, keywords: Sequence[str], comment_summary: CommentSummary
    ) -> str:
        keyword_text = self._scatter_keywords(keywords)
        highlights = ", ".join(comment_summary.highlights[:2]) or "주목 받은 의견"
        pain_points = ", ".join(comment_summary.pain_points[:2]) or "해결이 필요한 문제"
        wishes = ", ".join(comment_summary.wishes[:2]) or "독자가 바라는 방향"

        if section_name == "서론":
            return (
                f"읽기 쉬운 흐름으로 시작합니다. {keyword_text}를 자연스럽게 녹여 "
                "주제를 소개하고, 독자가 궁금해할 질문을 던집니다."
            )
        if section_name == "문제 제기":
            return (
                f"댓글에서 특히 언급된 '{pain_points}'를 토대로 문제를 정리합니다. "
                f"{keyword_text}를 과도하지 않게 배치해 공감대를 형성합니다."
            )
        if section_name == "정보 제공":
            return (
                f"실제 독자가 강조한 '{highlights}'와 바라는 '{wishes}'를 중심으로 "
                f"정보와 사례를 제시합니다. {keyword_text}는 활용 팁과 함께 배치해 "
                "검색 가독성을 높입니다."
            )
        return (
            f"앞서 다룬 내용을 간결하게 요약하며 {keyword_text}를 다시 한 번 짚습니다. "
            f"독자가 바로 적용할 수 있는 다음 행동을 안내하고 톤을 '{comment_summary.tone or '긍정적'}'으로 유지합니다."
        )

    def _scatter_keywords(self, keywords: Sequence[str]) -> str:
        if not keywords:
            return "핵심 키워드"
        return "와 ".join(keywords[: self.keywords_per_section])

    def _keywords_for_section(self, keywords: Sequence[str], section_index: int) -> List[str]:
        start = section_index * self.keywords_per_section
        end = start + self.keywords_per_section
        return list(keywords[start:end]) or list(keywords[: self.keywords_per_section])


__all__ = ["BlogPostGenerator", "CommentSummary"]
