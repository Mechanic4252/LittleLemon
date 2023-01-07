from django.shortcuts import render, get_object_or_404
from rest_framework import generics,exceptions, status, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import MenuItem, OrderItem, Cart, Order, Category
from .serializers import MenuItemSerializer, UserSerializer, OrderItemSerializer, CartSerializer, OrderSerializer, CategorySerializer
from .permissions import ManagerAndCustomerPermission, IsOnlyManagerPermission, IsOwnerPermission, IsOwnerAndManagerCustomerPermission
from django.contrib.auth.models import User, Group
from django.http import Http404
from django.db import transaction,models


class CategoryView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [ManagerAndCustomerPermission]

class UpdateCategoryView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [ManagerAndCustomerPermission]    

class MenuItemsView(generics.ListCreateAPIView, generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [ManagerAndCustomerPermission]

class RetrieveMenuItemsView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.select_related('category').all()
    serializer_class = MenuItemSerializer
    permission_classes = [ManagerAndCustomerPermission]
    

@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsOnlyManagerPermission])
def managersView(request, **kwargs):
    state = status.HTTP_400_BAD_REQUEST
    data = {'message': "error"}
    userId = kwargs.get('userId')

    if request.method == 'POST':
        username = request.data.get('username')
        user = get_object_or_404(User, username=username)
        managers = Group.objects.get(name='Manager')
        
        managers.user_set.add(user)
        data = {'message': 'ok'}
        state = status.HTTP_201_CREATED

    elif request.method == 'GET':
        managers = User.objects.filter(groups__name='Manager')
        many = True
        if userId:
            
            managers = get_object_or_404(managers, pk=userId)
            many = False
        serialized = UserSerializer(managers, many=many)
        data = serialized.data
        state = status.HTTP_200_OK

    elif request.method == 'DELETE':
        user = get_object_or_404(User, pk=userId)
        managers = Group.objects.get(name='Manager')
        managers.user_set.remove(user)
        data = {'message': 'ok'}
        state = status.HTTP_200_OK

    return Response(data, state)


class DeliveryCrewView( generics.ListCreateAPIView):
    queryset = User.objects.filter(groups__name='Delivery crew')
    serializer_class = UserSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        delivery = Group.objects.get(name='Delivery crew')
        delivery.user_set.add(user)

    def get_permissions(self):
        methods = ['GET', 'POST', 'DELETE']
        if self.request.method in methods:
            permission_classes = [IsOnlyManagerPermission]
        else:
            permission_classes = []
    
        return [permission() for permission in permission_classes]

