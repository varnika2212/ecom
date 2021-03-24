from django.conf import settings
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render,get_object_or_404,redirect
from .models import Item,OrderItem,Order, Address,Payment,Refund
from django.views.generic import ListView, DetailView,View
from django.utils import timezone
from .forms import CheckoutForm,RefundForm
import random
import string
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY #"sk_test_4eC39HqLyjWDarjtT1zdp7dc"
# `source` is obtained with Stripe.js; see https://stripe.com/docs/payments/accept-a-payment-charges#web-create-token


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + sring.digits,k=20))

# Create your views here.
def products(request):
    context={
             'items':Item.objects.all()
    }
    return render(request,'product.html',context)

def is_valid_form(values):
    valid=True
    for field in values:
        if field=='':
            valid=False
    return valid

class CheckoutView(View):
    def get(self,*args,**kwargs):
        form=CheckoutForm()
        context={
                'form':form
        }

        shipping_address_qs=Address.objects.filter(
                user=self.request.user,
                address_type='S',
                default=True
                )
        if shipping_address_qs.exists():
            context.update({'default_shipping_address':shipping_address_qs[0]})

        billing_address_qs=Address.objects.filter(
                user=self.request.user,
                address_type='B',
                default=True
                )
        if billing_address_qs.exists():
            context.update({'default_billing_address':billing_address_qs[0]})


        return render(self.request,'checkout.html',context)


    def post(self,*args,**kwargs):
        form=CheckoutForm(self.request.POST or None)
        try:
            order=Order.objects.get(user=self.request.user,ordered=False)
            if form.is_valid():
                use_default_shipping=form.cleaned_data.get('use_default_shipping')
                if use_default_shipping:
                    print("using default shipping address")
                    address_qs=Address.objects.filter(
                                user=self.request.user,
                                address_type='S',
                                default=True
                                )
                    if address_qs.exists():
                        shipping_address=address_qs[0]
                        order.shipping_address=shipping_address
                        order.save()
                    else:
                        messages.info(self.request,"no default shipping address")
                        return redirect('djecom_app:checkout')
                else:
                    print("user adding new information")
                    shipping_address1=form.cleaned_data.get('shipping_address')
                    shipping_address2=form.cleaned_data.get('shipping_address2')
                    shipping_country=form.cleaned_data.get('shipping_country')
                    shipping_zip=form.cleaned_data.get('shipping_zip')

                    if is_valid_form([shipping_address1,shipping_country,shipping_zip]):
                        shipping_address=Address(
                            user=self.request.user,
                            street_address=shipping_address1,
                            apartment_address=shipping_address2,
                            country=shipping_country,
                            zip=shipping_zip,
                            address_type='S'
                                )
                        shipping_address.save()
                        order.shipping_address=shipping_address
                        order.save()
                        set_default_shipping=form.cleaned_data.get('set_default_shipping')
                        if set_default_shipping:
                            shipping_address.default=True
                            shipping_address.save()
                    else:
                        message.info(self.request,"please fill valid information")

                use_default_billing=form.cleaned_data.get('use_default_billing')
                same_billing_address=form.cleaned_data.get('same_billing_address')
                if same_billing_address:
                    billing_address=shipping_address
                    billing_address.pk=None
                    billing_address.save()
                    billing_address.address_type='B'
                    billing_address.save()
                    order.billing_address=billing_address
                    order.save()
                elif use_default_billing:
                    print("using default billing address")
                    address_qs=Address.objects.filter(
                                user=self.request.user,
                                address_type='B',
                                default=True
                                )
                    if address_qs.exists():
                        billing_address=address_qs[0]
                        order.billing_address=billing_address
                        order.save()
                    else:
                        messages.info(self.request,"no default billing address")
                        return redirect('djecom_app:checkout')
                else:
                    print("user adding new information")
                    billing_address1=form.cleaned_data.get('billing_address')
                    billing_address2=form.cleaned_data.get('billing_address2')
                    billing_country=form.cleaned_data.get('billing_country')
                    billing_zip=form.cleaned_data.get('billing_zip')

                    if is_valid_form([billing_address1,billing_country,billing_zip]):
                        billing_address=Address(
                             user=self.request.user,
                            street_address=billing_address1,
                            apartment_address=billing_address2,
                            country=billing_country,
                            zip=billing_zip,
                            address_type='B'
                                )
                        billing_address.save()
                        order.billing_address=billing_address
                        order.save()
                        set_default_billing=form.cleaned_data.get('set_default_billing')
                        if set_default_billing:
                            billing_address.default=True
                            billing_address.save()
                    else:
                        message.info(self.request,"please fill valid information")


                payment_option=form.cleaned_data.get('payment_option')

                if payment_option=='S':
                    return redirect('djecom_app:payment',payment_option='stripe')
                elif payment_option=='P':
                    return redirect('djecom_app:payment',payment_option='paypal')
                else:
                    messages.error(self.request,"Failed Checout")
                    return redirect('djecom_app:checkout')
        except ObjectDoesNotExist:
            messages.error(self.request,"Invalid Payment Option!")
            return redirect("djecom_app:order_summary")

