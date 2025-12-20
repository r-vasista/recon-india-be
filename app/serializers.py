from rest_framework import serializers
from .models import (
    Portal, PortalCategory, MasterCategory, MasterCategoryMapping, Group, MasterNewsPost, NewsDistribution, CrossPortalMapping
)

class PortalSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/updating Portal.
    Includes all fields, including API/Secret keys.
    """

    class Meta:
        model = Portal
        fields = ["id", "name", "base_url", "api_key", "secret_key"]

    # def validate_name(self, value):
    #     if Portal.objects.filter(name=value).exclude(id=self.instance.id if self.instance else None).exists():
    #         raise serializers.ValidationError("A portal with this name already exists.")
    #     return value


class PortalSafeSerializer(serializers.ModelSerializer):
    """
    Safe serializer for listing and retrieving portals.
    Hides sensitive fields (api_key, secret_key).
    """

    class Meta:
        model = Portal
        fields = ["id", "name", "base_url"]


class PortalCategorySerializer(serializers.ModelSerializer):
    portal_name = serializers.CharField(write_only=True)

    class Meta:
        model = PortalCategory
        fields = ["id", "external_id", "name", "portal_name", "parent_name", "parent_external_id"]

    def create(self, validated_data):
        portal_name = validated_data.pop("portal_name")
        portal = Portal.objects.get(name=portal_name)
        return PortalCategory.objects.create(portal=portal, **validated_data)

    def update(self, instance, validated_data):
        if "portal_name" in validated_data:
            portal_name = validated_data.pop("portal_name")
            portal = Portal.objects.get(name=portal_name)
            instance.portal = portal
        return super().update(instance, validated_data)


class MasterCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterCategory
        fields = ["id", "name", "description", "created_at", "updated_at"]


class MasterCategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterCategory
        fields = ["id", "name"]
        

class MasterCategoryMappingSerializer(serializers.ModelSerializer):
    master_category_name = serializers.CharField(source="master_category.name", read_only=True)
    portal_name = serializers.CharField(source="portal_category.portal.name", read_only=True)
    portal_category_name = serializers.CharField(source="portal_category.name", read_only=True)
    portal_id = serializers.CharField(source="portal_category.portal.id", read_only=True)

    class Meta:
        model = MasterCategoryMapping
        fields = [
            "id",
            "master_category",
            "master_category_name",
            "portal_category",
            "portal_name",
            "portal_id",
            "portal_category_name",
            "use_default_content",
            "is_default",
        ]
        
class GroupSerializer(serializers.ModelSerializer):
    master_categories = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=MasterCategory.objects.all()
    )

    class Meta:
        model = Group
        fields = ['id', 'name', 'master_categories']


class GroupListSerializer(serializers.ModelSerializer):
    master_categories = MasterCategoryListSerializer(many=True)

    class Meta:
        model = Group
        fields = ['id', 'name', 'master_categories']


class MasterNewsPostSerializer(serializers.ModelSerializer):
    post_image = serializers.ImageField(required=False, allow_null=True, use_url=True)
    master_category_name = serializers.CharField(source='master_category.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = MasterNewsPost
        fields = '__all__'
        read_only_fields = ["id", "created_at", "updated_at"]


class MasterNewsPostListSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = MasterNewsPost
        fields = ['title', 'short_description', 'post_image', 'created_by', 'created_at', 'updated_at']


class NewsDistributionSerializer(serializers.ModelSerializer):
    news_post_title = serializers.CharField(source="news_post.title", read_only=True)
    portal_name = serializers.CharField(source="portal.name", read_only=True)
    master_category_name = serializers.CharField(source="master_category.name", read_only=True)
    portal_category_name = serializers.CharField(source="portal_category.name", read_only=True)
    news_post_image = serializers.SerializerMethodField()

    class Meta:
        model = NewsDistribution
        fields = "__all__"
        
    def get_news_post_image(self, obj):
        request = self.context.get("request")
        if obj.news_post.post_image and request:
            return request.build_absolute_uri(obj.news_post.post_image.url)
        return None

class NewsDistributionListSerializer(serializers.ModelSerializer):
    news_post_title = serializers.CharField(source="news_post.title", read_only=True)
    news_post_created_by = serializers.CharField(source="news_post.created_by", read_only=True)
    news_post_image = serializers.SerializerMethodField()
    portal_name = serializers.CharField(source="portal.name", read_only=True)
    master_category_name = serializers.CharField(source="master_category.name", read_only=True)
    portal_category_name = serializers.CharField(source="portal_category.name", read_only=True)
    live_url = serializers.SerializerMethodField()

    class Meta:
        model = NewsDistribution
        fields = ['id', 'news_post_title', 'portal_name', 'master_category_name', 'portal_category_name', 'status', 
                  'sent_at', 'retry_count', 'news_post_image', 'news_post_created_by', 'ai_title', 'ai_short_description',
                  'ai_content', 'ai_meta_title', 'ai_slug', 'live_url', 'time_taken', 'response_message', 'portal_news_id']
    
    def get_news_post_image(self, obj):
        request = self.context.get("request")
        if obj.news_post.post_image and request:
            return request.build_absolute_uri(obj.news_post.post_image.url)
        return None
    
    def get_live_url(self, obj):
        """
        Returns the live URL for the distributed news post, following the pattern:
        <portal.domain_url>/<ai_slug>
        Example: https://www.gccnews24.com/sresan-pharma-owner-arrested-after-children-die-from-toxic-syrup
        """
        if obj.portal and obj.portal.domain_url and obj.ai_slug:
            domain = obj.portal.domain_url.rstrip("/") 
            slug = obj.ai_slug.lstrip("/")
            return f"{domain}/{slug}"
        return None


class CrossPortalMappingReadSerializer(serializers.ModelSerializer):
    """
    Read-only serializer to show human-readable details.
    """
    target_category_name = serializers.CharField(source='target_category.name', read_only=True)
    target_portal_name = serializers.CharField(source='target_category.portal.name', read_only=True)
    target_portal_id = serializers.IntegerField(source='target_category.portal.id', read_only=True)

    class Meta:
        model = CrossPortalMapping
        fields = [
            'id', 
            'source_category', 
            'target_category', 
            'target_category_name', 
            'target_portal_name', 
            'target_portal_id'
        ]

class CrossPortalMappingCreateSerializer(serializers.Serializer):
    """
    Write serializer to handle mapping one source to MULTIPLE targets.
    """
    source_category_id = serializers.IntegerField()
    target_category_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        allow_empty=False,
        help_text="List of PortalCategory IDs to map to."
    )

    def validate(self, data):
        source_id = data['source_category_id']
        target_ids = data['target_category_ids']

        # 1. Validate Source Exists
        if not PortalCategory.objects.filter(id=source_id).exists():
            raise serializers.ValidationError({"source_category_id": "Invalid source category ID."})

        # 2. Validate Targets Exist
        valid_targets = PortalCategory.objects.filter(id__in=target_ids).count()
        if valid_targets != len(set(target_ids)):
             raise serializers.ValidationError({"target_category_ids": "One or more target category IDs are invalid."})

        # 3. Prevent Self-Mapping
        if source_id in target_ids:
            raise serializers.ValidationError("Cannot map a category to itself.")

        return data

    def create(self, validated_data):
        source_id = validated_data['source_category_id']
        target_ids = validated_data['target_category_ids']
        
        source_cat = PortalCategory.objects.get(id=source_id)
        created_mappings = []

        for target_id in target_ids:
            # get_or_create prevents duplicates if user submits same list twice
            mapping, created = CrossPortalMapping.objects.get_or_create(
                source_category=source_cat,
                target_category_id=target_id
            )
            if created:
                created_mappings.append(mapping)
        
        return created_mappings
    

class SourceCategoryDetailSerializer(serializers.ModelSerializer):
    """
    Serializes the 'requested_portal_category' part of the response.
    """
    portal_name =serializers.CharField(source='portal.name')
    portal_id = serializers.CharField(source='portal.id')

    class Meta:
        model = PortalCategory
        fields = [
            'id', 
            'name', 
            'parent_name', 
            'portal_name',
            'portal_id',
        ]

class MappedTargetCategorySerializer(serializers.ModelSerializer):
    """
    Serializes the 'mapped_portal_categories' list.
    It takes a CrossPortalMapping object but outputs the Target Category details
    plus the Portal Name.
    """
    # Map fields from the related 'target_category'
    id = serializers.IntegerField(source='target_category.id')
    name = serializers.CharField(source='target_category.name')
    parent_name = serializers.CharField(source='target_category.parent_name')
    
    # Map fields from the related 'target_category.portal'
    portal_name = serializers.CharField(source='target_category.portal.name')
    portal_id = serializers.CharField(source='target_category.portal.id')
    

    # Essential: Include the Mapping ID so the frontend knows which ID to delete
    cross_mapping_id = serializers.IntegerField(source='id')

    class Meta:
        model = CrossPortalMapping
        fields = [
            'id', 
            'name',
            'parent_name', 
            'portal_name',
            'portal_id',
            'cross_mapping_id' 
        ]
