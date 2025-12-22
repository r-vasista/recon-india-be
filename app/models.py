import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify

from django.core.exceptions import ValidationError

User = get_user_model()

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    is_active = models.BooleanField(default=True)
    inactivated_at = models.DateTimeField(null=True, blank=True)

    def deactivate(self):
        self.is_active = False
        self.inactivated_at = timezone.now()
        self.save()

    def activate(self):
        self.is_active = True
        self.inactivated_at = None
        self.save()

    class Meta:
        abstract = True


class Portal(BaseModel):
    """Represents an external news portal (other Django project)."""
    name = models.CharField(max_length=150, unique=True)
    base_url = models.URLField(help_text="API's url ex: https://domain.com/portal_name")
    domain_url = models.URLField(help_text="Just the domain url ex: https://domain.com", null=True)
    api_key = models.CharField(max_length=255)
    secret_key = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class PortalCategory(BaseModel):
    """Categories belonging to a Portal."""
    portal = models.ForeignKey(Portal, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=150)
    external_id = models.CharField(max_length=100)
    parent_name = models.CharField(max_length=255, null=True, blank=True)  # 🔹 store parent category name
    parent_external_id = models.CharField(max_length=255, null=True, blank=True) 

    class Meta:
        unique_together = ("portal", "external_id")

    def __str__(self):
        return f"{self.portal.name} - {self.name}"


class MasterCategory(BaseModel):
    """Super Admin defined category grouping across portals."""
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class MasterCategoryMapping(BaseModel):
    """Mapping between MasterCategory and PortalCategory."""
    master_category = models.ForeignKey(MasterCategory, on_delete=models.CASCADE, related_name="mappings")
    portal_category = models.ForeignKey(PortalCategory, on_delete=models.CASCADE, related_name="mappings")
    use_default_content = models.BooleanField(default=False, help_text="If true, send MasterNewsPost content without GPT rewrite")
    is_default = models.BooleanField(default=False)

    class Meta:
        unique_together = ("master_category", "portal_category")

    def __str__(self):
        return f"{self.master_category.name} -> {self.portal_category}"


class Group(BaseModel):
    """Group of master categories assigned to users."""
    name = models.CharField(max_length=150, unique=True)
    master_categories = models.ManyToManyField(MasterCategory, related_name="groups")

    def __str__(self):
        return self.name


