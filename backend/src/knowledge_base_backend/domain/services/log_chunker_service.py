import re
from typing import List

class LogChunkerService:
    """
    Service responsible for intelligent log token estimation, preprocessing, and chunking.
    It splits large logs into optimal sizes for LLM ingestion while preserving logical boundaries
    (e.g., keeping stack traces with their parent error lines).
    """

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of LLM tokens for a given string.
        A common heuristic is 1 token ≈ 4 characters for English text.
        """
        if not text:
            return 0
        return len(text) // 4

    def chunk_log(self, content: str, max_tokens: int) -> List[str]:
        """
        Splits a large log string into smaller chunks, each under the max_tokens limit.
        Attempts to preserve logical groupings like multi-line exceptions.
        """
        if not content.strip():
            return []

        lines = content.split('\n')
        chunks = []
        current_chunk_lines = []
        current_chunk_length = 0
        
        # Max characters roughly equivalent to max_tokens
        max_chars = max_tokens * 4

        # A heuristic for detecting if a line starts a new log record 
        # (e.g., starts with a timestamp or log level). 
        # If it starts with space/tab, it's likely a stack trace or continuation.
        continuation_regex = re.compile(r'^[ \t]+')

        for line in lines:
            line_len = len(line) + 1  # +1 for newline character
            
            # If a single line is absurdly large, we must blindly chop it, 
            # though this is rare in proper logs.
            if line_len > max_chars:
                if current_chunk_lines:
                    chunks.append("\n".join(current_chunk_lines))
                    current_chunk_lines = []
                    current_chunk_length = 0
                
                # Split the massive line exactly by max_chars
                for i in range(0, len(line), max_chars):
                    chunks.append(line[i:i+max_chars])
                continue

            # Check if adding this line exceeds the target size
            if current_chunk_length + line_len > max_chars:
                # If the line is a continuation (like a stack trace), we try to keep it 
                # together with the preceding lines IF we aren't wildly exceeding the budget.
                # However, to be strict on API limits, if we exceed 1.1x the budget, we forcefully cut.
                is_continuation = bool(continuation_regex.match(line))
                if is_continuation and (current_chunk_length + line_len) < (max_chars * 1.1):
                    current_chunk_lines.append(line)
                    current_chunk_length += line_len
                    continue
                else:
                    # Finalize current chunk and start a new one
                    chunks.append("\n".join(current_chunk_lines))
                    current_chunk_lines = [line]
                    current_chunk_length = line_len
            else:
                current_chunk_lines.append(line)
                current_chunk_length += line_len

        # Append any remaining lines
        if current_chunk_lines:
            chunks.append("\n".join(current_chunk_lines))

        return chunks