class PaymentView(View):
    def get(self,*args,**kwargs):
        order=Order.objects.get(user=self.request.user,ordered=False)
        context={
                 'order':order
        }
        return render(self.request,'payment.html',context)
    def post(self,*args,**kwargs):
        order=Order.objects.get(user=self.request.user,ordered=False)
        token=self.request.POST.get('stripeToken')
        amount=int(order.get_total()*100)

        try:
            charge=stripe.Charge.create(
            amount=amount, #in cents
            currency="usd",
            source=token
            )

            #create payment
            payment=Payment()
            payment.stripe_charge_id=charge['id']
            payment.user=self.request.user
            payment.amount=amount
            payment.save()

            order_items=order.items.all()
            order_items.update(ordered=True)
            for item in order_items:
                item.save()
            #assign payment to the order
            order.ordered=True
            order.payment= order.get_total()
            #assign ref code
            order.ref_code=create_ref_code()
            order.save()


            messages.success(self.request,"Order successfully placed")
            return redirect("/")

        except stripe.error.CardError as e:
             body=e.json_body
             err=body.get('error',{})
             messages.error(self.request,f"{err.get('message')}")
             return redirect("/")
        except stripe.error.RateLimitError as e:
             messages.error(self.request,"Rate Limit error")
             return redirect("/")
        except stripe.error.InvalidRequestError as e:
          # Invalid parameters were supplied to Stripe's API
            messages.error(self.request,"Invalid Rquest Error")
            return redirect("/")

        except stripe.error.AuthenticationError as e:
          # Authentication with Stripe's API failed
          # (maybe you changed API keys recently)
            messages.error(self.request,"Authentication Error")
            return redirect("/")

        except stripe.error.APIConnectionError as e:
          # Network communication with Stripe failed
            messages.error(self.request,"APIConnectionError")
            return redirect("/")

        except stripe.error.StripeError as e:
          # Display a very generic error to the user, and maybe send
          # yourself an email
            messages.error(self.request,"StripeError")
            return redirect("/")

        except Exception as e:
          # Send email to ourselves
            messages.error(self.request,"Serious error, we have been notified")
            return redirect("/")







class HomeView(ListView):
    model=Item
    paginate_by=10
    template_name='home.html'

def tshirts(request):
    context={
             'items':Item.objects.filter(label="T")
    }
    return render(request,'tshirts.html',context)

class OrderSummaryView(LoginRequiredMixin,View):

    @method_decorator(login_required)
    def get(self,*args,**kwargs):
        try:
            order=Order.objects.get(user=self.request.user,ordered=False)
            context = {
                'object': order
            }
            return render(self. request,'order_summary.html',context)
        except ObjectDoesNotExist:
            messages.error(self.request,"You don't have any active order!")
            return redirect("/")

class ItemDetailView(DetailView):
    model=Item
    template_name='product.html'

@login_required
def add_to_cart(request,slug):
    item=get_object_or_404(Item,slug=slug)
    order_item,created=OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False)
    order_qs=Order.objects.filter(user=request.user,ordered=False)
    if order_qs.exists():
        order=order_qs[0]
        #check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity+=1
            order_item.save()
            messages.info(request,"Item Quantity is updated in your cart")
            return redirect("djecom_app:order_summary")
        else:
            order.items.add(order_item)
            messages.info(request,"This Item is added to your cart")
            return redirect("djecom_app:order_summary")

    else:
        ordered_date = timezone.now()
        order=Order.objects.create(user=request.user,ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request,"This Item is added to your cart")
        return redirect("djecom_app:order_summary")

@login_required
def remove_from_cart(request,slug):
    item=get_object_or_404(Item,slug=slug)
    order_qs=Order.objects.filter(user=request.user,ordered=False)
    if order_qs.exists():
        order=order_qs[0]
        #check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item,created=OrderItem.objects.get_or_create(
                item=item,
                user=request.user,
                ordered=False)
            order.items.remove(order_item)
            messages.info(request,"This Item is removed from your cart")
            return redirect("djecom_app:order_summary")
        else:
            messages.info(request,"This Item is not in your cart")
            return redirect("djecom_app:products",slug=slug)
    else:
        messages.info(request,"You don't have an order")
        return redirect("djecom_app:products",slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "This item quantity was updated.")
            return redirect("djecom_app:order_summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("djecom_app:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("djecom_app:product", slug=slug)

class RequestRefundView(View):
    def get(self,*args,**kwargs):
        form=RefundForm()
        context={
                 'form':form
        }
        return render(self.request,"request_refund.html",context)
    def post(self,*args,**kwargs):
        form=RefundForm(self.request.POST)
        if form.is_valid():
            ref_code=form.cleaned_data.get('ref_code')
            message=form.cleaned_data.get('message')
            email=form.cleaned_data.get('email')
            #edit order
            try:
                order=Order.objects.get(ref_code=ref_code)
                order.refund_reuested=True
                order.save()

            #store the refund
                refund=Refund()
                refund.order=order
                refund.reason=message
                refund.email=email
                refund.save()

                messages.info(self.request,"Your request was received")
                return redirect("djecom_app:request_refund")

            except ObjectDoesNotExist:
                messages.info(self.request,"This order doesn't exist")
                return redirect("djecom_app:request_refund")
