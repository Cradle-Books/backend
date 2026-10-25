from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from Azaniah.authentication.models import Account, Profile
from .models import Following
from .serializers import FollowCreateSerializer, FollowingSerializer

User = get_user_model()


def public_username(user):
    profile = (
        Profile.objects.select_related("account")
        .filter(account__Email=user.email)
        .first()
    )
    if profile:
        return profile.Username.strip() or profile.account.Username.strip()
    if user.username and user.username.casefold() != (user.email or "").casefold():
        return user.username
    return ""


def connection_data(relationship, user):
    state = (
        "accepted"
        if relationship.state == Following.FollowStatus.ACCEPTED
        else "pending"
    )
    return {
        "id": relationship.id,
        "user_id": user.id,
        "username": public_username(user),
        "state": state,
    }


class AuthenticatedFollowView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


class FollowView(AuthenticatedFollowView):
    def post(self, request):
        serializer = FollowCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        follower = request.user
        target = serializer.validated_data["following"]
        if follower.pk == target.pk:
            return Response(
                {"message": "You cannot follow yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_profile = Profile.objects.filter(account__Email=target.email).first()
        if target_profile is None:
            return Response(
                {"message": "Profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        initial_state = (
            Following.FollowStatus.PENDING
            if target_profile.privacy == Profile.PrivacySettings.PRIVATE
            else Following.FollowStatus.ACCEPTED
        )
        relationship, created = Following.objects.get_or_create(
            follower=follower,
            following=target,
            defaults={"state": initial_state},
        )

        if not created:
            if relationship.state == Following.FollowStatus.ACCEPTED:
                return Response(
                    {
                        "message": "You already follow this reader.",
                        "data": FollowingSerializer(relationship).data,
                    },
                    status=status.HTTP_200_OK,
                )
            if relationship.state == Following.FollowStatus.PENDING:
                return Response(
                    {
                        "message": "Your follow request is already pending.",
                        "data": FollowingSerializer(relationship).data,
                    },
                    status=status.HTTP_200_OK,
                )
            relationship.state = initial_state
            relationship.save(update_fields=["state"])

        message = (
            "Follow request sent successfully."
            if initial_state == Following.FollowStatus.PENDING
            else "Account followed successfully."
        )
        return Response(
            {"message": message, "data": FollowingSerializer(relationship).data},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class FollowRequestDecisionView(AuthenticatedFollowView):
    decision = None

    def post(self, request, request_id):
        try:
            relationship = Following.objects.get(
                pk=request_id,
                following=request.user,
                state=Following.FollowStatus.PENDING,
            )
        except Following.DoesNotExist:
            return Response(
                {"message": "Pending follow request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        relationship.state = self.decision
        relationship.save(update_fields=["state"])
        message = (
            "Follow request accepted."
            if self.decision == Following.FollowStatus.ACCEPTED
            else "Follow request declined."
        )
        return Response(
            {"message": message, "data": FollowingSerializer(relationship).data},
            status=status.HTTP_200_OK,
        )


class AcceptRequestView(FollowRequestDecisionView):
    decision = Following.FollowStatus.ACCEPTED


class DenyRequestView(FollowRequestDecisionView):
    decision = Following.FollowStatus.DECLINED


class UnfollowView(AuthenticatedFollowView):
    def delete(self, request, following_id):
        deleted, _ = Following.objects.filter(
            pk=following_id,
            follower=request.user,
        ).delete()
        if not deleted:
            return Response(
                {"message": "Follow relationship not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class FollowListView(AuthenticatedFollowView):
    def get(self, request):
        followers = (
            Following.objects.filter(
                following=request.user,
                state=Following.FollowStatus.ACCEPTED,
            )
            .select_related("follower")
            .order_by("-created_at")
        )
        following = (
            Following.objects.filter(
                follower=request.user,
                state=Following.FollowStatus.ACCEPTED,
            )
            .select_related("following")
            .order_by("-created_at")
        )
        outgoing_pending = (
            Following.objects.filter(
                follower=request.user,
                state=Following.FollowStatus.PENDING,
            )
            .select_related("following")
            .order_by("-created_at")
        )
        return Response(
            {
                "followers": [
                    connection_data(relationship, relationship.follower)
                    for relationship in followers
                ],
                "following": [
                    connection_data(relationship, relationship.following)
                    for relationship in following
                ],
                "outgoing_pending": [
                    connection_data(relationship, relationship.following)
                    for relationship in outgoing_pending
                ],
            },
            status=status.HTTP_200_OK,
        )


class PendingListView(AuthenticatedFollowView):
    def get(self, request):
        pending = (
            Following.objects.filter(
                following=request.user,
                state=Following.FollowStatus.PENDING,
            )
            .select_related("follower")
            .order_by("-created_at")
        )
        return Response(
            {
                "pending": [
                    connection_data(relationship, relationship.follower)
                    for relationship in pending
                ]
            },
            status=status.HTTP_200_OK,
        )


class PeopleSearchView(AuthenticatedFollowView):
    def get(self, request):
        username = request.query_params.get("username", "").strip().removeprefix("@")
        if not username:
            return Response(
                {"message": "A username is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        matching_emails = Account.objects.filter(
            Q(Username__iexact=username) | Q(profile__Username__iexact=username)
        ).values_list("Email", flat=True)
        target = (
            User.objects.filter(
                Q(username__iexact=username) | Q(email__in=matching_emails)
            )
            .exclude(pk=request.user.pk)
            .order_by("pk")
            .first()
        )
        if target is None:
            return Response({"results": []}, status=status.HTTP_200_OK)

        profile = Profile.objects.filter(account__Email=target.email).first()
        handle = public_username(target)
        if profile is None or not handle:
            return Response({"results": []}, status=status.HTTP_200_OK)

        relationship = Following.objects.filter(
            follower=request.user,
            following=target,
        ).first()
        follow_status = "none"
        if relationship:
            if relationship.state == Following.FollowStatus.PENDING:
                follow_status = "pending"
            elif relationship.state == Following.FollowStatus.ACCEPTED:
                follow_status = "accepted"

        follows_you = Following.objects.filter(
            follower=target,
            following=request.user,
            state=Following.FollowStatus.ACCEPTED,
        ).exists()
        return Response(
            {
                "results": [
                    {
                        "id": target.pk,
                        "username": handle,
                        "privacy": profile.privacy,
                        "follow_status": follow_status,
                        "follows_you": follows_you,
                    }
                ]
            },
            status=status.HTTP_200_OK,
        )


class PublicProfileView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [JWTAuthentication]

    def get(self, request, username):
        matching_emails = Account.objects.filter(
            Q(Username__iexact=username) | Q(profile__Username__iexact=username)
        ).values_list("Email", flat=True)
        target = (
            User.objects.filter(
                Q(username__iexact=username) | Q(email__in=matching_emails)
            )
            .order_by("pk")
            .first()
        )
        if target is None:
            return Response(
                {"message": "Reader not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        profile = Profile.objects.filter(account__Email=target.email).first()
        handle = public_username(target)
        if profile is None or not handle or handle.casefold() != username.casefold():
            return Response(
                {"message": "Reader not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        follow_status = "none"
        follows_you = False
        if request.user.is_authenticated:
            relationship = Following.objects.filter(
                follower=request.user,
                following=target,
            ).first()
            if relationship:
                if relationship.state == Following.FollowStatus.PENDING:
                    follow_status = "pending"
                elif relationship.state == Following.FollowStatus.ACCEPTED:
                    follow_status = "accepted"
            follows_you = Following.objects.filter(
                follower=target,
                following=request.user,
                state=Following.FollowStatus.ACCEPTED,
            ).exists()

        return Response(
            {
                "id": target.pk,
                "username": handle,
                "privacy": profile.privacy,
                "follow_status": follow_status,
                "follows_you": follows_you,
            },
            status=status.HTTP_200_OK,
        )
