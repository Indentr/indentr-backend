import stripe
from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from werkzeug.security import check_password_hash

from app.constants import (
    GRATIS_PASSWORD,
    STRIPE_SECRET_KEY,
    TRIAGE_MAIL,
    TRIAGE_MAIL_PASSWORD,
)
from app.database.crud.custom_prompt import create_custom_prompt
from app.database.crud.letter_config import create_letter_config
from app.database.crud.practice import (
    create_new_practice,
    retrieve_practice_by_email,
    retrieve_practice_by_id,
)
from app.database.crud.triage_settings import create_triage_settings
from app.database.crud.user import (
    create_new_user,
    retrieve_user_by_email,
    save_password_reset_token,
    update_user_details,
)
from app.middleware.jwt import JWTBearer, decodeJWT, sign_reset_password_token, signJWT
from app.models.login import (
    CheckEmail,
    ResetPassword,
    UserLoginRequest,
    UserRegisterRequest,
    UserResetPasswordRequest,
)
from app.services.email import generate_password_reset_email, send_email
from app.utils.new_account_setup import (
    insert_instruction_triages,
    insert_welcome_consent_letter,
)

stripe.api_key = STRIPE_SECRET_KEY

router = APIRouter(prefix="/auth", tags=["Authorisation"])


@router.post("/login/")
def post_user_login(body: UserLoginRequest):
    """
    This route handles user login requests. It expects a `UserLoginRequest` object
    as the request body, containing the user's email and password. The `check_user`
    function is invoked to validate the user's credentials against the database.
    If the user's credentials are valid, the `signJWT` function generates an access
    token, which is then returned in the response.
    """
    try:
        user_document = retrieve_user_by_email(body.email.lower())

        if not user_document or not check_password_hash(user_document["password"], body.password):
            raise HTTPException(status_code=403, detail="Email or password is incorrect")

        user_id = str(user_document["_id"])
        practice_id = str(user_document["practice_id"])
        practice = retrieve_practice_by_id(practice_id)

        if "gratis_password" in practice and practice["gratis_password"] == GRATIS_PASSWORD:
            return signJWT(user_id, practice_id)

        if "stripe_customer_id" not in practice:
            raise HTTPException(status_code=403, detail="No active subscription found")

        customer = stripe.Customer.retrieve(practice["stripe_customer_id"], expand=["subscriptions.data"])
        subscriptions = customer.subscriptions.data
        has_active_subscription = any(sub.status == "active" for sub in subscriptions)
        has_active_trial_subscription = next((sub for sub in subscriptions if sub.status == "trialing"), None)

        if has_active_subscription or has_active_trial_subscription:
            return signJWT(user_id, practice_id)
        else:
            raise HTTPException(status_code=403, detail="Your subscription is inactive. Please update your billing information.")

    except HTTPException as e:
        raise e


