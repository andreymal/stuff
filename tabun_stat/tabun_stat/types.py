from dataclasses import dataclass
from datetime import date, datetime

# pylint: disable=too-many-instance-attributes


@dataclass(slots=True)
class UsersLimits:
    count: int
    first_id: int | None
    last_id: int | None


@dataclass(slots=True)
class User:
    id: int
    username: str
    skill: float
    rating: float
    registered_at: datetime
    registered_at_local: datetime | None = None  # filled automatically by tabun_stat
    realname: str | None = None
    gender: str | None = None  # "M", "F"
    birthday: date | None = None
    description: str | None = None


@dataclass(slots=True)
class BlogsLimits:
    count: int
    first_id: int | None
    last_id: int | None


@dataclass(slots=True)
class Blog:
    id: int
    slug: str
    name: str
    creator_id: int
    rating: float
    status: int  # 0 - open, 1 - closed, 2 - semiclosed
    description: str
    vote_count: int
    created_at: datetime
    created_at_local: datetime | None = None  # filled automatically by tabun_stat


@dataclass(slots=True)
class PostsLimits:
    count: int
    first_id: int | None
    last_id: int | None
    first_created_at: datetime | None
    last_created_at: datetime | None


@dataclass(slots=True)
class Post:
    id: int
    created_at: datetime
    author_id: int
    blog_id: int | None
    blog_status: int  # 0 - open or personal, 1 - closed, 2 - semiclosed
    title: str
    vote_count: int
    vote_value: int | None
    body: str
    tags: list[str]
    favorites_count: int
    created_at_local: datetime | None = None  # filled automatically by tabun_stat

    comments: list["Comment"] | None = None


@dataclass(slots=True)
class CommentsLimits:
    count: int
    first_id: int | None
    last_id: int | None
    first_created_at: datetime | None
    last_created_at: datetime | None


@dataclass(slots=True)
class Comment:
    id: int
    created_at: datetime
    author_id: int
    post_id: int | None  # Может быть None, например, из-за бага с удалёнными блогами
    blog_id: int | None
    blog_status: int | None  # 0 - открытый или персональный, 1 - закрытый, 2 - полузакрытый, None - блог неизвестен
    parent_id: int | None
    vote_value: int
    body: str
    favorites_count: int
    created_at_local: datetime | None = None  # filled automatically by tabun_stat
