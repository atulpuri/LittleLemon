from django.urls import path, include
from . import views 

urlpatterns = [
    path("category", views.CategoriesView.as_view()),
    path("menu-items", views.MenuItemsView.as_view()),
    path("menu-items/<int:pk>", views.SingleMenuItemsView.as_view()),
    path("groups/<str:group>/users", views.GroupsView.as_view()),
    path("groups/<str:group>/users/<str:userId>", views.GroupsDeleteView.as_view()),
    path("cart/menu-items", views.CartView.as_view()),
    path("orders", views.OrdersView.as_view()),
    path("orders/<int:pk>", views.SingleOrderView.as_view()),
]