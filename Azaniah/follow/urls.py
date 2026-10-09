from django.urls import path

from .views import (
    AcceptRequestView,
    DenyRequestView,
    FollowListView,
    FollowView,
    PendingListView,
    PeopleSearchView,
    PublicProfileView,
    UnfollowView,
)

urlpatterns = [
    path("follow/", FollowView.as_view(), name="follow-user"),
    path("follow-requests/", PendingListView.as_view(), name="pending-follow-requests"),
    path(
        "follow-requests/<int:request_id>/accept/",
        AcceptRequestView.as_view(),
        name="accept-follow-request",
    ),
    path(
        "follow-requests/<int:request_id>/deny/",
        DenyRequestView.as_view(),
        name="deny-follow-request",
    ),
    path("following/<int:following_id>/", UnfollowView.as_view(), name="unfollow-user"),
    path("follows/", FollowListView.as_view(), name="follow-list"),
    path("users/", PeopleSearchView.as_view(), name="people-search"),
    path("users/<str:username>/", PublicProfileView.as_view(), name="public-reader-profile"),
]
