"""
Context Optimizer - R&D Framework (Reduce & Delegate)

Implements intelligent context optimization to reduce token usage by 30-50%
through context compression, relevance filtering, and smart delegation.

R&D Framework:
- REDUCE: Compress context by removing redundancy and irrelevant information
- DELEGATE: Split large contexts across multiple specialized agents

Links Back To: Main Plan → Phase 2 → Task 2.4

Key Features:
- Context size analysis and estimation
- Relevance scoring for context filtering
- Automatic context summarization
- Smart context splitting for delegation
- Token usage tracking and optimization

Performance Targets:
- Context reduction: 30-50% token savings
- Processing overhead: <100ms per optimization
- Relevance accuracy: >90% for important content
"""

import re
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ContextAnalysis:
    """
    Analysis results for a context block.

    Attributes:
        estimated_tokens: Estimated token count
        sections: List of identified sections
        redundancy_score: Redundancy score (0-1, higher = more redundant)
        complexity_score: Complexity score (1-10)
        key_concepts: Important concepts/keywords
        suggested_reduction: Estimated tokens after optimization
    """
    estimated_tokens: int
    sections: List[Dict[str, Any]] = field(default_factory=list)
    redundancy_score: float = 0.0
    complexity_score: int = 5
    key_concepts: Set[str] = field(default_factory=set)
    suggested_reduction: int = 0


