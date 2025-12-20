from django.contrib import admin
from .models import (
    Portal, PortalCategory, MasterCategory, MasterCategoryMapping, Group, MasterNewsPost, NewsDistribution, PortalPrompt,
    NewsPublishTask, NewsArticle, NewsSource, NewsSourceFeed, CrossPortalMapping
)

@admin.register(Portal)
class PortalAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'base_url']
    search_fields = ['id', 'name', 'base_url']
    list_filter = ['id', 'name', 'base_url']
    

@admin.register(PortalCategory)
class PortalCategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'portal', 'name', 'external_id', "parent_name", "parent_external_id"]
    search_fields =['id', 'portal', 'name', 'external_id', "parent_name", "parent_external_id"]
    list_filter = ['id', 'portal', 'name', 'external_id', "parent_name", "parent_external_id"]


@admin.register(MasterCategory)
class MasterCategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description']
    search_fields = ['id', 'name', 'description']
    list_filter = ['id', 'name', 'description']


@admin.register(MasterCategoryMapping)
class MasterCategoryMappingAdmin(admin.ModelAdmin):
    list_display = ['id', 'master_category', 'portal_category', 'use_default_content']
    search_fields = ['id', 'master_category', 'portal_category', 'use_default_content']
    list_filter = ['id', 'master_category', 'portal_category', 'use_default_content']


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['id', 'name']
    list_filter = ['id', 'name']
    

@admin.register(MasterNewsPost)
class MasterNewsPostAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'created_by__username', 'master_category', 'created_at']
    search_fields = [
        "title",
        "slug",
        "meta_title",
        "created_by__username",
        "master_category",
        'created_at'
    ]
    list_filter = ['id', 'title', 'created_by__username', 'master_category', 'created_at']


@admin.register(NewsDistribution)
class NewsDistributionAdmin(admin.ModelAdmin):
    list_display = ['id', 'news_post', 'portal', 'portal_category', 'status', 'master_category', 'news_post__created_by__username', 'time_taken', 'created_at']
    search_fields = ['id', 'news_post', 'portal', 'portal_category', 'status', 'master_category', 'news_post__created_by__username', 'time_taken', 'created_at']
    list_filter = ['id', 'news_post', 'portal', 'portal_category', 'status', 'master_category', 'news_post__created_by__username', 'time_taken', 'created_at']


@admin.register(PortalPrompt)
class PortalPromptAdmin(admin.ModelAdmin):
    list_display = ['id', 'portal', 'prompt_text', 'is_global_prompt']
    search_fields = ['id', 'portal', 'prompt_text', 'is_global_prompt']
    list_filter = ['id', 'portal', 'prompt_text', 'is_global_prompt']


@admin.register(NewsPublishTask)
class NewsPublishTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'news_post', 'task_id', 'status', 'triggered_by']
    search_fields = ['id', 'news_post', 'task_id', 'status', 'triggered_by']
    list_filter = ['id', 'news_post', 'task_id', 'status', 'triggered_by']


@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description']
    search_fields = ['id', 'name', 'description']
    list_filter = ['id', 'name', 'description']


@admin.register(NewsSourceFeed)
class NewsSourceFeedAdmin(admin.ModelAdmin):
    list_display = ['id', 'source', 'section_name', 'rss_url']
    search_fields = ['id', 'source', 'section_name', 'rss_url']
    list_filter = ['id', 'source', 'section_name', 'rss_url']


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'link', 'source_feed']
    search_fields = ['id', 'title', 'link', 'source_feed']
    list_filter = ['id', 'title', 'link', 'source_feed']


@admin.register(CrossPortalMapping)
class CrossPortalMappingAdmin(admin.ModelAdmin):
    list_display = ['id', 'source_category', 'target_category', 'created_at']
    search_fields = ['id', 'source_category', 'target_category', 'created_at']
    list_filter = ['id', 'source_category', 'target_category', 'created_at']
