from django.shortcuts import render
from rest_framework import generics, status, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from .models import MenuItem, Category, Cart, Order, OrderItem
from .serializers import MenuItemSerializer, CategorySerializer, UserSerializer, CartSerializer, \
                            OrderSerializer, OrderItemSerializer
from django.contrib.auth.models import User, Group
from django.shortcuts import get_object_or_404
from .permissions import ManagerPermission, CustomerPermission
from rest_framework.exceptions import PermissionDenied, NotFound
from django_filters.rest_framework import DjangoFilterBackend

class CategoriesView(generics.CreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class MenuItemsView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    ordering_fields = ['price']
    filterset_fields = ['price', 'category', 'featured']
    search_fields = ['title']
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]


class SingleMenuItemsView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    ordering_fields = ['price']
    filterset_fields = ['price', 'category', 'featured']
    search_fields = ['title']
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class GroupsView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, ManagerPermission]
    group_mapping = {'manager': 'Manager', 'delivery-crew': 'Delivery Crew'}

    def get_queryset(self):
        if self.kwargs['group'] in self.group_mapping:
            return Group.objects.get(name=self.group_mapping[self.kwargs['group']]).user_set.all()
        raise NotFound()

    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            if not (self.kwargs['group'] in self.group_mapping):
                return Response(status=status.HTTP_404_NOT_FOUND)
            
            username = request.data.get('username')
            if username:
                user = get_object_or_404(User, username=username)
                group = Group.objects.get(name=self.group_mapping[kwargs['group']])
                group.user_set.add(user)                
        
            return Response(status=status.HTTP_200_OK)            

class GroupsDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated, ManagerPermission]
    group_mapping = {'manager': 'Manager', 'delivery-crew': 'Delivery Crew'}

    def delete(self, request, group, userId):
        if request.method == 'DELETE':
            if not (group in self.group_mapping):
                return Response(status=status.HTTP_404_NOT_FOUND)
            if userId:
                user = get_object_or_404(User, username=userId)
                group = Group.objects.get(name=self.group_mapping[group])
                group.user_set.remove(user)
                return Response(status=status.HTTP_200_OK)
            return Response(status=status.HTTP_400_BAD_REQUEST)

class CartView(generics.ListCreateAPIView, generics.DestroyAPIView):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated, CustomerPermission]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)
    
    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        menuitem = get_object_or_404(MenuItem, id=data.get('menuitem_id'))

        # Compose data for serializer
        serializer_data = {
            'user_id': request.user.id,
            'menuitem_id': data.get('menuitem_id'),
            'quantity': int(data.get('quantity', 1)),
            'unit_price': float(menuitem.price),
        }

        serializer = self.get_serializer(data=serializer_data)
        if serializer.is_valid():
            print('is valid')
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        queryset = self.get_queryset()
        queryset.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class OrdersView(generics.ListAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.groups.filter(name='Manager').exists():
            orders = Order.objects.all()
        elif self.request.user.groups.filter(name='Delivery Crew').exists():
            orders = Order.objects.filter(delivery_crew=self.request.user)
        else:
            orders = Order.objects.filter(user=self.request.user)
        return orders
        
    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            user = request.user
            
            if user.groups.filter(name='Delivery Crew').exists() or user.groups.filter(name='Manager').exists():
                return Response({'message': 'action not permitted'}, status=status.HTTP_403_FORBIDDEN)

            cart = Cart.objects.filter(user=user)
            if not len(cart):
                return Response({'message': 'no items in cart for user'},
                                status=status.HTTP_400_BAD_REQUEST)
            
            order_details = {
                'user_id': user.id,
                'total': sum(x.unit_price*x.quantity for x in cart),
                'delivery_crew_id': None
            }
            order_serializer = OrderSerializer(data=order_details)
            if not order_serializer.is_valid():
                return Response(order_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            order_serializer.save()
            order = order_serializer.data
            
            order_item_details = [{
                'order_id': order['id'],
                'menuitem_id': obj.menuitem.id,
                'quantity': obj.quantity,
                'unit_price': obj.unit_price,
                'price': obj.unit_price * obj.quantity,
                } 
                for obj in cart]

            order_item_serializer = OrderItemSerializer(data=order_item_details, many=True)
            if order_item_serializer.is_valid():
               order_item_serializer.save()             
            
            cart.all().delete()

            return Response({"message": f"order created wtih {len(cart)} menu items from cart",
                             "order_details": order},
                             status=status.HTTP_201_CREATED)
        
class SingleOrderView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer

    def get_queryset(self):
        pk = self.kwargs.get('pk')
        query_set = self.queryset.filter(order_id=pk).all()
        if self.request.user.groups.filter(name='Manager').exists():
            return query_set
        elif self.request.user.groups.filter(name='Delivery Crew').exists():
            if query_set.first().order.delivery_crew == self.request.user:
                return query_set
            else:
                raise PermissionDenied() 
        else:
            if query_set.first().order.user == self.request.user:
                return query_set
            else:
                raise PermissionDenied()
    
    def patch(self, request, pk):
        if request.method == 'PATCH':
            user = request.user
            data = request.data

            if 'status' in data:
                if user.groups.filter(name='Delivery Crew').exists():
                    requested_order = Order.objects.filter(id=pk,
                                                           delivery_crew=user).first()
                    if data['status'].lower() in ['0', '1', 'true', 'false']:
                        return self.update_status(requested_order, 
                                           data={'status': data['status'].lower()})
                    else:
                        return Response({'message': 'invalid data format'}, status=status.HTTP_400_BAD_REQUEST)

                if user.groups.filter(name='Manager').exists():
                    requested_order = Order.objects.filter(id=pk).first()
                    if data['status'].lower() in ['0', '1', 'true', 'false']:
                        return self.update_status(requested_order, 
                                           data={'status': data['status'].lower()})
                    else:
                        return Response({'message': 'invalid data format'}, status=status.HTTP_400_BAD_REQUEST)
            
            if 'delivery_crew' in data:
                if user.groups.filter(name='Manager').exists():
                    requested_order = Order.objects.filter(id=pk).first()
                    delivery_crew_ids = [x.id for x in Group.objects.get(name='Delivery Crew').user_set.all()]
                    if int(data['delivery_crew']) in delivery_crew_ids:
                        return self.update_status(requested_order, 
                                                  data={'delivery_crew_id': int(data['delivery_crew'])})
                    return Response({'message': 'not a valid delivery crew id'}, status=status.HTTP_400_BAD_REQUEST)
                return Response(status=status.HTTP_403_FORBIDDEN)
            
            return Response({'message': 'no valid field to update'}, status=status.HTTP_400_BAD_REQUEST)
    
    def update_status(self, order, data):
        if isinstance(order, Order):
            serializer = OrderSerializer(order, data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)            
        return Response(status=status.HTTP_404_NOT_FOUND)