from datetime import datetime

import stripe

from app.constants import STRIPE_SECRET_KEY

stripe.api_key = STRIPE_SECRET_KEY


async def retrieve_stripe_customer_details(stripe_customer_id: str):
    customer = stripe.Customer.retrieve(stripe_customer_id, expand=["subscriptions.data"])

    # get the active subscription and plan details
    subscriptions = customer.subscriptions.data

    active_subscription = next((sub for sub in subscriptions if sub.status == "active"), None)
    trial_subscription = next((sub for sub in subscriptions if sub.status == "trialing"), None)

    plan_name = "Unkown"
    plan = None
    allowed_audio_note_hours = 0
    allowed_consent_letters = 0

    if active_subscription:
        plan = active_subscription.plan
    elif trial_subscription:
        plan = trial_subscription.plan

    if plan is not None:
        plan_name = plan.metadata.nickname
        allowed_audio_note_hours = plan.metadata.allowed_audio_note_hours
        allowed_consent_letters = plan.metadata.allowed_consent_letters

    # Retrieve the number of letters created in the current billing cycle
    start_date = (
        datetime.fromtimestamp(active_subscription.current_period_start)
        if active_subscription
        else (datetime.fromtimestamp(trial_subscription.current_period_start) if trial_subscription else None)
    )
    end_date = (
        datetime.fromtimestamp(active_subscription.current_period_end)
        if active_subscription
        else (datetime.fromtimestamp(trial_subscription.current_period_end) if trial_subscription else None)
    )

    return {
        "active_subscription": active_subscription,
        "trial_subscription": trial_subscription,
        "plan_name": plan_name,
        "allowed_audio_note_hours": allowed_audio_note_hours,
        "allowed_consent_letters": allowed_consent_letters,
        "start_date": start_date,
        "end_date": end_date,
    }
