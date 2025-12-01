from django.contrib import admin
from .models import Product, Denomination, Purchase, PurchaseItem

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_id', 'available_stocks', 'price_per_unit', 'tax_percentage')
    search_fields = ('name', 'product_id')

@admin.register(Denomination)
class DenominationAdmin(admin.ModelAdmin):
    list_display = ('value', 'count')
    ordering = ('-value',)

class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    readonly_fields = ('product', 'quantity', 'unit_price', 'tax_percentage', 'line_subtotal', 'line_tax', 'line_total')
    can_delete = False
    extra = 0

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_email', 'created_at', 'total', 'cash_paid', 'change_given')
    inlines = [PurchaseItemInline]