class RemoveUserFromGroupView(generics.RetrieveDestroyAPIView):
    queryset = User.objects.filter(groups__name='Delivery crew')
    serializer_class = UserSerializer
    permission_classes = [IsOnlyManagerPermission]

    def destroy(self, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return Response(status=status.HTTP_404_NOT_FOUND)

        delivery_crew = Group.objects.get(name='Delivery crew')
        delivery_crew.user_set.remove(instance)

        return Response(status=status.HTTP_200_OK)

class CartView(generics.ListCreateAPIView, generics.DestroyAPIView):
    serializer_class = CartSerializer

    def get_queryset(self):
        return Cart.objects.select_related('menuitem').filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        cart = Cart.objects.all().filter(user=self.request.user)
        self.perform_destroy(cart)

        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET', 'POST'])
def OrdersView(request):
    
    if request.method == 'GET':
        orders = OrderItem.objects.all()
        if request.user.groups.filter(name='Manager').exists():
            order = orders
        if request.user.groups.filter(name='Delivery crew').exists():
            order = get_object_or_404(orders, delivery_crew = request.user)
            # order = order.filter(delivery_crew = request.user)
        if not request.user.groups.filter(name='Manager').exists() and not request.user.groups.filter(name='Delivery crew').exists():
            order = get_object_or_404(orders, user = request.user)
            # order = order.filter(user = request.user)
            
        serialized_data = OrderItemSerializer(order, many=True)
        data = serialized_data.data
        return Response(data)

    elif request.method == 'POST':
        # order = Order.objects.create(user=request.user, total=0.00)
        # data = {'user': request.user, 'total': 0.00}
        order = {"user":request.user.pk}
        serialized_order = OrderSerializer(data=order)
        serialized_order.is_valid(raise_exception=True)
        
        
        data = {"message": "failed"}
        state = status.HTTP_400_BAD_REQUEST

        cart = Cart.objects.all().filter(user=request.user)
        # sum_price = user_items.aggregate(total=sum('price'))
        F = models.F
        price_sum = cart.aggregate(total=models.Sum(F('unit_price') * F('quantity'), output_field=models.DecimalField()))
        print(price_sum)

        items = []

        with transaction.atomic():
            instance = serialized_order.save(total=price_sum.get('total', 0))

            for item in cart:
                # order_item = OrderItem(order, menuitem = item.menuitem, quantity=item.quantity, unit_price=item.unit_price, price=item.price)
                # print(item.menuitem.pk, item.quantity, item.unit_price, item.price, instance.pk)
                print(item.quantity, item.price)
                order_item = {"order": instance.pk, "menuitem": item.menuitem.pk, "quantity": item.quantity, "unit_price": item.unit_price, "price": item.price}
                items.append(order_item)
                # total += float(item.price)
            
            serialized_item = OrderItemSerializer(data=items, many=True)
            serialized_item.is_valid(raise_exception=True)
            serialized_item.save()
            cart.delete()
            data = serialized_item.data
            state = status.HTTP_201_CREATED
            
        return Response(serialized_item.data, status=state)


class OrderView(generics.RetrieveUpdateDestroyAPIView):
    # queryset = OrderItem.objects.filter()
    serializer_class = OrderSerializer
    # authentication_classes = [IsAuthenticated]
    permission_classes = [IsOwnerAndManagerCustomerPermission]

    def getAuthorization(self, request):
        manager = request.user.groups.filter(name='Manager').exists()
        staff = manager or request.user.groups.filter(name='Delivery crew').exists()
        return manager, staff

    def get_object(self):
        try:
            orderId = self.kwargs.get('orderId')
            # items = OrderItem.objects.all().filter(order=orderId)
            _, staff = self.getAuthorization(self.request)
            order = Order.objects.get(id=orderId)
            if not staff:
                order = get_object_or_404(order, user=self.request.user)
            return order
        except Order.DoesNotExist:
            raise Http404
    
    def put(self, request, *args, **kwargs):
        # order = self.get_object(orderId)
        isManager, staff = self.getAuthorization(request)
        if isManager or not staff:
            # serializer = OrderItemSerializer(order, data=kwargs)
            # serializer.is_valid(raise_exception=True)
            # serializer.save()
            return self.update(request, *args, **kwargs)

        return Response(status=status.HTTP_403_FORBIDDEN)


    def patch(self, request, *args, **kwargs):
        # if no OrderItem exists by this PK, raise a 404 error
        response = {}
        # orderId = kwargs.get('orderId')
        isManager, staff = self.getAuthorization(request)
        data = {}
        # order_item = get_object_or_404(OrderItem, pk=orderId)
        # order_item = self.get_object(orderId)
        if request.user.groups.filter(name="Delivery crew").exists():
            # this is the only field we want to update
            data = {"status": 1}
        if isManager or not staff: 
            # data_status = 
            # user = get_object_or_404(User, username='crew')
            data = kwargs

        if not data:
            return Response(status=status.HTTP_403_FORBIDDEN)
            
        return self.partial_update(request, *args, data)
        

    def delete(self, request, *args, **kwargs):
        isManager, _ = self.getAuthorization(request)
        if isManager:
            order = Order.objects.get(pk=kwargs.get('orderId'))
            self.perform_destroy(order)
            return Response(status=status.HTTP_204_NO_CONTENT)
            # return self.destroy(request, *args, **kwargs)

        return Response(status=status.HTTP_403_FORBIDDEN)



    





        

        









        



