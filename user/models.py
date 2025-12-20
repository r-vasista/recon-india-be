import uuid
from django.db import models
from django.contrib.auth import get_user_model
from app.models import BaseModel, Portal, Group, MasterCategory

User = get_user_model()

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)  # e.g., ADMIN, USER, EDITOR

    def __str__(self):
        return self.name


class UserRole(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="role")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="users")

    def __str__(self):
        return f"{self.user.username} -> {self.role.name}"
    
    
class PortalUserMapping(BaseModel):
    """
    Maps a Recon user to their account in a specific portal.
    - When user logs in, Recon checks each portal by username.
    - If found, map immediately.
    - If not found, mark status=PENDING until user/admin resolves it.
    """

    STATUS_CHOICES = (
        ("MATCHED", "Matched"),   # Found a user in portal with same username
        ("PENDING", "Pending"),   # User not found, waiting for manual action
        ("MISMATCH", "Mismatch"), # Username exists but different (needs update)
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="portal_user_mappings")
    portal = models.ForeignKey(Portal, on_delete=models.CASCADE, related_name="user_mappings")

    # Portal-side reference
    portal_user_id = models.CharField(max_length=100, null=True, blank=True)  # ID from portal DB
    portal_username = models.CharField(max_length=150, null=True, blank=True) # Username in portal

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    notes = models.TextField(null=True, blank=True)  # extra info like error msg

    class Meta:
        unique_together = ("user", "portal")

    def __str__(self):
        return f"{self.user.username} -> {self.portal.name} ({self.status})"


class UserCategoryGroupAssignment(BaseModel):
    """Assign either a Group or a MasterCategory to a User."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="category_group_assignments")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True, related_name="user_assignments")
    master_category = models.ForeignKey(MasterCategory, on_delete=models.CASCADE, null=True, blank=True, related_name="user_assignments")

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(group__isnull=False, master_category__isnull=True) |
                    models.Q(group__isnull=True, master_category__isnull=False)
                ),
                name="only_one_of_group_or_category"
            ),
            models.UniqueConstraint(
                fields=["user", "group"],
                name="unique_user_group_assignment"
            ),
            models.UniqueConstraint(
                fields=["user", "master_category"],
                name="unique_user_category_assignment"
            ),
        ]

    def __str__(self):
        if self.group:
            return f"{self.user} → Group: {self.group}"
        return f"{self.user} → Category: {self.master_category}"


class UserPortalAssignment(BaseModel):
    """
    Assign a Portal to a User.
    (Similar to UserCategoryGroupAssignment but for portals only)
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="portal_assignments"
    )

    portal = models.ForeignKey(
        Portal,
        on_delete=models.CASCADE,
        related_name="user_assignments"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "portal"],
                name="unique_user_portal_assignment"
            )
        ]

    def __str__(self):
        return f"{self.user} → Portal: {self.portal}"
    