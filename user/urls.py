from django.urls import path
from .views import (
    CheckUsernameAcrossPortalsAPIView, PortalUserMappingCreateAPIView, UserRegistrationAPIView, UserPortalMappingsListAPIView,
    LoginView, UserAssignmentCreateAPIView, UserAssignmentListByUserAPIView, UserAssignmentListAPIView, PortalUserMappingManualAPIView,
    PortalUserMappingUpdateAPIView, UserListAPIView, UserAssignedPortalsView, UnassignedUsersAPIView, UserDetailsListAPIView,\
    UserAssignmentRemoveAPIView, MyAssignmentListAPIView, AllUsersAPIView, AssignPortalToUserAPIView, RemovePortalFromUserAPIView, 
    ListUserPortalsAPIView,
)

urlpatterns = [
    # Login, Registration & users
    path('login/', LoginView.as_view(), name='token_obtain_pair'),
    path('registration/', UserRegistrationAPIView.as_view()),
    path('users/list/', UserListAPIView.as_view()),
    
    # User portal sync
    path('check/username/', CheckUsernameAcrossPortalsAPIView.as_view()),
    path('portal/user/mapping/', PortalUserMappingCreateAPIView.as_view()),
    path('portal/user/mapping/manual/', PortalUserMappingManualAPIView.as_view()),
    path('portal/user/mapping/update/<int:pk>/', PortalUserMappingUpdateAPIView.as_view()),
    path('user/mapped/portals/', UserPortalMappingsListAPIView.as_view()),
    
    # User group/category mapping
    path('user/assignment/', UserAssignmentCreateAPIView.as_view()),
    path('remove/user/assignment/', UserAssignmentRemoveAPIView.as_view()),
    path('user/assignments/list/<str:username>/', UserAssignmentListByUserAPIView.as_view()),
    path('my/assignments/list/', MyAssignmentListAPIView.as_view()),
    path('assignments/list/', UserAssignmentListAPIView.as_view()),
    path('user/assigned/portals/', UserAssignedPortalsView.as_view()),
    path('unassigned/users/', UnassignedUsersAPIView.as_view()),
    path('user/details/list/', UserDetailsListAPIView.as_view()),
    path('all/users/list/', AllUsersAPIView.as_view()),
    
    #User Portal assignment
    path("user/assign-portal/", AssignPortalToUserAPIView.as_view()),
    path("user/remove-portal/", RemovePortalFromUserAPIView.as_view()),
    path("user/portals/<int:user_id>/", ListUserPortalsAPIView.as_view()),
]