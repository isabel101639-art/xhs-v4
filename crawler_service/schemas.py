from typing import List

from pydantic import BaseModel, Field


class SyncTarget(BaseModel):
    registration_id: int = 0
    submission_id: int = 0
    topic_id: int = 0
    creator_account_id: int = 0
    profile_url: str = ''
    account_handle: str = ''
    owner_name: str = ''
    owner_phone: str = ''
    registration_ids: List[int] = Field(default_factory=list)
    submission_ids: List[int] = Field(default_factory=list)
    note_url: str = ''
    last_synced_at: str = ''


class AccountPostsRequest(BaseModel):
    targets: List[SyncTarget] = Field(default_factory=list)
    batch_name: str = ''
    source_channel: str = 'Crawler服务'
    current_month_only: bool = True
    date_from: str = ''
    date_to: str = ''
    max_posts_per_account: int = 60


class CreatorAccountRow(BaseModel):
    platform: str = 'xhs'
    owner_name: str = ''
    owner_phone: str = ''
    account_handle: str
    display_name: str = ''
    profile_url: str = ''
    follower_count: int = 0
    source_channel: str = 'crawler_service'
    notes: str = ''


class CreatorPostRow(BaseModel):
    platform: str = 'xhs'
    account_handle: str
    owner_phone: str = ''
    owner_name: str = ''
    profile_url: str = ''
    registration_id: int = 0
    topic_id: int = 0
    submission_id: int = 0
    platform_post_id: str = ''
    title: str
    post_url: str
    publish_time: str = ''
    topic_title: str = ''
    views: int = 0
    exposures: int = 0
    likes: int = 0
    favorites: int = 0
    comments: int = 0
    shares: int = 0
    follower_delta: int = 0
    source_channel: str = 'crawler_service'


class CreatorSnapshotRow(BaseModel):
    platform: str = 'xhs'
    account_handle: str
    owner_phone: str = ''
    owner_name: str = ''
    profile_url: str = ''
    snapshot_date: str
    follower_count: int = 0
    post_count: int = 0
    total_views: int = 0
    total_interactions: int = 0
    source_channel: str = 'crawler_service'


class AccountPostsResponse(BaseModel):
    success: bool = True
    provider: str = 'mock'
    batch_name: str = ''
    source_channel: str = 'Crawler服务'
    accounts: List[CreatorAccountRow] = Field(default_factory=list)
    posts: List[CreatorPostRow] = Field(default_factory=list)
    snapshots: List[CreatorSnapshotRow] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)
