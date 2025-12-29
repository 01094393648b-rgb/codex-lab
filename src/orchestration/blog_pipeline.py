
# src/orchestration/blog_pipeline.py
"""
Blog pipeline (orchestration)

End-to-end flow:
- Ingest: HTML (URL or raw HTML)
- (Optional) Ingest: YouTube comments
- Analyze: comment insights
- Generate: title + blog post

This file is the "control tower" that stitches together the modules created earlier.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

# --- Imports from your project ---
from config.settings import get_settings

from ingestion.html_parser import parse_html, ParsedPage
from analysis.comment_analyzer import CommentAnalyzer
from generation.title_generator import TitleGenerator
from generation.blog_post_generator import BlogPostGenerator, CommentSummary


@dataclass
class PipelineInput:
    # One of url or html must be provided
    url: Optional[str] = None
    html: Optional[str] = None

    # Optional: YouTube ingestion can be added later
    youtube_video_id: Optional[str] = None

    # Optional: if you already have comments as text list
    comments: Optional[List[str]] = None


@dataclass
class PipelineOutput:
    parsed: Dict[str, Any]
    comment_summary: Dict[str, Any]
    title: str
    blog_post: str


class BlogPipeline:
    """
    Orchestrates ingestion -> analysis -> generation.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

        # Components
        self.comment_analyzer = CommentAnalyzer()
        self.title_generator = TitleGenerator()
        self.blog_generator = BlogPostGenerator()

    def run(self, inp: PipelineInput) -> PipelineOutput:
        if not inp.url and not inp.html:
            raise ValueError("Either 'url' or 'html' must be provided.")

        # 1) Ingest HTML
        source = inp.url if inp.url else inp.html
        parsed_page: ParsedPage = parse_html(source)

        # 2) Gather comments (optional)
        #    For now: use inp.comments if provided.
        comments: List[str] = inp.comments or []

        # 3) Analyze comments -> CommentSummary
        #    CommentAnalyzer is expected to return a CommentSummary-like dict or object.
        #    We normalize to CommentSummary for BlogPostGenerator.
        comment_summary = self._analyze_comments(comments)

        # 4) Generate title (use page title + body + insights)
        title = self._generate_title(parsed_page, comment_summary)

        # 5) Generate blog post
        keywords = self._derive_keywords(parsed_page, title)
        blog_post = self.blog_generator.generate(
            title=title,
            keywords=keywords,
            comment_summary=comment_summary,
        )

        return PipelineOutput(
            parsed={
                "title": parsed_page.title,
                "meta_description": parsed_page.meta_description,
                "body_text": parsed_page.body_text,
            },
            comment_summary=asdict(comment_summary),
            title=title,
            blog_post=blog_post,
        )

    def _analyze_comments(self, comments: List[str]) -> CommentSummary:
        if not comments:
            # Safe default: empty insights
            return CommentSummary(
                highlights=[],
                pain_points=[],
                wishes=[],
                tone=None,
            )

        analyzed = self.comment_analyzer.summarize(comments)

        # Normalize to CommentSummary
        # If your CommentAnalyzer already returns CommentSummary, this will just work.
        if isinstance(analyzed, CommentSummary):
            return analyzed

        # If it returns dict-like, map fields safely
        if isinstance(analyzed, dict):
            return CommentSummary(
                highlights=list(analyzed.get("highlights", [])),
                pain_points=list(analyzed.get("pain_points", [])),
                wishes=list(analyzed.get("wishes", [])),
                tone=analyzed.get("tone", None),
            )

        # Otherwise fail loudly (better than silent wrong output)
        raise TypeError(
            "CommentAnalyzer.summarize() must return CommentSummary or dict-like object."
        )

    def _generate_title(self, parsed_page: ParsedPage, comment_summary: CommentSummary) -> str:
        base_title = (parsed_page.title or "").strip()
        if base_title:
            # TitleGenerator should refine/upgrade title
            return self.title_generator.generate(
                base_title=base_title,
                meta_description=parsed_page.meta_description or "",
                highlights=comment_summary.highlights,
                pain_points=comment_summary.pain_points,
                wishes=comment_summary.wishes,
            )

        # If page has no title, generate from body
        return self.title_generator.generate(
            base_title="",
            meta_description=parsed_page.meta_description or "",
            highlights=comment_summary.highlights,
            pain_points=comment_summary.pain_points,
            wishes=comment_summary.wishes,
            body_text=parsed_page.body_text,
        )

    def _derive_keywords(self, parsed_page: ParsedPage, title: str) -> List[str]:
        """
        Very simple keyword derivation.
        Later you can replace with:
        - Naver/Google keyword planner API
        - Trends / SERP scraping
        - Your own keyword DB
        """
        seeds: List[str] = []
        if title:
            seeds.extend(self._tokenize_ko_simple(title))
        if parsed_page.meta_description:
            seeds.extend(self._tokenize_ko_simple(parsed_page.meta_description))
        # De-duplicate while preserving order
        seen = set()
        out: List[str] = []
        for s in seeds:
            s = s.strip()
            if not s or len(s) < 2:
                continue
            if s in seen:
                continue
            seen.add(s)
            out.append(s)
        return out[:12]

    def _tokenize_ko_simple(self, text: str) -> List[str]:
        # Minimal tokenizer: split by spaces and punctuation-ish.
        # Keep it simple to avoid extra dependencies.
        for ch in [",", ".", ":", ";", "!", "?", "(", ")", "[", "]", "{", "}", "\"", "'"]:
            text = text.replace(ch, " ")
        return [t for t in text.split() if t]


def _parse_comments_arg(raw: Optional[str]) -> Optional[List[str]]:
    """
    Accepts:
    - JSON array string: '["a","b"]'
    - newline separated string: "a\nb\nc"
    """
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None

    # Try JSON
    if raw.startswith("["):
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(x) for x in data]
        except Exception:
            pass

    # Fallback: newline split
    return [line.strip() for line in raw.splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run blog pipeline (orchestration).")
    parser.add_argument("--url", type=str, default=None, help="Target URL to ingest")
    parser.add_argument("--html", type=str, default=None, help="Raw HTML string to ingest")
    parser.add_argument(
        "--comments",
        type=str,
        default=None,
        help='Comments input. JSON list (["a","b"]) or newline-separated text.',
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Optional output JSON file path",
    )

    args = parser.parse_args()
    comments = _parse_comments_arg(args.comments)

    pipeline = BlogPipeline()
    result = pipeline.run(
        PipelineInput(
            url=args.url,
            html=args.html,
            comments=comments,
        )
    )

    payload = asdict(result)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"[OK] wrote: {args.out}")
    else:
        # Print readable output
        print("\n=== TITLE ===")
        print(payload["title"])
        print("\n=== BLOG POST ===")
        print(payload["blog_post"])
        print("\n=== META ===")
        print(json.dumps({"parsed": payload["parsed"], "comment_summary": payload["comment_summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
