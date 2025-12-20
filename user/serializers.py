from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils import timezone
from datetime import timedelta, datetime
from django.contrib.auth import get_user_model
import jwt

from .models import (
    PortalUserMapping, UserCategoryGroupAssignment, Portal, UserPortalAssignment
)
from app.models import (
    Group, MasterCategoryMapping, MasterCategory, NewsDistribution
)
from app.serializers import (
    MasterCategoryListSerializer, GroupListSerializer, PortalCategorySerializer
)
User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email"),
            password=validated_data["password"],
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Get the refresh token to extract expiration times
        refresh = self.get_token(self.user)
        
        # Add additional user info
        role_name = None
        if hasattr(self.user, "role") and self.user.role:
            role_name = self.user.role.role.name
        
        # Calculate expiration times
        access_token_expiration = datetime.fromtimestamp(refresh.access_token['exp'])
        refresh_token_expiration = datetime.fromtimestamp(refresh['exp'])
        
        data.update({
            "user_id": self.user.id,
            "username": self.user.username,
            "role": role_name,
            "access_token_expiration": access_token_expiration.isoformat(),
            "refresh_token_expiration": refresh_token_expiration.isoformat(),
            # Optionally, also include the expiration in seconds from now
            "access_expires_in": refresh.access_token['exp'] - datetime.now().timestamp(),
            "refresh_expires_in": refresh['exp'] - datetime.now().timestamp(),
        })
        
        return data
    
class PortalCheckResultSerializer(serializers.Serializer):
    portal = serializers.CharField()
    found = serializers.BooleanField()
    user_id = serializers.IntegerField(required=False, allow_null=True)
    username = serializers.CharField(required=False, allow_null=True)
    message = serializers.CharField(required=False, allow_blank=True)


class PortalUserMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortalUserMapping
        fields = '__all__'
        read_only_fields = ["id", "created_at", "updated_at"]
   
        
class PortalUserMappingListSerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(source="portal.name", read_only=True)

    class Meta:
        model = PortalUserMapping
        fields = ["id", "portal_name", "portal_user_id", "status"]


class UserAssignmentCreateSerializer(serializers.Serializer):
    username = serializers.CharField(write_only=True)
    groups = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=Group.objects.all()),
        required=False,
        allow_empty=True
    )
    master_categories = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=MasterCategory.objects.all()),
        required=False,
        allow_empty=True
    )

    def validate(self, data):
        groups = data.get("groups", [])
        master_categories = data.get("master_categories", [])

        if not groups and not master_categories:
            raise serializers.ValidationError("Either groups or master_categories must be provided.")
        if groups and master_categories:
            raise serializers.ValidationError("You cannot assign both groups and master_categories in the same request.")

        return data

    def create(self, validated_data):
        username = validated_data.pop("username")
        groups = validated_data.pop("groups", [])
        master_categories = validated_data.pop("master_categories", [])

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist.")

        assignments = []
        if groups:
            for group in groups:
                assignment, _ = UserCategoryGroupAssignment.objects.get_or_create(
                    user=user, group=group
                )
                assignments.append(assignment)
        elif master_categories:
            for category in master_categories:
                assignment, _ = UserCategoryGroupAssignment.objects.get_or_create(
                    user=user, master_category=category
                )
                assignments.append(assignment)

        return assignments

class UserAssignmentListSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="user.username")
    group = GroupListSerializer()
    master_category = MasterCategoryListSerializer()

    class Meta:
        model = UserCategoryGroupAssignment
        fields = ["id", "user", "group", "master_category", "created_at"]

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "is_active",
            "date_joined",
        ]
        

class PortalWithPostsSerializer(serializers.ModelSerializer):
    categories = serializers.SerializerMethodField()
    total_posts = serializers.SerializerMethodField()
    todays_posts = serializers.SerializerMethodField()
    todays_success_posts = serializers.SerializerMethodField()
    total_success_posts = serializers.SerializerMethodField()

    class Meta:
        model = Portal
        fields = ["id", "name", "categories", "total_posts", "todays_posts", "todays_success_posts", "total_success_posts"]

    def get_categories(self, portal):
        user = self.context.get("user")
        if not user:
            return []

        assignments = UserCategoryGroupAssignment.objects.filter(user=user)
        categories = []

        for assignment in assignments:
            if assignment.master_category:
                mappings = MasterCategoryMapping.objects.filter(
                    master_category=assignment.master_category, portal_category__portal=portal
                ).select_related("portal_category")
                categories.extend([m.portal_category for m in mappings])
            elif assignment.group:
                for mc in assignment.group.master_categories.all():
                    mappings = MasterCategoryMapping.objects.filter(
                        master_category=mc, portal_category__portal=portal
                    ).select_related("portal_category")
                    categories.extend([m.portal_category for m in mappings])

        return PortalCategorySerializer(categories, many=True).data

    def get_total_posts(self, portal):
        user = self.context.get("user")
        return NewsDistribution.objects.filter(
            portal=portal,
            news_post__created_by=user
        ).count()
        
    def get_todays_posts(self, portal):
        """
        Returns the count of posts published today by this user for the given portal.
        """
        user = self.context.get("user")
        if not user:
            return 0

        today = timezone.now().date()
        return NewsDistribution.objects.filter(
            portal=portal,
            news_post__created_by=user,
            sent_at__date=today
        ).count()
    
    def get_todays_success_posts(self, portal):
        """
        Returns the count of successfully distributed posts today by this user for the given portal.
        """
        user = self.context.get("user")
        if not user:
            return 0

        today = timezone.now().date()
        return NewsDistribution.objects.filter(
            portal=portal,
            news_post__created_by=user,
            sent_at__date=today,
            status="SUCCESS"
        ).count()
    
    def get_total_success_posts(self, portal):
        user = self.context.get("user")
        return NewsDistribution.objects.filter(
            portal=portal,
            news_post__created_by=user,
            status="SUCCESS"
        ).count()



class UserWithPortalsSerializer(serializers.ModelSerializer):
    assigned_portals = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "date_joined", "assigned_portals"]

    def get_assigned_portals(self, user):
        # Collect unique portals for the user
        assignments = UserCategoryGroupAssignment.objects.filter(user=user)
        portal_set = {}
        for assignment in assignments:
            if assignment.master_category:
                mappings = MasterCategoryMapping.objects.filter(
                    master_category=assignment.master_category
                ).select_related("portal_category__portal")
                for m in mappings:
                    portal_set[m.portal_category.portal.id] = m.portal_category.portal
            elif assignment.group:
                for mc in assignment.group.master_categories.all():
                    mappings = MasterCategoryMapping.objects.filter(
                        master_category=mc
                    ).select_related("portal_category__portal")
                    for m in mappings:
                        portal_set[m.portal_category.portal.id] = m.portal_category.portal

        portals = list(portal_set.values())
        return PortalWithPostsSerializer(portals, many=True, context={"user": user}).data


class UserAssignmentRemoveSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    master_category_id = serializers.IntegerField(required=False)
    group_id = serializers.IntegerField(required=False)

    def validate(self, data):
        if not data.get("master_category_id") and not data.get("group_id"):
            raise serializers.ValidationError("Either master_category_id or group_id must be provided.")
        return data


class UserPortalAssignmentSerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(source="portal.name", read_only=True)

    class Meta:
        model = UserPortalAssignment
        fields = ["id", "user", "portal", "portal_name", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        user = attrs.get("user")
        portal = attrs.get("portal")

        if UserPortalAssignment.objects.filter(user=user, portal=portal).exists():
            raise serializers.ValidationError("Portal is already assigned to this user.")

        return attrs
