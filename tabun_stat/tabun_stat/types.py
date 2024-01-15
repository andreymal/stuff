from datetime import date, datetime
from dataclasses import dataclass
from typing import List, Optional


# pylint: disable=too-many-instance-attributes


@dataclass
class UsersLimits:
    count: int
    first_id: Optional[int]
    last_id: Optional[int]


@dataclass
class User:
    id: int
    username: str
    skill: float
    rating: float
    registered_at: datetime
    registered_at_local: Optional[datetime] = None  # filled automatically by tabun_stat
    realname: Optional[str] = None
    gender: Optional[str] = None  # 'M', 'F'
    birthday: Optional[date] = None
    description: Optional[str] = None


@dataclass
class BlogsLimits:
    count: int
    first_id: Optional[int]
    last_id: Optional[int]


@dataclass
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
    deleted: bool = False
    created_at_local: Optional[datetime] = None  # filled automatically by tabun_stat


@dataclass
class PostsLimits:
    count: int
    first_id: Optional[int]
    last_id: Optional[int]
    first_created_at: Optional[datetime]
    last_created_at: Optional[datetime]


@dataclass
class Post:
    id: int
    created_at: datetime
    author_id: int
    blog_id: Optional[int]
    blog_status: int  # 0 - open or personal, 1 - closed, 2 - semiclosed
    title: str
    vote_count: int
    vote_value: Optional[int]
    body: str
    favorites_count: int
    deleted: bool = False
    draft: bool = False
    created_at_local: Optional[datetime] = None  # filled automatically by tabun_stat

    comments: Optional[List['Comment']] = None


@dataclass
class CommentsLimits:
    count: int
    first_id: Optional[int]
    last_id: Optional[int]
    first_created_at: Optional[datetime]
    last_created_at: Optional[datetime]


@dataclass
class Comment:
    id: int
    created_at: datetime
    author_id: int
    post_id: Optional[int]
    parent_id: Optional[int]
    vote_value: int
    body: str
    favorites_count: int
    deleted: bool = False
    created_at_local: Optional[datetime] = None  # filled automatically by tabun_stat
