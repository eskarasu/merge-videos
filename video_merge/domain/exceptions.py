class VideoMergeError(Exception):
    """Base exception for video merge domain/application errors."""


class InvalidInputError(VideoMergeError):
    """Raised when user input does not satisfy business constraints."""


class JobNotFoundError(VideoMergeError):
    """Raised when a merge job does not exist or is not accessible."""


class FFmpegUnavailableError(VideoMergeError):
    """Raised when FFmpeg is not installed or not discoverable."""


class MergeExecutionError(VideoMergeError):
    """Raised when FFmpeg command execution fails."""


class QueueUnavailableError(VideoMergeError):
    """Raised when job queue infrastructure is not reachable."""
