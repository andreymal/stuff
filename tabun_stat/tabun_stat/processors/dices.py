from dataclasses import dataclass

from tabun_stat import types, utils
from tabun_stat.processors.base import BaseProcessor


@dataclass(slots=True)
class DiceStat:
    # Число публикаций с дайсами у этого пользователя
    publications_count: int = 0
    # Число дайсов в этих публикациях
    dices_count: int = 0


class DicesProcessor(BaseProcessor):
    def __init__(self) -> None:
        super().__init__()
        self._dices: dict[int, DiceStat] = {}

    def process_post(self, post: types.Post) -> None:
        self._process(post.author_id, post.body)

    def process_comment(self, comment: types.Comment) -> None:
        self._process(comment.author_id, comment.body)

    def _process(self, author_id: int, body: str) -> None:
        count = body.count('<span class="dice">')
        if count == 0:
            return

        if author_id not in self._dices:
            self._dices[author_id] = DiceStat()
        self._dices[author_id].publications_count += 1
        self._dices[author_id].dices_count += count

    def stop(self) -> None:
        assert self.stat

        with (self.stat.destination / "dices.csv").open("w", encoding="utf-8") as fp:
            fp.write(
                utils.csvline(
                    "ID юзера",
                    "Пользователь",
                    "Сколько публикаций с дайсами",
                    "Сколько раз брошены дайсы",
                )
            )
            info = sorted(
                self._dices.items(),
                key=lambda x: (x[1].publications_count, x[1].dices_count, -x[0]),
                reverse=True,
            )
            for user_id, st in info:
                fp.write(
                    utils.csvline(
                        user_id,
                        self.stat.source.get_username_by_user_id(user_id),
                        st.publications_count,
                        st.dices_count,
                    )
                )

        super().stop()
