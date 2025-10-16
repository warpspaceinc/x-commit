"""Pattern-based message filtering using .xcommitignore file."""

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class IgnorePatternManager:
    """Manages ignore patterns from .xcommitignore file."""

    def __init__(self, ignore_file_path: Optional[Path] = None):
        """Initialize the ignore pattern manager.

        Args:
            ignore_file_path: Path to .xcommitignore file. If None, uses .xcommitignore in current directory.
        """
        if ignore_file_path is None:
            ignore_file_path = Path(".xcommitignore")

        self.ignore_file_path = ignore_file_path
        self.patterns = []
        self.regex_patterns = []
        self._load_patterns()

        logger.info(f"Loaded {len(self.patterns)} string patterns and {len(self.regex_patterns)} regex patterns from {ignore_file_path}")

    def _load_patterns(self):
        """Load patterns from the ignore file.

        File format:
        - Lines starting with # are comments
        - Empty lines are ignored
        - Lines starting with 'regex:' are treated as regular expressions
        - Other lines are treated as literal strings (case-insensitive substring match)
        """
        if not self.ignore_file_path.exists():
            logger.info(f"Ignore file not found: {self.ignore_file_path}, no patterns loaded")
            return

        try:
            with open(self.ignore_file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue

                    # Check if it's a regex pattern
                    if line.startswith('regex:'):
                        pattern_str = line[6:].strip()  # Remove 'regex:' prefix
                        try:
                            compiled_pattern = re.compile(pattern_str, re.IGNORECASE)
                            self.regex_patterns.append(compiled_pattern)
                            logger.debug(f"Loaded regex pattern from line {line_num}: {pattern_str}")
                        except re.error as e:
                            logger.warning(f"Invalid regex pattern at line {line_num}: {pattern_str} - {e}")
                    else:
                        # Literal string pattern (will be matched case-insensitively)
                        self.patterns.append(line.lower())
                        logger.debug(f"Loaded string pattern from line {line_num}: {line}")

        except Exception as e:
            logger.error(f"Failed to load ignore patterns from {self.ignore_file_path}: {e}")

    def should_ignore(self, message: str) -> tuple[bool, Optional[str]]:
        """Check if a message should be ignored based on loaded patterns.

        Args:
            message: The message text to check

        Returns:
            Tuple of (should_ignore: bool, matched_pattern: Optional[str])
            - should_ignore: True if message matches any pattern
            - matched_pattern: The pattern that matched, or None
        """
        if not message:
            return False, None

        message_lower = message.lower()

        # Check literal string patterns (case-insensitive substring match)
        for pattern in self.patterns:
            if pattern in message_lower:
                logger.debug(f"Message matches string pattern: {pattern}")
                return True, pattern

        # Check regex patterns
        for regex_pattern in self.regex_patterns:
            if regex_pattern.search(message):
                logger.debug(f"Message matches regex pattern: {regex_pattern.pattern}")
                return True, f"regex:{regex_pattern.pattern}"

        return False, None

    def reload(self):
        """Reload patterns from the ignore file.

        Useful if the file has been modified during runtime.
        """
        self.patterns = []
        self.regex_patterns = []
        self._load_patterns()
        logger.info(f"Reloaded patterns from {self.ignore_file_path}")


def should_ignore_message(message: str, ignore_file_path: Optional[Path] = None) -> bool:
    """Convenience function to check if a message should be ignored.

    Args:
        message: The message text to check
        ignore_file_path: Path to .xcommitignore file (optional)

    Returns:
        True if message should be ignored
    """
    manager = IgnorePatternManager(ignore_file_path)
    should_ignore, _ = manager.should_ignore(message)
    return should_ignore