@router.post("/register/")
def post_user_registration(body: UserRegisterRequest):
    """
    This route handles user registration requests. It expects a `UserRegisterRequest`
    object as the request body, containing the user's name, email, and password.
    The route first checks if the provided email is already in use. If the email is
    available, it securely hashes the password and creates a new user in the database.
    """

    try:
        try:
            # Attempt to retrieve the user by email
            existing_user = retrieve_user_by_email(body.email.lower())
        except HTTPException as e:
            # Handle the 404 exception if user is not found
            if e.status_code == 404:
                existing_user = None
            else:
                raise

        # Check if the email already exists
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already in use")

        practice_id = create_new_practice(
            body.practice_name,
            body.practice_email.lower(),
            body.practice_url,
            body.address,
            body.phone,
            body.stripe_customer_id,
            gratis_password=body.gratis_password,
        )

        new_user = create_new_user(body.name, body.email.lower(), body.password, practice_id, "Owner")
        create_letter_config(practice_id)
        create_triage_settings(practice_id)
        create_custom_prompt(
            new_user["_id"],
            new_user["practice_id"],
            "Dental consultation",
            "Convert the dental dictation transcript into professional, concise but comprehensive dental notes for patient record inclusion. include all relevant sections from the example (if nothing is mentioned then put n/a for the section.)"
            "<p></p><p><strong>Dental Consultation Note</strong></p><p>Request for Appointment (RFA):</p><p></p><p><strong>Purpose</strong>: Exam/Consultation</p><p>Nurse Information:</p><ul><li><p><strong>Name</strong>: n/a</p></li><li><p><strong>Notes</strong>: n/a</p></li></ul><p></p><p><strong>Chief Complaint / Request for Appointment (CO/RFA): </strong>n/a</p><p></p><p><strong>Medical History</strong></p><ul><li><p><strong>Conditions</strong>: Fit and well; not pregnant</p></li><li><p><strong>Medications</strong>: n/a</p></li><li><p><strong>Allergies</strong>: n/a</p></li></ul><p></p><p><strong>Dental History</strong></p><ul><li><p><strong>Hygiene Practices:</strong> n/a</p></li><li><p>Brushes _ times daily (Manual/Electric)</p></li><li><p>Interdental Cleaning: Floss/Tepe/None; Frequency: _ times per day/week/month/on occasion</p></li></ul><p></p><p><strong>Orthodontic History</strong></p><ul><li><p>Previous orthodontic treatment: n/a</p></li><li><p>Retainers: n/a</p></li><li><p>Fixed orthodontic retainers (Upper/Lower): n/a</p></li><li><p>Removable orthodontic retainers (Hawley/Essix), worn daily/nightly: n/a</p></li><li><p>Current orthodontic treatment (Fixed appliance/Removable appliance/Aligners): n/a</p></li><li><p>Referred for orthodontic consultation: n/a</p></li></ul><p></p><p><strong>Implant History</strong></p><ul><li><p>Previous implants: Yes/No</p></li><li><p>Location: In the UK</p></li><li><p>Years ago: X years</p></li><li><p>By: XXX</p></li></ul><p></p><p><strong>Social History</strong></p><ul><li><p>Tobacco Use: Non-smoker/Smoker, cigarettes/day, Smoking duration: years, E-cigarette usage</p></li><li><p>Alcohol Consumption: Drinks _ units/week or Does not drink</p></li><li><p>Occupation: n/a</p></li><li><p>Stress Levels: n/a</p></li><li><p>Habits: n/a</p></li><li><p>Clenching/Grinding</p></li><li><p>Other: _</p></li><li><p>Dietary Habits: n/a</p></li><li><p>Frequency of snacking</p></li><li><p>Sugar and acid intake details</p></li></ul><p></p><p><strong>Examination</strong></p><p>n/a</p><p></p><p><strong>Extraoral Examination (E/O)</strong></p><ul><li><p>TMJ, lymph nodes, muscles of mastication (MOM), facial symmetry</p></li></ul><p></p><p><strong>Intraoral Examination (I/O)</strong></p><ul><li><p>Soft tissues: Oral mucosa, tongue, palate, tonsils</p></li><li><p>Oral Hygiene (OH): Poor/Moderate/Good</p></li><li><p>Presence of calculus and plaque deposits</p></li><li><p>Teeth:</p></li><li><p>Incisor and molar relationships</p></li><li><p>Overjet, overbite, lateral excursions</p></li><li><p>Tooth Surface Loss (TSL): Generalized/Localized</p></li><li><p>Abrasion cavities, attrition, erosion</p></li><li><p>Wisdom teeth status: Upper/Lower 8s (Functional/Impacted/Unerupted)</p></li><li><p>Radiographic Findings:</p></li><li><p>Bitewing (BW) and periapical (PA) radiographs: Caries and bone level screening</p></li><li><p>OPG: Condyles, sinuses, bone levels</p></li></ul><p></p><p><strong>Diagnoses</strong></p><ul><li><p>Soft tissue conditions</p></li><li><p>Caries (Enamel/Dentine/Pulp)</p></li><li><p>Periodontal status: Health, Periodontitis (Localized/Generalized, Stage, Grade)</p></li><li><p>Risk factors for dental diseases</p></li></ul><p></p><p><strong>Treatment Plan</strong></p><ul><li><p>Oral Health Education: Brushing technique, flossing, use of interdental brushes</p></li><li><p>Specific products recommended (e.g., high fluoride toothpaste, mouthwash)</p></li><li><p>Periodontal treatment plan and follow-up</p></li><li><p>Dietary advice</p></li><li><p>Referrals for specialist treatment</p></li><li><p>Restorative options for TSL</p></li><li><p>Tooth whitening and cosmetic treatments</p></li><li><p>Emergency procedures and extractions</p></li><li><p>Possible medical interventions affecting dental care (e.g., medications affecting salivation, manual dexterity issues)</p></li></ul><p></p><p><strong>Next Steps</strong></p><ul><li><p>Follow-up Appointments: n/a</p></li><li><p>Approximate Treatment Cost: Subject to changes based on detailed review</p></li><li><p>Patient's Consent: Obtained for clinical photos and use in educational/marketing materials</p></li><li><p>Agreed Care Plan: n/a</p></li><li><p>Prescriptions, dietary advice, smoking cessation options provided</p></li></ul><p></p>",
        )
        create_custom_prompt(
            new_user["_id"],
            new_user["practice_id"],
            "Record consultation",
            "Convert the following dental consultation transcript into a concise conversation transcript between the dentist and patient. Format each line clearly as 'Dentist' or 'Patient' ",
        )
        insert_welcome_consent_letter(body.name, body.email.lower(), body.address)
        insert_instruction_triages(practice_id)

        return signJWT(new_user["_id"], new_user["practice_id"])

    except HTTPException as e:
        raise e


