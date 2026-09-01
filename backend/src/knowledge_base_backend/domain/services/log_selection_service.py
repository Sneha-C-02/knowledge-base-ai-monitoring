import re
from dataclasses import dataclass
from typing import List, Set, Tuple

@dataclass
class SelectedLogContent:
    content: str
    original_line_count: int
    analyzed_line_count: int
    was_reduced: bool

class LogSelectionService:
    """
    Intelligently reduces large log files to fit within LLM analysis limits
    while preserving high-priority diagnostic information:
    1. ERROR / CRITICAL / FATAL lines
    2. Surrounding context lines (pre/post) for errors to preserve stack traces & operational context
    3. Recent tail lines (latest state of the instrument)
    4. WARNING lines with context
    5. Discontinuity markers where sections are omitted
    """

    def __init__(
        self,
        max_lines: int = 600,
        context_lines: int = 2,
        tail_lines: int = 100
    ):
        self.max_lines = max_lines
        self.context_lines = context_lines
        self.tail_lines = tail_lines

        self.severe_regex = re.compile(
            r'(?i)\b(fatal|critical|severe|error|exception|panic|fail(?:ed|ure)?)\b'
        )
        self.warning_regex = re.compile(
            r'(?i)\b(warn|warning)\b'
        )

    def select_log_content(self, raw_content: str) -> SelectedLogContent:
        if not raw_content:
            return SelectedLogContent(content="", original_line_count=0, analyzed_line_count=0, was_reduced=False)

        lines = raw_content.split('\n')
        total_lines = len(lines)
        char_count = len(raw_content)

        # If under max_lines AND under 5000 estimated tokens (~20,000 chars), no reduction needed
        if total_lines <= self.max_lines and (char_count * 0.25) <= 5000:
            return SelectedLogContent(
                content=raw_content,
                original_line_count=total_lines,
                analyzed_line_count=total_lines,
                was_reduced=False
            )

        selected_indices: Set[int] = set()
        severe_indices: List[int] = []
        warning_indices: List[int] = []

        for idx, line in enumerate(lines):
            if self.severe_regex.search(line):
                severe_indices.append(idx)
            elif self.warning_regex.search(line):
                warning_indices.append(idx)

        # 1. Add severe lines and their context windows
        for idx in severe_indices:
            start = max(0, idx - self.context_lines)
            end = min(total_lines, idx + self.context_lines + 1)
            for i in range(start, end):
                selected_indices.add(i)

        # 2. Add tail lines (latest events)
        tail_start = max(0, total_lines - self.tail_lines)
        for i in range(tail_start, total_lines):
            selected_indices.add(i)

        # 3. Add warning lines and context if still under budget
        if len(selected_indices) < self.max_lines:
            for idx in warning_indices:
                start = max(0, idx - 1)
                end = min(total_lines, idx + 2)
                for i in range(start, end):
                    selected_indices.add(i)
                if len(selected_indices) >= self.max_lines:
                    break

        # 4. If over budget because of massive number of errors, prioritize
        if len(selected_indices) > self.max_lines:
            priority_indices: List[Tuple[int, int]] = []
            for idx in selected_indices:
                if idx in severe_indices:
                    priority = 0
                elif idx >= tail_start:
                    priority = 1
                elif any(abs(idx - s) <= 1 for s in severe_indices):
                    priority = 2
                elif idx in warning_indices:
                    priority = 3
                else:
                    priority = 4
                priority_indices.append((priority, idx))

            priority_indices.sort(key=lambda x: (x[0], -x[1]))
            selected_indices = set(idx for _, idx in priority_indices[:self.max_lines])

        # 5. If under budget, include header lines (first 30 lines)
        if len(selected_indices) < self.max_lines:
            head_end = min(30, total_lines)
            for i in range(0, head_end):
                selected_indices.add(i)
                if len(selected_indices) >= self.max_lines:
                    break

        sorted_indices = sorted(list(selected_indices))

        reduced_lines = []
        last_idx = -1
        for idx in sorted_indices:
            if last_idx != -1 and idx > last_idx + 1:
                omitted_count = idx - last_idx - 1
                reduced_lines.append(f"... [{omitted_count} non-critical lines omitted for fast diagnostic analysis] ...")
            reduced_lines.append(lines[idx])
            last_idx = idx

        reduced_content = "\n".join(reduced_lines)
        return SelectedLogContent(
            content=reduced_content,
            original_line_count=total_lines,
            analyzed_line_count=len(sorted_indices),
            was_reduced=True
        )