@dataclass
class OptimizationResult:
    """
    Result of context optimization.

    Attributes:
        original_tokens: Original token count
        optimized_tokens: Optimized token count
        savings_tokens: Tokens saved
        savings_percent: Percentage saved
        optimized_context: Optimized context string
        optimization_methods: Methods applied
        metadata: Additional metadata
    """
    original_tokens: int
    optimized_tokens: int
    savings_tokens: int
    savings_percent: float
    optimized_context: str
    optimization_methods: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextOptimizer:
    """
    Optimizes context for agent invocations to reduce token usage.

    Implements R&D (Reduce & Delegate) framework for intelligent
    context management.
    """

    def __init__(self):
        """Initialize context optimizer."""
        # Token estimation (rough approximation)
        self.chars_per_token = 4  # Average characters per token

        # Relevance keywords (domain-specific, can be configured)
        self.relevance_keywords = {
            # Code-related
            "function", "class", "method", "import", "export", "async", "await",
            "error", "exception", "bug", "fix", "refactor", "test",
            # Architecture-related
            "architecture", "design", "pattern", "component", "module", "service",
            "api", "endpoint", "database", "schema",
            # Project-related
            "task", "feature", "requirement", "spec", "documentation",
            # Performance-related
            "performance", "optimization", "latency", "throughput", "memory",
            # Security-related
            "security", "authentication", "authorization", "validation", "sanitize"
        }

        # Statistics
        self.stats = {
            "optimizations_performed": 0,
            "total_tokens_saved": 0,
            "total_original_tokens": 0,
            "optimization_times": []
        }

    def analyze_context(self, context: str) -> ContextAnalysis:
        """
        Analyze context to understand structure and identify optimization opportunities.

        Args:
            context: Context string to analyze

        Returns:
            ContextAnalysis with detailed metrics

        Example:
            >>> optimizer = ContextOptimizer()
            >>> analysis = optimizer.analyze_context(long_context)
            >>> print(f"Estimated tokens: {analysis.estimated_tokens}")
            >>> print(f"Redundancy score: {analysis.redundancy_score:.2f}")
        """
        estimated_tokens = self._estimate_tokens(context)

        # Identify sections (code blocks, prose, lists, etc.)
        sections = self._identify_sections(context)

        # Calculate redundancy score
        redundancy_score = self._calculate_redundancy(context)

        # Extract key concepts
        key_concepts = self._extract_key_concepts(context)

        # Estimate potential reduction
        suggested_reduction = self._estimate_reduction(
            estimated_tokens,
            redundancy_score,
            len(sections)
        )

        return ContextAnalysis(
            estimated_tokens=estimated_tokens,
            sections=sections,
            redundancy_score=redundancy_score,
            complexity_score=self._calculate_complexity(context),
            key_concepts=key_concepts,
            suggested_reduction=suggested_reduction
        )

    def optimize_context(
        self,
        context: str,
        target_reduction: float = 0.3,
        preserve_code: bool = True
    ) -> OptimizationResult:
        """
        Optimize context to reduce token usage.

        Args:
            context: Original context string
            target_reduction: Target reduction ratio (0.3 = 30% reduction)
            preserve_code: If True, preserve code blocks verbatim

        Returns:
            OptimizationResult with optimized context and metrics

        Example:
            >>> optimizer = ContextOptimizer()
            >>> result = optimizer.optimize_context(large_context, target_reduction=0.4)
            >>> print(f"Saved {result.savings_percent:.1f}%")
            >>> print(f"Optimized context: {result.optimized_context[:100]}...")
        """
        start_time = datetime.utcnow()

        # Analyze context
        analysis = self.analyze_context(context)
        original_tokens = analysis.estimated_tokens

        # Apply optimization methods
        optimized = context
        methods_applied = []

        # Method 1: Remove excessive whitespace
        if self._should_apply_whitespace_optimization(context):
            optimized = self._remove_excessive_whitespace(optimized)
            methods_applied.append("whitespace_reduction")

        # Method 2: Remove redundant sections
        if analysis.redundancy_score > 0.3:
            optimized = self._remove_redundant_sections(optimized, preserve_code)
            methods_applied.append("redundancy_removal")

        # Method 3: Summarize verbose sections
        if len(optimized) > 5000 and not preserve_code:
            optimized = self._summarize_verbose_sections(optimized, analysis)
            methods_applied.append("verbose_summarization")

        # Method 4: Filter low-relevance content
        optimized = self._filter_low_relevance(optimized, analysis.key_concepts)
        methods_applied.append("relevance_filtering")

        # Calculate final metrics
        optimized_tokens = self._estimate_tokens(optimized)
        savings_tokens = original_tokens - optimized_tokens
        savings_percent = (savings_tokens / original_tokens * 100) if original_tokens > 0 else 0.0

        # Update statistics
        self.stats["optimizations_performed"] += 1
        self.stats["total_tokens_saved"] += savings_tokens
        self.stats["total_original_tokens"] += original_tokens

        optimization_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        self.stats["optimization_times"].append(optimization_time)

        logger.info(
            f"Context optimized: {original_tokens} → {optimized_tokens} tokens "
            f"({savings_percent:.1f}% reduction) in {optimization_time:.1f}ms"
        )

        return OptimizationResult(
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            savings_tokens=savings_tokens,
            savings_percent=savings_percent,
            optimized_context=optimized,
            optimization_methods=methods_applied,
            metadata={
                "analysis": analysis,
                "optimization_time_ms": optimization_time
            }
        )

    def split_context_for_delegation(
        self,
        context: str,
        max_tokens_per_chunk: int = 50000
    ) -> List[Dict[str, Any]]:
        """
        Split large context into smaller chunks for delegation to multiple agents.

        Args:
            context: Large context to split
            max_tokens_per_chunk: Maximum tokens per chunk

        Returns:
            List of context chunks with metadata

        Example:
            >>> optimizer = ContextOptimizer()
            >>> chunks = optimizer.split_context_for_delegation(huge_context)
            >>> for i, chunk in enumerate(chunks):
            ...     print(f"Chunk {i}: {chunk['estimated_tokens']} tokens")
        """
        analysis = self.analyze_context(context)

        if analysis.estimated_tokens <= max_tokens_per_chunk:
            # No need to split
            return [{
                "content": context,
                "estimated_tokens": analysis.estimated_tokens,
                "chunk_index": 0,
                "total_chunks": 1,
                "key_concepts": list(analysis.key_concepts)
            }]

        # Split by sections first
        sections = analysis.sections

        chunks = []
        current_chunk = []
        current_tokens = 0

        for section in sections:
            section_tokens = self._estimate_tokens(section["content"])

            if current_tokens + section_tokens > max_tokens_per_chunk and current_chunk:
                # Finalize current chunk
                chunk_content = "\n\n".join(s["content"] for s in current_chunk)
                chunks.append({
                    "content": chunk_content,
                    "estimated_tokens": current_tokens,
                    "chunk_index": len(chunks),
                    "sections": [s["type"] for s in current_chunk]
                })

                # Start new chunk
                current_chunk = [section]
                current_tokens = section_tokens
            else:
                current_chunk.append(section)
                current_tokens += section_tokens

        # Add final chunk
        if current_chunk:
            chunk_content = "\n\n".join(s["content"] for s in current_chunk)
            chunks.append({
                "content": chunk_content,
                "estimated_tokens": current_tokens,
                "chunk_index": len(chunks),
                "sections": [s["type"] for s in current_chunk]
            })

        # Add metadata
        for chunk in chunks:
            chunk["total_chunks"] = len(chunks)
            chunk["key_concepts"] = list(self._extract_key_concepts(chunk["content"]))

        logger.info(
            f"Split context: {analysis.estimated_tokens} tokens → "
            f"{len(chunks)} chunks (max {max_tokens_per_chunk} tokens/chunk)"
        )

        return chunks

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count from text.

        Uses rough approximation of 4 characters per token.
        For production, use tiktoken or similar.
        """
        return len(text) // self.chars_per_token

    def _identify_sections(self, context: str) -> List[Dict[str, Any]]:
        """
        Identify different sections in context (code blocks, prose, lists, etc.).
        """
        sections = []

        # Split by double newlines (paragraph boundaries)
        paragraphs = re.split(r'\n\n+', context)

        for para in paragraphs:
            if not para.strip():
                continue

            # Determine section type
            section_type = "prose"
            if re.match(r'^```', para):
                section_type = "code_block"
            elif re.match(r'^\s*[-*]\s+', para, re.MULTILINE):
                section_type = "list"
            elif re.match(r'^\s*\d+\.\s+', para, re.MULTILINE):
                section_type = "numbered_list"
            elif re.match(r'^#+\s+', para):
                section_type = "heading"

            sections.append({
                "type": section_type,
                "content": para,
                "length": len(para)
            })

        return sections

    def _calculate_redundancy(self, context: str) -> float:
        """
        Calculate redundancy score (0-1, higher = more redundant).

        Looks for repeated phrases, duplicate sections, etc.
        """
        # Simple approach: Look for repeated n-grams
        words = context.lower().split()

        if len(words) < 10:
            return 0.0

        # Count 3-grams
        trigrams = {}
        for i in range(len(words) - 2):
            trigram = ' '.join(words[i:i+3])
            trigrams[trigram] = trigrams.get(trigram, 0) + 1

        # Calculate redundancy (repeated trigrams / total trigrams)
        total_trigrams = len(words) - 2
        repeated_trigrams = sum(count - 1 for count in trigrams.values() if count > 1)

        redundancy = repeated_trigrams / total_trigrams if total_trigrams > 0 else 0.0

        return min(redundancy, 1.0)

    def _extract_key_concepts(self, context: str) -> Set[str]:
        """
        Extract key concepts/keywords from context.
        """
        words = set(re.findall(r'\b\w+\b', context.lower()))

        # Find relevance keywords present in context
        key_concepts = words & self.relevance_keywords

        # Also add capitalized words (likely important names)
        capitalized = set(re.findall(r'\b[A-Z][a-zA-Z]+\b', context))

        return key_concepts | capitalized

    def _calculate_complexity(self, context: str) -> int:
        """
        Calculate complexity score (1-10).

        Based on sentence length, vocabulary diversity, nesting, etc.
        """
        # Simple heuristic
        words = context.split()
        unique_words = set(words)

        if not words:
            return 1

        # Vocabulary diversity
        diversity = len(unique_words) / len(words)

        # Average word length
        avg_word_length = sum(len(w) for w in words) / len(words)

        # Combine factors
        complexity = int(diversity * 5 + avg_word_length * 0.5)

        return min(max(complexity, 1), 10)

    def _estimate_reduction(
        self,
        tokens: int,
        redundancy: float,
        section_count: int
    ) -> int:
        """
        Estimate potential token reduction.
        """
        # Base reduction from redundancy removal
        redundancy_reduction = tokens * redundancy * 0.5

        # Additional reduction from summarization if many sections
        summarization_reduction = 0
        if section_count > 10:
            summarization_reduction = tokens * 0.2

        total_reduction = redundancy_reduction + summarization_reduction

        return int(min(total_reduction, tokens * 0.5))  # Cap at 50% reduction

    def _should_apply_whitespace_optimization(self, context: str) -> bool:
        """Check if whitespace optimization would be beneficial."""
        # Count excessive whitespace
        excessive_ws = len(re.findall(r'\s{3,}', context))
        return excessive_ws > 10

    def _remove_excessive_whitespace(self, context: str) -> str:
        """Remove excessive whitespace while preserving structure."""
        # Collapse multiple spaces to single space
        optimized = re.sub(r' {2,}', ' ', context)

        # Collapse multiple newlines to max 2
        optimized = re.sub(r'\n{3,}', '\n\n', optimized)

        return optimized

    def _remove_redundant_sections(self, context: str, preserve_code: bool) -> str:
        """
        Remove redundant sections from context.

        Args:
            context: Context to optimize
            preserve_code: If True, don't remove code blocks

        Returns:
            Optimized context
        """
        sections = self._identify_sections(context)

        # Track unique content
        seen_content = set()
        unique_sections = []

        for section in sections:
            # Preserve code blocks if requested
            if preserve_code and section["type"] == "code_block":
                unique_sections.append(section)
                continue

            # Create a normalized version for comparison
            normalized = re.sub(r'\s+', ' ', section["content"].lower()).strip()

            if normalized not in seen_content:
                seen_content.add(normalized)
                unique_sections.append(section)

        # Reconstruct context
        return "\n\n".join(s["content"] for s in unique_sections)

    def _summarize_verbose_sections(
        self,
        context: str,
        analysis: ContextAnalysis
    ) -> str:
        """
        Summarize verbose sections that are not critical.

        This is a simple heuristic-based approach.
        For production, consider using a summarization model.
        """
        sections = analysis.sections

        optimized_sections = []

        for section in sections:
            # Skip short sections
            if len(section["content"]) < 500:
                optimized_sections.append(section["content"])
                continue

            # Check if section contains key concepts
            section_concepts = self._extract_key_concepts(section["content"])
            has_key_concepts = bool(section_concepts & analysis.key_concepts)

            if has_key_concepts:
                # Preserve important sections
                optimized_sections.append(section["content"])
            else:
                # Summarize: Keep first and last sentences
                sentences = re.split(r'[.!?]+', section["content"])
                if len(sentences) > 2:
                    summary = f"{sentences[0]}. [...] {sentences[-1]}"
                    optimized_sections.append(summary)
                else:
                    optimized_sections.append(section["content"])

        return "\n\n".join(optimized_sections)

    def _filter_low_relevance(
        self,
        context: str,
        key_concepts: Set[str]
    ) -> str:
        """
        Filter out low-relevance content based on key concepts.

        Keeps paragraphs that contain key concepts.
        """
        paragraphs = re.split(r'\n\n+', context)

        relevant_paragraphs = []

        for para in paragraphs:
            # Always keep code blocks and headings
            if re.match(r'^```', para) or re.match(r'^#+\s+', para):
                relevant_paragraphs.append(para)
                continue

            # Check for key concepts
            para_words = set(re.findall(r'\b\w+\b', para.lower()))
            has_key_concepts = bool(para_words & key_concepts)

            # Keep if it has key concepts or is short (likely important)
            if has_key_concepts or len(para) < 200:
                relevant_paragraphs.append(para)

        return "\n\n".join(relevant_paragraphs)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get optimization statistics.

        Returns:
            Statistics dictionary with:
                - optimizations_performed
                - total_tokens_saved
                - total_original_tokens
                - avg_savings_percent
                - avg_optimization_time_ms
        """
        total_optimized = self.stats["total_original_tokens"]
        total_saved = self.stats["total_tokens_saved"]

        avg_savings_percent = (
            (total_saved / total_optimized * 100) if total_optimized > 0 else 0.0
        )

        avg_optimization_time = (
            sum(self.stats["optimization_times"]) / len(self.stats["optimization_times"])
            if self.stats["optimization_times"] else 0.0
        )

        return {
            **self.stats,
            "avg_savings_percent": avg_savings_percent,
            "avg_optimization_time_ms": avg_optimization_time
        }


# Global optimizer instance
_global_optimizer: Optional[ContextOptimizer] = None


def get_context_optimizer() -> Optional[ContextOptimizer]:
    """Get the global context optimizer instance."""
    return _global_optimizer


def initialize_context_optimizer() -> ContextOptimizer:
    """
    Initialize the global context optimizer.

    Returns:
        ContextOptimizer instance
    """
    global _global_optimizer

    if _global_optimizer is not None:
        logger.warning("Context optimizer already initialized")
        return _global_optimizer

    _global_optimizer = ContextOptimizer()

    logger.info("Context optimizer initialized")

    return _global_optimizer


def shutdown_context_optimizer() -> None:
    """Shutdown the global context optimizer."""
    global _global_optimizer
    _global_optimizer = None
    logger.info("Context optimizer shutdown complete")
