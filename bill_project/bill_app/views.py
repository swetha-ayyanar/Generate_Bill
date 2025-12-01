from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from .models import Product, Denomination, Purchase, PurchaseItem
from decimal import Decimal, ROUND_HALF_UP
from django.views.decorators.http import require_http_methods
from django.db import transaction
from bill_app import templates

def billing_page(request):
    """
    Render the billing form. Denominations are passed to show available counts.
    """
    denominations = Denomination.objects.all()
    return render(request, 'billing_app/billing_page.html', {"denominations": denominations})


def get_products(request):
    products = Product.objects.all().values(
        'id',
        'name',
        'product_id',
        'price_per_unit',
        'tax_percentage',
        'available_stocks'
    )
    print(products)
    return JsonResponse(list(products),safe=False)


def _to_decimal(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

@require_http_methods(["POST"])
@transaction.atomic
def generate_bill(request):
    """
    Accept POST with:
      - customer_email
      - items: product_id[], qty[] (these are product PKs)
      - denominations counts (we will not rely on posted counts to update shop; denominations already stored in DB)
      - cash_paid
    Calculation:
      - compute line totals = qty * price
      - compute tax per line = line_subtotal * tax_percentage / 100
      - subtotal, tax_total, total
      - compute change = cash_paid - total
      - compute change breakdown using available Denomination objects (greedy with available counts)
      - update Denomination counts by subtracting the notes dispensed
      - create Purchase and PurchaseItems
    """
    data = request.POST
    customer_email = data.get('customer_email', '').strip()
    if not customer_email:
        return HttpResponseBadRequest("Customer email required")

    # items are sent with names product_pk[] and qty[] via form; handle both single and multiple
    product_pks = request.POST.getlist('product[]')
    qtys = request.POST.getlist('qty[]')

    if not product_pks or not qtys or len(product_pks) != len(qtys):
        return HttpResponseBadRequest("Invalid items")

    # parse cash paid
    try:
        cash_paid = _to_decimal(request.POST.get('cash_paid', '0') or '0')
    except:
        cash_paid = Decimal('0.00')

    subtotal = Decimal('0.00')
    tax_total = Decimal('0.00')
    items_data = []

    for pk_str, qty_str in zip(product_pks, qtys):
        try:
            pk = int(pk_str)
            qty = int(qty_str)
        except:
            return HttpResponseBadRequest("Invalid product or quantity")
        product = get_object_or_404(Product, pk=pk)
        unit_price = _to_decimal(product.price_per_unit)
        line_subtotal = (unit_price * qty).quantize(Decimal('0.01'))
        line_tax = (line_subtotal * Decimal(product.tax_percentage) / Decimal(100)).quantize(Decimal('0.01'))
        line_total = (line_subtotal + line_tax).quantize(Decimal('0.01'))
        subtotal += line_subtotal
        tax_total += line_tax
        items_data.append({
            'product': product,
            'quantity': qty,
            'unit_price': unit_price,
            'tax_percentage': Decimal(product.tax_percentage),
            'line_subtotal': line_subtotal,
            'line_tax': line_tax,
            'line_total': line_total
        })

    total = (subtotal + tax_total).quantize(Decimal('0.01'))
    change = (cash_paid - total).quantize(Decimal('0.01'))

    # Build change breakdown using available denominations (greedy)
    change_amount = change
    change_breakdown = {}
    dispensed = {}
    if change_amount > 0:
        denominations = list(Denomination.objects.order_by('-value'))  # highest to lowest
        remaining = int(change_amount)  # convert to integer rupee/units — assumes currency without paise for denominations given
        # If currency supports paise (decimals), we'd need coin denominations with decimals. Here denominations are integers.
        for denom in denominations:
            if remaining <= 0:
                break
            denom_value = denom.value
            max_needed = remaining // denom_value
            give = min(max_needed, denom.count)
            if give > 0:
                dispensed[denom_value] = give
                remaining -= give * denom_value

        if remaining != 0:
            # Not possible to make exact change with available denominations
            # We will not modify denominations; record that exact change couldn't be made
            change_breakdown = {'error': 'Cannot make exact change with available denominations', 'remaining_unable': remaining}
        else:
            # success, update denom counts
            for val, cnt in dispensed.items():
                denom_obj = Denomination.objects.get(value=val)
                denom_obj.count = denom_obj.count - cnt
                denom_obj.save()
            change_breakdown = dispensed
    else:
        # No change to give
        change_breakdown = {}

    # Save Purchase and items
    purchase = Purchase.objects.create(
        customer_email=customer_email,
        subtotal=subtotal,
        tax_total=tax_total,
        total=total,
        cash_paid=cash_paid,
        change_given=change if change > 0 else Decimal('0.00'),
        change_breakdown=change_breakdown
    )
    for it in items_data:
        PurchaseItem.objects.create(
            purchase=purchase,
            product=it['product'],
            quantity=it['quantity'],
            unit_price=it['unit_price'],
            tax_percentage=it['tax_percentage'],
            line_subtotal=it['line_subtotal'],
            line_tax=it['line_tax'],
            line_total=it['line_total'],
        )
        # reduce product stock
        p = it['product']
        p.available_stocks = max(0, p.available_stocks - it['quantity'])
        p.save()

    # Render invoice page
    return render(request, 'billing_app/invoice.html', {
        'purchase': purchase,
        'items': purchase.items.all(),
        'change_breakdown': change_breakdown,
    })

def history(request):
    """
    Show purchases. If customer_email provided as ?email=..., filter.
    """
    email = request.GET.get('email', '').strip()
    if email:
        purchases = Purchase.objects.filter(customer_email=email).order_by('-created_at')
    else:
        purchases = Purchase.objects.all().order_by('-created_at')
    return render(request, 'billing_app/history.html', {'purchases': purchases, 'email': email})

def purchase_detail(request, pk):
    purchase = get_object_or_404(Purchase, pk=pk)
    return render(request, 'billing_app/purchase_detail.html', {'purchase': purchase, 'items': purchase.items.all()})
