from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable

from video_merge.domain.exceptions import FFmpegUnavailableError, MergeExecutionError
from video_merge.domain.interfaces import VideoMerger


class FFmpegVideoMerger(VideoMerger):
    def __init__(self, ffmpeg_binary: str = "ffmpeg") -> None:
        self._ffmpeg_binary = ffmpeg_binary

    def merge(self, clip_paths: Iterable[Path], output_path: Path) -> None:
        if shutil.which(self._ffmpeg_binary) is None:
            raise FFmpegUnavailableError("FFmpeg executable bulunamadi.")

        clip_paths = list(clip_paths)
        if not clip_paths:
            raise MergeExecutionError("Birlesecek video listesi bos.")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        list_file_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".txt",
                delete=False,
                encoding="utf-8",
            ) as list_file:
                list_file_path = Path(list_file.name)
                for clip_path in clip_paths:
                    normalized_path = clip_path.resolve().as_posix().replace("'", r"'\''")
                    list_file.write(f"file '{normalized_path}'\n")

            command = [
                self._ffmpeg_binary,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file_path),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                str(output_path),
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                error_text = result.stderr.strip() or "Bilinmeyen FFmpeg hatasi."
                raise MergeExecutionError(error_text)
        finally:
            if list_file_path and list_file_path.exists():
                list_file_path.unlink(missing_ok=True)
