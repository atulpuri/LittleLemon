from rest_framework import serializers 
from .models import MenuItem, Order, Cart, Category, OrderItem
from rest_framework.validators import UniqueTogetherValidator 
from django.contrib.auth.models import User, Group

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model= Group
        fields = ('id','name')

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id','title']

class MenuItemSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(write_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = MenuItem
        fields = ['id', 'title', 'price', 'featured', 'category', 'category_id']

class CartSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(write_only=True)
    user = UserSerializer(read_only=True)
    menuitem_id = serializers.IntegerField(write_only=True)
    menuitem = MenuItemSerializer(read_only=True)
    price = serializers.SerializerMethodField(method_name='calculate_price')

    def calculate_price(self, Cart):
        return Cart.unit_price * Cart.quantity

    class Meta:
        model = Cart
        fields = ['user', 'menuitem', 'quantity', 'unit_price', 'price', 'menuitem_id', 'user_id',]
        validators = [UniqueTogetherValidator(queryset = Cart.objects.all(),
                                              fields = ['user_id', 'menuitem_id']),
                        ]

class OrderSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(write_only=True)
    user = UserSerializer(read_only=True) 
    delivery_crew_id = serializers.IntegerField(write_only=True, allow_null=True)
    delivery_crew = UserSerializer(read_only=True) 

    class Meta:
        model = Order
        fields = ['id', 'user', 'delivery_crew', 'status', 'total', 'date', 'user_id', 'delivery_crew_id',]

class OrderItemSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(write_only=True)
    order = OrderSerializer(read_only=True)
    menuitem_id = serializers.IntegerField(write_only=True)
    menuitem = MenuItemSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['order', 'menuitem', 'quantity', 'unit_price', 'price', 'menuitem_id', 'order_id',]
        validators = [UniqueTogetherValidator(queryset = OrderItem.objects.all(),
                                              fields = ['order_id', 'menuitem_id']),
                        ]