import logging

import stripe
from fastapi import APIRouter, HTTPException, Request

from app.constants import STRIPE_ENDPOINT_SECRET, STRIPE_SECRET_KEY
from app.database.crud import (
    retrieve_practice_by_stripe_customer_id,
    update_practice_details,
)

stripe.api_key = STRIPE_SECRET_KEY
endpoint_secret = STRIPE_ENDPOINT_SECRET


router = APIRouter(prefix="/webhook", tags=["Stripe Webhooks"])

# initiates logger
log = logging.getLogger(__name__)


@router.post("/")
async def webhook_handler(request: Request):
    sig_header = request.headers.get("Stripe-Signature", None)
    if not sig_header:
        raise HTTPException(status_code=400, detail="Webhook signature missing")

    try:
        event = stripe.Webhook.construct_event(
            payload=await request.body(),
            sig_header=sig_header,
            secret=endpoint_secret,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Handle the event
    event_type = event.type
    data = event.data.object

    if event_type == "customer.subscription.updated":
        await handle_subscription_update(data)
    elif event_type == "checkout.session.completed":
        await handle_new_customer(data)

    return {"status": "success"}


async def handle_subscription_update(invoice_data):
    # get the stripe_customer_id
    customer_id = invoice_data.customer
    practice = retrieve_practice_by_stripe_customer_id(customer_id)

    # need to handle when a customer updates their subscription
    if invoice_data.plan.id != practice["stripe_plan_id"]:
        update_practice_details(practice_id=practice["_id"], stripe_plan_id=invoice_data.plan.id)

    # no need to handle when a customer cancels their subscription in the webhook
    # as login function will check if users subscription is active


async def handle_new_customer(new_customer_data):
    # if its a new customer then ? not sure for now as the code is already in place but not water tight
    pass
