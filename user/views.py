from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated

from django.http import Http404
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

import requests
import json

from .models import (
    PortalUserMapping, UserCategoryGroupAssignment, Role, UserRole, UserPortalAssignment
)
from .serializers import (
    PortalCheckResultSerializer, UserRegistrationSerializer, PortalUserMappingListSerializer, CustomTokenObtainPairSerializer,
    UserAssignmentCreateSerializer, UserAssignmentListSerializer, PortalUserMappingSerializer, UserSerializer, UserWithPortalsSerializer,
    UserAssignmentRemoveSerializer, UserPortalAssignmentSerializer
)
from .utils import (
    map_user_to_portals
)
from app.models import (
    Portal
)
from app.serializers import (
    PortalSafeSerializer
)
from app.utils import success_response, error_response, get_portals_from_assignment
from app.pagination import PaginationMixin


User = get_user_model()


class UserRegistrationAPIView(APIView):
    """
    POST /api/register/
    {
        "username": "vasista",
        "email": "vasista@example.com",
        "password": "strongpassword123"
    }
    """

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(error_response(serializer.errors), status=status.HTTP_400_BAD_REQUEST)

        # Create user
        user = serializer.save()

        # Assign default role = USER
        try:
            default_role, _ = Role.objects.get_or_create(name="user")
            UserRole.objects.create(user=user, role=default_role)
        except Exception as e:
            return Response(
                error_response(f"User created but role assignment failed: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Map across portals
        mappings = map_user_to_portals(user.id, user.username)

        response_data = {
            "user": serializer.data,
            "role": "user",
            "portal_mappings": mappings
        }

        return Response(
            success_response(response_data, "User registered with USER role and portal mappings created"),
            status=status.HTTP_201_CREATED
        )


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            return Response(
                success_response(serializer.validated_data, "Login successful"),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(str(e)),
                status=status.HTTP_401_UNAUTHORIZED
            )
            
            
class CheckUsernameAcrossPortalsAPIView(APIView, PaginationMixin):
    """
    GET /api/user-portal/check-username/?username=<username>
    """

    def get(self, request):
        username = request.query_params.get("username")
        if not username:
            return Response(
                error_response("Username is required"),
                status=status.HTTP_400_BAD_REQUEST,
            )

        results = []
        not_found_portals = []

        for portal in Portal.objects.all():
            try:
                url = f"{portal.base_url}/api/check-username/"
                r = requests.get(url, params={"username": username}, timeout=60)

                if r.status_code == 200 and r.json().get("status"):
                    user_data = r.json().get("data", {})
                    results.append({
                        "portal": portal.name,
                        "found": True,
                        "user_id": user_data.get("id"),
                        "username": user_data.get("username"),
                    })
                else:
                    results.append({
                        "portal": portal.name,
                        "found": False,
                        "message": r.json().get("message", "User not found"),
                    })
                    not_found_portals.append(portal.name)

            except Exception as e:
                results.append({
                    "portal": portal.name,
                    "found": False,
                    "message": str(e),
                })
                not_found_portals.append(portal.name)

        # Decide final message
        if not not_found_portals:
            final_message = "User found in all portals"
        else:
            final_message = f"User not found in these portals: {', '.join(not_found_portals)}"

        # Serialize and paginate
        serializer = PortalCheckResultSerializer(results, many=True)
        page = self.paginate_queryset(serializer.data, request)
        if page is not None:
            return self.get_paginated_response(page, final_message)

        # If pagination not applied, return full results
        return Response(
            success_response(serializer.data, final_message),
            status=status.HTTP_200_OK,
        )


class PortalUserMappingCreateAPIView(APIView):
    """
    POST /api/user-portal/mappings/
    """

    def post(self, request):
        user_id = request.data.get("user_id")
        username = request.data.get("username")

        if not user_id or not username:
            return Response(
                error_response("user_id and username are required"),
                status=status.HTTP_400_BAD_REQUEST,
            )

        results = map_user_to_portals(user_id, username)

        return Response(
            success_response(results, "User portal mappings processed"),
            status=status.HTTP_201_CREATED,
        )


class UserPortalMappingsListAPIView(APIView, PaginationMixin):
    """
    GET /api/user-portal/mappings/?username=<username>&page=1&page_size=10
    """

    def get(self, request):
        username = request.query_params.get("username")
        if not username:
            return Response(error_response("Username is required"), status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, username=username)

        queryset = PortalUserMapping.objects.filter(user=user).order_by("id")
        page = self.paginate_queryset(queryset, request)
        serializer = PortalUserMappingListSerializer(page, many=True)

        return self.get_paginated_response(serializer.data, message="Portal mappings fetched successfully")


class UserAssignmentCreateAPIView(APIView):
    """
    POST /api/user-assignments/
    Assign multiple groups OR multiple master categories to a user.
    """

    def post(self, request):
        try:
            serializer = UserAssignmentCreateSerializer(data=request.data)
            if serializer.is_valid():
                assignments = serializer.save()
                data = UserAssignmentListSerializer(assignments, many=True).data
                return Response(success_response(
                    data,
                    "Assignments created successfully"
                ), status=status.HTTP_201_CREATED)
            return Response(error_response(serializer.errors), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserAssignmentListByUserAPIView(APIView, PaginationMixin):
    """
    GET /api/user-assignments/{username}/
    List assignments for a particular user
    """
    def get(self, request, username):
        try:
            user = get_object_or_404(User, username=username)
            queryset = UserCategoryGroupAssignment.objects.filter(user=user).order_by("-created_at")
            page = self.paginate_queryset(queryset, request)
            serializer = UserAssignmentListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data, message=f"Assignments for user {username}")
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserAssignmentListAPIView(APIView, PaginationMixin):
    """
    GET /api/user-assignments/
    List all assignments (admin view, with pagination & filters)
    Filters: ?group=1, ?master_category=2, ?username=john
    """
    def get(self, request):
        try:
            queryset = UserCategoryGroupAssignment.objects.all().order_by("-created_at")

            group = request.query_params.get("group")
            master_category = request.query_params.get("master_category")
            username = request.query_params.get("username")

            if group:
                queryset = queryset.filter(group_id=group)
            if master_category:
                queryset = queryset.filter(master_category_id=master_category)
            if username:
                queryset = queryset.filter(user__username=username)

            page = self.paginate_queryset(queryset, request)
            serializer = UserAssignmentListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data, message="All user assignments fetched successfully")
        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PortalUserMappingManualAPIView(APIView):
    """
    POST /api/portal-user-mapping/
    Create a mapping between a Recon user and a portal.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data.copy()

            serializer = PortalUserMappingSerializer(data=data)
            if serializer.is_valid():
                mapping = serializer.save()
                return Response(
                    success_response(
                        PortalUserMappingSerializer(mapping).data,
                        "Portal user mapping created successfully"
                    ),
                    status=status.HTTP_201_CREATED
                )
            return Response(error_response(serializer.errors), status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PortalUserMappingUpdateAPIView(APIView):
    """
    PUT /api/portal-user-mapping/{id}/
    Update portal user mapping (status, portal_user_id, username, notes).
    Only the owner can update their mapping.
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        try:
            mapping = get_object_or_404(PortalUserMapping, pk=pk)

            serializer = PortalUserMappingSerializer(mapping, data=request.data, partial=True)
            if serializer.is_valid():
                mapping = serializer.save()
                return Response(
                    success_response(
                        PortalUserMappingSerializer(mapping).data,
                        "Portal user mapping updated successfully"
                    ),
                    status=status.HTTP_200_OK
                )
            return Response(error_response(serializer.errors), status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserListAPIView(APIView, PaginationMixin):
    """
    GET /api/users/?search=<username>&page=1&page_size=10
    Returns paginated users with optional username search filter.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            search = request.query_params.get("search", "").strip()
            users = User.objects.all().order_by("-date_joined")

            if search:
                users = users.filter(Q(username__icontains=search))

            paginated_qs = self.paginate_queryset(users, request, view=self)
            serializer = UserSerializer(paginated_qs, many=True)

            return self.get_paginated_response(
                serializer.data,
                message="User list fetched successfully"
            )

        except Exception as e:
            return Response(
                {"status": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class UserAssignedPortalsView(APIView, PaginationMixin):
    """
    GET /api/user/assigned-portals/
    Returns all unique portals assigned to the authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            assignments = UserCategoryGroupAssignment.objects.filter(user=user)

            if not assignments.exists():
                return Response(
                    error_response("No assignments found for this user."),
                    status=status.HTTP_404_NOT_FOUND
                )

            # Collect unique portals
            portal_set = {}
            for assignment in assignments:
                for portal, portal_category in get_portals_from_assignment(assignment):
                    portal_set[portal.id] = portal  # dict ensures uniqueness

            unique_portals = list(portal_set.values())

            # Apply pagination
            page = self.paginate_queryset(unique_portals, request, view=self)
            if page is not None:
                serializer = PortalSafeSerializer(page, many=True)
                return self.get_paginated_response(serializer.data, message="Assigned portals fetched")

            # If pagination not applied
            serializer = PortalSafeSerializer(unique_portals, many=True)
            return Response(
                success_response(serializer.data, "Assigned portals fetched"),
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                error_response(str(e)),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UnassignedUsersAPIView(APIView, PaginationMixin):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            # Users without assignments
            unassigned_users = User.objects.exclude(
                id__in=UserCategoryGroupAssignment.objects.values_list("user_id", flat=True)
            )
            paginated_qs = self.paginate_queryset(unassigned_users, request, view=self)
            serializer = UserSerializer(paginated_qs, many=True)
            return self.get_paginated_response(serializer.data, message="All un assigned users fetched successfully")

        except Exception as e:
            return Response(
                error_response(str(e)),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserDetailsListAPIView(APIView, PaginationMixin):
    """
    GET /api/users/
    Lists all users (no role filter) with their assigned portals, categories, and total posts.
    Supports optional search by username (?search=xyz).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            search_query = request.query_params.get("search", "").strip()

            users = User.objects.all().order_by("-date_joined")

            if search_query:
                users = users.filter(username__icontains=search_query)

            paginated_qs = self.paginate_queryset(users, request, view=self)
            serializer = UserWithPortalsSerializer(paginated_qs, many=True)

            return self.get_paginated_response(
                serializer.data,
                message="Users fetched successfully"
            )

        except Exception as e:
            return Response(
                error_response(str(e)),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserAssignmentRemoveAPIView(APIView):
    """
    DELETE /api/user-assignments/remove/
    Example Payload:
    {
        "user_id": 5,
        "master_category_id": 2
    }
    OR
    {
        "user_id": 5,
        "group_id": 3
    }
    """

    def delete(self, request):
        try:
            serializer = UserAssignmentRemoveSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(error_response(serializer.errors), status=status.HTTP_400_BAD_REQUEST)

            user_id = serializer.validated_data["user_id"]
            master_category_id = serializer.validated_data.get("master_category_id")
            group_id = serializer.validated_data.get("group_id")

            qs = UserCategoryGroupAssignment.objects.filter(user_id=user_id)
            if master_category_id:
                qs = qs.filter(master_category_id=master_category_id)
            if group_id:
                qs = qs.filter(group_id=group_id)

            if not qs.exists():
                return Response(
                    error_response("No matching assignment found."),
                    status=status.HTTP_404_NOT_FOUND,
                )

            deleted_count = qs.delete()[0]
            return Response(
                success_response({"deleted_count": deleted_count}, "Assignment(s) removed successfully."),
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(error_response(str(e)), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MyAssignmentListAPIView(APIView, PaginationMixin):
    """
    GET /api/user-assignments/me/
    List assignments for the currently authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user

            queryset = (
                UserCategoryGroupAssignment.objects
                .filter(user=user)
                .order_by("-created_at")
            )

            page = self.paginate_queryset(queryset, request)
            serializer = UserAssignmentListSerializer(page, many=True)

            return self.get_paginated_response(
                serializer.data,
                message=f"Assignments for user {user.username}"
            )

        except Http404 as e:
            return Response(
                error_response(str(e)),
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response(
                error_response(e.detail),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                error_response(str(e)),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AllUsersAPIView(APIView, PaginationMixin):
    """
    GET /api/users/all/?search=john&page=1&page_size=10
    Returns all users in the system (no exclusions), paginated.
    Supports optional search by username, email, or full name.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            search = request.query_params.get("search")

            queryset = User.objects.all().order_by("-date_joined")

            # Optional search filter
            if search:
                queryset = queryset.filter(
                    Q(username__icontains=search)
                    | Q(email__icontains=search)
                    | Q(first_name__icontains=search)
                    | Q(last_name__icontains=search)
                ).distinct()

            paginated_qs = self.paginate_queryset(queryset, request, view=self)
            serializer = UserSerializer(paginated_qs, many=True)

            return self.get_paginated_response(
                serializer.data,
                message="All users fetched successfully"
            )

        except ValidationError as e:
            return Response(
                error_response(e.detail),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                error_response(str(e)),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AssignPortalToUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user_id = request.data.get("user_id")
            portal_ids = request.data.get("portal_ids")  # LIST expected

            if not user_id:
                return Response(error_response("user_id is required"), status=400)

            if not portal_ids:
                return Response(error_response("portal_ids list is required"), status=400)

            # Convert string → list
            if isinstance(portal_ids, str):
                try:
                    portal_ids = json.loads(portal_ids)
                except:
                    return Response(error_response("portal_ids must be a list"), status=400)

            if not isinstance(portal_ids, list):
                return Response(error_response("portal_ids must be a list"), status=400)

            user = get_object_or_404(User, id=user_id)

            success_list = []
            failed_list = []

            for pid in portal_ids:
                try:
                    portal = Portal.objects.get(id=pid)

                    # Check duplicate
                    if UserPortalAssignment.objects.filter(user=user, portal=portal).exists():
                        failed_list.append({
                            "portal_id": pid,
                            "reason": "Already assigned"
                        })
                        continue

                    # Create assignment
                    assignment = UserPortalAssignment.objects.create(
                        user=user,
                        portal=portal
                    )

                    success_list.append(UserPortalAssignmentSerializer(assignment).data)

                except Portal.DoesNotExist:
                    failed_list.append({
                        "portal_id": pid,
                        "reason": "Portal not found"
                    })

            return Response(
                success_response(
                    {
                        "assigned": success_list,
                        "failed": failed_list
                    },
                    "Portal assignment process completed"
                ),
                status=200
            )

        except Exception as e:
            return Response(error_response(str(e)), status=500)
        
        
class RemovePortalFromUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        try:
            user_id = request.data.get("user_id")
            portal_id = request.data.get("portal_id")

            if not portal_id:
                return Response(error_response("portal_id is required"), status=400)
            
            if not user_id:
                return Response(error_response("user_id is required"), status=400)
            
            assignment = UserPortalAssignment.objects.filter(
                user_id=user_id, portal_id=portal_id
            ).first()

            if not assignment:
                return Response(error_response("Portal not assigned to this user"), status=404)

            assignment.delete()

            return Response(
                success_response({}, "Portal removed from user"),
                status=200
            )

        except Exception as e:
            return Response(error_response(str(e)), status=500)
        

class ListUserPortalsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)

            assignments = UserPortalAssignment.objects.filter(user=user).select_related("portal")

            data = [
                {
                    "assignment_id": a.id,
                    "portal_id": a.portal.id,
                    "portal_name": a.portal.name,
                    "domain_url": a.portal.domain_url,
                    "assigned_at": a.created_at,
                }
                for a in assignments
            ]

            return Response(success_response(data, "User portals fetched successfully"), status=200)

        except Exception as e:
            return Response(error_response(str(e)), status=500)
