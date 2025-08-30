from django.contrib import admin
from .models import CustomUser, Category, Product, Rating, Cart, CartItem, Order, OrderItem

# admin.site.register(Category)
# admin.site.register(Product)
# admin.site.register(Rating)
# admin.site.register(Cart)
# admin.site.register(CartItem)
# admin.site.register(Order)
# admin.site.register(OrderItem)

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    ordering = ('email',)
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_staff', 'is_active', 'is_verified')
    list_filter = ('is_staff', 'is_active', 'is_verified')

    search_fields = ('email', 'username', 'first_name', 'last_name')
    readonly_fields = ('date_joined', 'last_login')

    # Fields to be used in displaying the User model.
    # These override the default fieldsets in UserAdmin
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': (
            'username', 'first_name', 'last_name',
            'address_line_1', 'address_line_2', 'city', 'postcode', 'country', 'mobile',
            'profile_picture',
        )}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    # Fields to be shown on the user creation page
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'username', 'first_name', 'last_name', 'password1', 'password2',
                'address_line_1', 'address_line_2', 'city', 'postcode', 'country', 'mobile',
                'profile_picture',
                'is_active', 'is_staff', 'is_superuser', 'is_verified',
            ),
        }),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

class RatingInline(admin.TabularInline):
    model = Rating
    extra = 0
    readonly_fields = ('user', 'rating', 'comment', 'created')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'old_price', 'new_price', 'stock', 'available', 'created', 'updated')
    list_filter = ('available', 'category', 'created', 'updated')
    list_editable = ('old_price', 'new_price', 'stock', 'available')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [RatingInline]

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0  

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at')
    inlines = [CartItemInline]

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'first_name', 'last_name', 'email', 'paid', 'address', 'status')
    list_filter = ('created_at', 'status', 'paid')
    search_fields = ('first_name', 'last_name', 'email')
    inlines = [OrderItemInline]

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'rating', 'created')
    list_filter = ('rating', 'created')