@router.post("/check-email/")
def checks_if_email_in_use(body: CheckEmail):
    """
    This route checks to see if the user is able to signup with an email by checking there isn't another account with the same email
    """

    try:
        try:
            # Attempt to retrieve the user by email
            existing_user = retrieve_user_by_email(body.email.lower())
        except HTTPException as e:
            # Handle the 404 exception if user is not found
            if e.status_code == 404:
                existing_user = None
            else:
                raise

        # Check if the email already exists
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already in use")

        return {"valid": True}

    except HTTPException as e:
        raise e


@router.post("/check-practice-email/")
def checks_if_practice_email_in_use(body: CheckEmail):
    """
    This route checks to see if the user is able to signup with an email by checking there isn't another account with the same email
    """

    try:
        try:
            # Attempt to retrieve the user by email
            existing_practice = retrieve_practice_by_email(body.email.lower())
        except HTTPException as e:
            # Handle the 404 exception if user is not found
            if e.status_code == 404:
                existing_practice = None
            else:
                raise

        # Check if the email already exists
        if existing_practice:
            raise HTTPException(status_code=400, detail="Email already in use")

        return {"valid": True}

    except HTTPException as e:
        raise e


@router.get("/user/")
def authenticate_user(access_token=Depends(JWTBearer())):
    """
    Checks if `access_token` is valid and then signs a new JWT based on the user_id
    """

    token = decodeJWT(access_token)
    user_id = token["user_id"]
    practice_id = token["user_id"]

    return signJWT(user_id, practice_id)


@router.post("/send-reset-password-email/")
def sent_reset_password_email(body: UserResetPasswordRequest):
    """
    This route handles when a user needs to reset their password.
    It will create a jwt reset token.
    This token will be saved to the user's document in mongo.
    It will then send an email containing the link with the jwt reset token so it can then be validated with the one in the DB.
    """
    try:
        user_document = retrieve_user_by_email(body.email.lower())

        if not user_document:
            raise HTTPException(status_code=403, detail="No account associated with that email")

        user_id = str(user_document["_id"])
        reset_token = sign_reset_password_token(user_id)
        save_password_reset_token(user_id, str(reset_token))
        email = generate_password_reset_email(user_document["email"], reset_token)
        send_email(subject="Reset password", msg=email, sender=TRIAGE_MAIL, recipient=user_document["email"], password=TRIAGE_MAIL_PASSWORD)
        return "Email sent successfully!"

    except HTTPException as e:
        raise e


@router.post("/reset-password/")
async def edit_user_field(body: ResetPassword):
    """
    Edits the users name or email or password depending on what gets sent in the body.
    """

    try:
        payload = decodeJWT(body.reset_token)
        if payload is None or payload.get("action") != "reset_password":
            raise HTTPException(status_code=401, detail="Password reset token is invalid or expired")

        user_id = payload["user_id"]
        password = body.password

        # Update the user's password in MongoDB
        update_user_details(user_id=user_id, password=password)
        save_password_reset_token(user_id, "")
        return {"message": "Password updated successfully!"}

    except HTTPException as e:
        raise e  # Reraise the HTTPException
