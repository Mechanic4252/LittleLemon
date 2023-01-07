from django.urls import path, include
from .views import (MenuItemsView, RetrieveMenuItemsView, managersView, 
DeliveryCrewView, RemoveUserFromGroupView, OrdersView, OrderView, CategoryView, UpdateCategoryView, CartView)

urlpatterns = [
    path('', include('djoser.urls')),
    path('', include('djoser.urls.authtoken')),
    path('category', CategoryView.as_view()),
    path('category/<int:menuItem>', UpdateCategoryView.as_view()),
    path('menu-items', MenuItemsView.as_view()),
    path('menu-items/<int:pk>', RetrieveMenuItemsView.as_view()),
    path('groups/manager/users', managersView),
    path('groups/manager/users/<str:userId>', managersView),
    path('groups/delivery-crew/users', DeliveryCrewView.as_view()),
    path('groups/delivery-crew/users/<int:pk>', RemoveUserFromGroupView.as_view()),
    path('cart/menu-items', CartView.as_view()),
    path('orders', OrdersView),
    path('orders/<int:orderId>', OrderView.as_view())
]