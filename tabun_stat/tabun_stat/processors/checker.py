from datetime import datetime

from tabun_stat import types
from tabun_stat.processors.base import BaseProcessor
from tabun_stat.stat import TabunStat


class CheckerProcessor(BaseProcessor):
    def __init__(self) -> None:
        super().__init__()
        self._last_date: datetime | None = None
        self._warned_posts: set[int] = set()

    def start(self, stat: TabunStat) -> None:
        super().start(stat)
        self._last_date = None

    def stop(self, stat: TabunStat) -> None:
        try:
            import resource  # pylint: disable=import-outside-toplevel
        except ImportError:
            pass
        else:
            maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            stat.log(1, f"\nMax RSS: {maxrss / 1024:.1f} MiB")

        super().stop(stat)

    def process_post(self, stat: TabunStat, post: types.Post) -> None:
        if self._last_date is not None:
            if post.created_at < self._last_date:
                stat.log(
                    0,
                    f"WARNING: next post {post.id} {post.created_at} is from past!",
                    f"(expected date after {self._last_date})",
                )
        self._last_date = post.created_at

    def process_comment(self, stat: TabunStat, comment: types.Comment) -> None:
        if self._last_date is not None:
            if comment.created_at < self._last_date:
                stat.log(
                    0,
                    f"WARNING: next comment {comment.id} {comment.created_at} is from past!",
                    f"(expected date after {self._last_date})",
                )
        self._last_date = comment.created_at

        # У комментария может отсутствовать пост или блог — такое может
        # происходить из-за удалённых блогов и других странных поломок.
        # Предупреждаем пользователя об этом
        if comment.post_id is None:
            stat.log(0, f"WARNING: comment {comment.id} has no post")
        elif comment.blog_status is None and comment.post_id not in self._warned_posts:
            stat.log(
                0,
                f"WARNING: comment {comment.id} from post {comment.post_id} has unknown blog {comment.blog_id}",
            )
            self._warned_posts.add(comment.post_id)
