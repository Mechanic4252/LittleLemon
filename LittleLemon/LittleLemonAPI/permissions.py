from rest_framework import permissions

class ManagerAndCustomerPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        else:
            return request.user.groups.filter(name='Manager').exists()

class IsOnlyManagerPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Manager').exists()

class IsOwnerPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method == 'DELETE':
            return obj.owner == request.user
        return False

class IsOwnerAndManagerCustomerPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):        
        if request.method in ['DELETE', 'PUT', 'PATCH'] and request.user.groups.filter(name='Manager').exists():
            return True

        if request.method in ['PATCH'] and request.user.groups.filter(name='Delivery crew').exists():
            return True

        if request.method in ['GET', 'PUT', 'PATCH'] and not request.user.groups.filter(name='Manager').exists() and not request.user.groups.filter(name='Delivery crew').exists():
            return True
        else:
            return False
