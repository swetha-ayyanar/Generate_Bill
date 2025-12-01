from django.db import models
from django.utils import timezone
from decimal import Decimal

class Product(models.Model):
    name = models.CharField(max_length=200)
    product_id = models.CharField(max_length=50, unique=True)
    available_stocks = models.IntegerField(default=0)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)  # unit price (OAT)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # percent

    def __str__(self):
        return f"{self.name} ({self.product_id})"

class Denomination(models.Model):
    value = models.IntegerField()  # e.g., 500, 100, 50, ...
    count = models.IntegerField(default=0)  # how many notes/coins of this denom are available

    class Meta:
        ordering = ['-value']  # highest first

    def __str__(self):
        return f"{self.value} x {self.count}"

class Purchase(models.Model):
    customer_email = models.EmailField()
    created_at = models.DateTimeField(default=timezone.now)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))  # sum of item totals without tax
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))  # subtotal + tax_total
    cash_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    change_given = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    # store computed change breakdown as JSON string for simplicity (denom:value->count)
    change_breakdown = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"Purchase #{self.id} - {self.customer_email} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    line_subtotal = models.DecimalField(max_digits=12, decimal_places=2)  # unit_price * qty
    line_tax = models.DecimalField(max_digits=12, decimal_places=2)  # tax amount for the line
    line_total = models.DecimalField(max_digits=12, decimal_places=2)  # subtotal + tax

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
