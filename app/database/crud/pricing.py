# Pricing CRUD file
# -- Files must start with either create, retrieve, update, delete

from typing import Dict, List

from fastapi import HTTPException
from mongoengine import DoesNotExist

from app.database.schemas.pricing import Pricing


def retrieve_pricing(practice_id: str):
    try:
        pricing = Pricing.objects(practice_id=practice_id).only("treatment", "price")

        if pricing is None:
            return None

        pricing_list = []
        for price in pricing:
            price_dict = price.to_mongo().to_dict()
            del price_dict["_id"]
            pricing_list.append(price_dict)

        return pricing_list

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found") from None


def retrieve_price_list(practice_id: str):
    try:
        # Fetch pricing documents for the given practice_id
        pricing_docs = Pricing.objects(practice_id=practice_id).select_related()

        # If no documents are found, return an empty list instead of raising an exception
        if not pricing_docs:
            return []

        price_list = []
        for pricing in pricing_docs:
            pricing_dict = pricing.to_mongo().to_dict()
            pricing_dict["_id"] = str(pricing_dict["_id"])
            pricing_dict["practice_id"] = str(pricing_dict["practice_id"])
            price_list.append(pricing_dict)

        return price_list

    except Exception as e:
        # Handle any other exceptions that might occur
        raise HTTPException(status_code=500, detail=str(e)) from None


def update_price_list(price_list: List[Dict], practice_id: str):
    try:
        # Delete all existing records for this practice_id
        Pricing.objects(practice_id=practice_id).delete()

        if price_list:
            Pricing.objects.insert([Pricing(treatment=item["treatment"], price=item["price"], practice_id=practice_id) for item in price_list])

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Practice not found") from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