class UserGroup(BaseModel):
    """Assigns a user to a group (1 user -> 1 group)."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="user_group")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="users")

    def __str__(self):
        return f"{self.user} -> {self.group}"


class MasterNewsPost(BaseModel):
    """Main news post created inside Recon."""
    
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("PUBLISHED", "Published"),
    ]
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="master_news_posts")

    # Mandatory fields
    title = models.CharField(max_length=255)
    short_description = models.CharField(max_length=300)
    content = models.TextField()
    post_image = models.ImageField(upload_to="posts/%Y/%m/%d/")
    
    # Optional overrides
    is_active = models.BooleanField(null=True, blank=True)
    latest_news = models.BooleanField(null=True, blank=True)
    upcoming_event = models.BooleanField(null=True, blank=True)
    Head_Lines = models.BooleanField(null=True, blank=True)
    articles = models.BooleanField(null=True, blank=True)
    trending = models.BooleanField(null=True, blank=True)
    BreakingNews = models.BooleanField(null=True, blank=True)
    Event = models.BooleanField(null=True, blank=True)
    Event_date = models.DateField(null=True, blank=True)
    Event_end_date = models.DateField(null=True, blank=True)
    schedule_date = models.DateTimeField(null=True, blank=True)
    post_tag = models.TextField(null=True, blank=True)
    counter = models.PositiveIntegerField(null=True, blank=True)
    
    # For recon india
    newstype_slug = models.SlugField(max_length=100, null=True, blank=True, 
                                     help_text="Slug for newsfrom field (e.g., 'punjab', 'warraich-towns')")
    
    # SEO fields
    meta_title = models.CharField(max_length=255, null=True, blank=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    
    # Mastercategory and exclude portal data
    master_category = models.ForeignKey(
        MasterCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="news_posts"
    )
    excluded_portals = models.JSONField(null=True, blank=True, default=list)
    portal_category_ids = models.JSONField(null=True, blank=True, default=list)
    exclude_portal_categories = models.JSONField(null=True, blank=True, default=list)
    cross_portal_category_id = models.IntegerField(null=True, blank=True, help_text="The specific portal category that triggers cross-posting logic.")

    # Meta info
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="PUBLISHED"
    )

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while MasterNewsPost.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class NewsDistribution(BaseModel):
    """
    Tracks distribution of a news post to each portal.
    Stores optional per-portal overrides.
    Example: user may set BreakingNews=True for Portal A,
             but leave it empty for Portal B.
    """
    news_post = models.ForeignKey(MasterNewsPost, on_delete=models.CASCADE, related_name="news_distribution")
    portal = models.ForeignKey(Portal, on_delete=models.CASCADE)
    portal_category = models.ForeignKey(PortalCategory, on_delete=models.SET_NULL, null=True, blank=True)
    group = models.ForeignKey(
        Group, on_delete=models.SET_NULL, null=True, blank=True, related_name="news_distributions"
    )
    master_category = models.ForeignKey(
        MasterCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="news_distributions"
    )
    portal_news_id = models.CharField(max_length=255, null=True, blank=True,
                                      help_text="ID of the NewsPost object in the target portal.")

    extra_data = models.JSONField(null=True, blank=True)
    
    ai_title = models.CharField(max_length=255, null=True, blank=True)
    ai_short_description = models.CharField(max_length=300, null=True, blank=True)
    ai_content = models.TextField(null=True, blank=True)
    ai_meta_title = models.CharField(max_length=255, null=True, blank=True)
    ai_slug = models.SlugField(max_length=255, null=True, blank=True)
    edited_image = models.ImageField(upload_to="distribution_edits/%Y/%m/%d/", null=True, blank=True, help_text="Edited image for this portal-specific distribution.")       
    # Store the newstype slug that was sent (for reference only)
    newstype_slug_sent = models.SlugField(max_length=100, null=True, blank=True,
                                          help_text="The newstype slug sent to portal")

    status = models.CharField(
        max_length=20,
        choices=(("PENDING", "Pending"), ("SUCCESS", "Success"), ("FAILED", "Failed")),
        default="PENDING"
    )
    response_message = models.TextField(null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    retry_count = models.PositiveIntegerField(default=0)
    edit_count = models.PositiveIntegerField(default=0)
    time_taken = models.FloatField(default=0.0, help_text="Time taken in seconds to publish on this portal")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ("news_post", "portal")

    def __str__(self):
        return f"{self.news_post.title} -> {self.portal.name}"


class PortalPrompt(models.Model):
    """Stores custom AI rewrite prompts for each portal (or globally)."""
    portal = models.OneToOneField(
        'Portal',
        on_delete=models.CASCADE,
        related_name='prompt',
        null=True,
        blank=True,
        help_text="Optional — if empty, use this prompt globally."
    )
    name = models.CharField(max_length=150, null=True, help_text="Prompt name, e.g., 'Default Rewrite Prompt'")
    prompt_text = models.TextField(help_text="The text prompt that controls GPT rewriting behavior.")
    is_active = models.BooleanField(default=True)
    is_global_prompt = models.BooleanField(
        default=False,
        help_text="If true, this prompt applies globally when no portal-specific prompt exists."
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Portal Prompt"
        verbose_name_plural = "Portal Prompts"

    def clean(self):
        # Enforce that only one global prompt can exist
        if self.is_global_prompt:
            qs = PortalPrompt.objects.filter(is_global_prompt=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError("Only one global prompt is allowed.")

        # A global prompt should not be linked to a portal
        if self.is_global_prompt and self.portal is not None:
            raise ValidationError("Global prompt cannot be linked to a specific portal.")

        # Non-global prompts must have a portal
        if not self.is_global_prompt and self.portal is None:
            raise ValidationError("Non-global prompts must be linked to a specific portal.")

    def save(self, *args, **kwargs):
        self.full_clean()  # Run clean() before saving
        super().save(*args, **kwargs)

    def __str__(self):
        if self.is_global_prompt:
            return f"🌍 Global Prompt: {self.name}"
        return f"{self.portal.name} Prompt"


class NewsPublishTask(models.Model):
    news_post = models.ForeignKey(
        MasterNewsPost, 
        on_delete=models.CASCADE, 
        related_name="publish_tasks"
    )

    task_id = models.CharField(
        max_length=255, 
        db_index=True
    )

    triggered_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "Pending"),
            ("STARTED", "Started"),
            ("SUCCESS", "Success"),
            ("FAILURE", "Failure"),
        ],
        default="PENDING"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.task_id} → {self.news_post.title}"


class NewsSource(models.Model):
    """Represents a news source (e.g., BBC, Times of India, etc.)."""
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name
    
    
class NewsSourceFeed(models.Model):
    """Represents a specific RSS feed section for a news source."""
    source = models.ForeignKey(NewsSource, on_delete=models.CASCADE, related_name="feeds")
    section_name = models.CharField(max_length=255)
    rss_url = models.URLField(unique=True)
    
    def __str__(self):
        return f"{self.source.name} - {self.section_name}"


class NewsArticle(models.Model):
    """Represents an article fetched from an RSS feed."""
    title = models.CharField(max_length=255)
    link = models.URLField()
    summary = models.TextField(null=True, blank=True)
    content = models.TextField(null=True, blank=True)
    published_at = models.DateTimeField()
    source_feed = models.ForeignKey(NewsSourceFeed, on_delete=models.CASCADE, related_name="articles")
    guid = models.CharField(max_length=255, unique=True)  # RSS unique identifier for the article
    author = models.CharField(max_length=255, null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)
    tags = models.JSONField(default=list, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    

class CrossPortalMapping(BaseModel):
    """
    Defines the flow: When a news post is sent to 'source_category',
    automatically send it to 'target_category' as well.
    """
    source_category = models.ForeignKey(
        PortalCategory, 
        on_delete=models.CASCADE, 
        related_name="outgoing_mappings",
        help_text=" The category the user selects (Trigger)"
    )
    target_category = models.ForeignKey(
        PortalCategory, 
        on_delete=models.CASCADE, 
        related_name="incoming_mappings",
        help_text="The category to automatically distribute to"
    )

    class Meta:
        unique_together = ("source_category", "target_category")
        verbose_name = "Cross Portal Mapping"
        verbose_name_plural = "Cross Portal Mappings"

    def __str__(self):
        return f"{self.source_category} -> {self.target_category}"


class MasterNewsPortalImage(models.Model):
    news_post = models.ForeignKey(MasterNewsPost, on_delete=models.CASCADE, related_name="portal_images")
    portal = models.ForeignKey(Portal, on_delete=models.CASCADE, related_name="custom_post_images")
    custom_image = models.ImageField(upload_to="portal_specific/%Y/%m/%d/")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('news_post', 'portal')

    def __str__(self):
        return f"Image for {self.portal.name} - {self.news_post.title}"
