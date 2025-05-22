from rest_framework import permissions

class ManagerPermission(permissions.BasePermission):
    """
    Permission for Managers and Admin view.
    """

    def has_permission(self, request, view):
        return request.user.groups.filter(name='Manager').exists() or request.user.is_staff

class CustomerPermission(permissions.BasePermission):
    """
    Permission for Managers and Admin view.
    """

    def has_permission(self, request, view):
        is_manager = request.user.groups.filter(name='Manager').exists()
        is_delivery = request.user.groups.filter(name='Delivery Crew').exists()
        return not (is_manager or is_delivery)