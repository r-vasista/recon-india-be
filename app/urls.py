from django.urls import path
from .views import (
    PortalListCreateView, PortalDetailView, PortalCategoryCreateView, PortalCategoryUpdateDeleteView,
    PortalCategoryListView, MasterCategoryView, MasterCategoryMappingView, MasterCategoryMappingsListView,
    GroupCreateListAPIView, GroupRetrieveUpdateDeleteAPIView, GroupCategoriesListAPIView, MasterNewsPostPublishAPIView,
    NewsPostCreateAPIView, PortalCreateAPIView, UserPostsListAPIView, AllNewsPostsAPIView, NewsDistributionListAPIView,
    NewsDistributionDetailAPIView, AdminStatsAPIView, DomainDistributionStatsAPIView, AllPortalsTagsLiveAPIView, 
    NewsPostUpdateAPIView, MyPostsListAPIView, NewsReportAPIView, NewsKPIAPIView, PortalStatsAPIView, GlobalStatsAPIView,
    InactivityAlertsAPIView, NewsDistributionRateOverTimeAPIView, FailureReasonsStatsAPIView, MasterCategoryHeatmapAPIView,
    UserPostStatsAPIView, UserPerformanceAPIView, NewsDistributionEditAPIView, NewsDistributionDeleteAPIView, 
    CategoryStatsAPIView, UserPortalDistributionStatsAPIView, NewsDistributionFetchAPIView, BackgroundNewsPostPublishAPIView,
    PublishStatusAPIView, NewsPublishTaskListAPIView, UniqueParentCategoryAPIView, PortalCategoriesByParentAPIView,
    PortalCategoryMatchWithMasterCategoryAPIView, CrossPortalMappingListCreateAPIView, CrossPortalMappingDeleteAPIView,
    NewsPortalImageUploadAPIView, PortalNewsTypeListAPIView
)

urlpatterns = [
    # Portals
    path('portals/list/', PortalListCreateView.as_view()),
    path('portal/detail/<int:id>/', PortalDetailView.as_view()),
    path('create/portal/', PortalCreateAPIView.as_view()),
    path('all/tags/', AllPortalsTagsLiveAPIView.as_view()),
    
    # Portal Category
    path('portal/category/', PortalCategoryCreateView.as_view()),
    path('portal/category/<str:portal_name>/<str:external_id>/', PortalCategoryUpdateDeleteView.as_view()),
    path('portals/categories/list/<str:portal_name>/', PortalCategoryListView.as_view()),
    path('portal/category/matching/', PortalCategoryMatchWithMasterCategoryAPIView.as_view()),
    
    # Cross portal Mapping
    path('cross-portal-mappings/', CrossPortalMappingListCreateAPIView.as_view()),
    path('cross-portal-mappings/<int:pk>/', CrossPortalMappingDeleteAPIView.as_view()),
    
    # Master Category
    path('master/category/', MasterCategoryView.as_view()),
    path('master/category/<int:pk>/', MasterCategoryView.as_view()),
    path('master/category/mapping/', MasterCategoryMappingView.as_view()),
    path('master/category/mapping/<int:pk>/', MasterCategoryMappingView.as_view()),
    path('master/categories/mapped/<int:master_category_id>/', MasterCategoryMappingsListView.as_view()),
    path('parent/categories/list/<int:portal_id>/', UniqueParentCategoryAPIView.as_view()),
    path('sub-categories/by/parent/category/', PortalCategoriesByParentAPIView.as_view()),
    
    # News type (news from)
    path('portal/newstype/<int:portal_id>/', PortalNewsTypeListAPIView.as_view(), name='portal-newstype-list'),
    
    # Groups
    path('group/', GroupCreateListAPIView.as_view()),
    path('group/<int:pk>/', GroupRetrieveUpdateDeleteAPIView.as_view()),
    path('group/categories/', GroupCategoriesListAPIView.as_view()),
    
    # News and Distribution
    path('news/create/', NewsPostCreateAPIView.as_view()),
    path('news/update/<int:pk>/', NewsPostUpdateAPIView.as_view()),
    path('publish/news/<int:pk>/', MasterNewsPostPublishAPIView.as_view()),
    path('back-ground/publish/news/<int:pk>/', BackgroundNewsPostPublishAPIView.as_view()),
    path('news/<int:pk>/', NewsDistributionFetchAPIView.as_view()),
    path('edit/news/<int:pk>/', NewsDistributionEditAPIView.as_view()),
    path('delete/news/<int:pk>/', NewsDistributionDeleteAPIView.as_view()),
    path('user/news/posts/', UserPostsListAPIView.as_view()),
    path('my/news/posts/', MyPostsListAPIView.as_view()),
    path('all/posts/', AllNewsPostsAPIView.as_view()),
    path('news/distributed/list/', NewsDistributionListAPIView.as_view()),
    path('news/distributed/detail/<int:pk>/', NewsDistributionDetailAPIView.as_view()),
    path('publish/status/', PublishStatusAPIView.as_view()),
    path('news/publish/tasks/list/<int:pk>/', NewsPublishTaskListAPIView.as_view()),
    path('portal-image-upload/<int:pk>/',NewsPortalImageUploadAPIView.as_view()),
    
    # Stats and Dashboard
    path('admin/stats/', AdminStatsAPIView.as_view()),
    path('domain/distribution/', DomainDistributionStatsAPIView.as_view()),
    path('news/report/', NewsReportAPIView.as_view()),
    path('news/kpi/', NewsKPIAPIView.as_view()),
    path('portal/stats/', PortalStatsAPIView.as_view()),
    path('global/stats/', GlobalStatsAPIView.as_view()),
    path('inactivity/alerts/', InactivityAlertsAPIView.as_view()),
    path('news/distribution/rate/', NewsDistributionRateOverTimeAPIView.as_view()),
    path('failure/news/distribution/stats/', FailureReasonsStatsAPIView.as_view()),
    path('category/heatmap/', MasterCategoryHeatmapAPIView.as_view()),
    path('user/posts/stats/', UserPostStatsAPIView.as_view()),
    path('user/performance/<int:user_id>/', UserPerformanceAPIView.as_view()),
    path('user/portal/performance/<int:user_id>/', UserPortalDistributionStatsAPIView.as_view()),
    path('category/stats/<int:category_id>/', CategoryStatsAPIView.as_view()),
]
