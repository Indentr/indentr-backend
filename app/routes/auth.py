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
            "Dental note",
            "Convert the dental dictation transcript into professional, concise but comprehensive dental notes for patient record inclusion.",
            "<p></p>",
        )
        create_custom_prompt(
            new_user["_id"],
            new_user["practice_id"],
            "Dental consultation",
            "Convert the transcript into professional, concise but comprehensive dental consultation notes for patient record inclusion. Include all relevant sections from the example. If nothing is mentioned then put n/a for the section.",
            """<p><strong><span style="font-family: Arial, sans-serif">Dental Consultation Note</span></strong></p><p></p><p><strong><span style="font-family: Arial, sans-serif">Request for Appointment (RFA):</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Purpose</span><strong><span style="font-family: Arial, sans-serif">:</span></strong><span style="font-family: Arial, sans-serif"> Exam/Consultation</span></p></li></ul><p><br><strong><span style="font-family: Arial, sans-serif">Nurse Information:</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Name</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p></li><li><p><span style="font-family: Arial, sans-serif">Notes</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p></li></ul><p></p><p><strong><span style="font-family: Arial, sans-serif">Chief Complaint / Request for Appointment (CO/RFA):</span></strong></p><p><br></p><p><strong><span style="font-family: Arial, sans-serif">Medical History</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Conditions</span><strong><span style="font-family: Arial, sans-serif">:</span></strong><span style="font-family: Arial, sans-serif"> Fit and well; not pregnant</span></p></li><li><p><span style="font-family: Arial, sans-serif">Medications</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p></li><li><p><span style="font-family: Arial, sans-serif">Allergies</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p></li></ul><p><br></p><p><strong><span style="font-family: Arial, sans-serif">Dental History</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Hygiene Practices</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Brushes _ times daily (Manual/Electric)</span></p></li><li><p><span style="font-family: Arial, sans-serif">Interdental Cleaning: Floss/Tepe/None; Frequency: _ times per day/week/month/on occasion</span></p></li></ul></li></ul><p></p><ul><li><p><span style="font-family: Arial, sans-serif">Orthodontic History</span></p><ul><li><p><span style="font-family: Arial, sans-serif">Previous orthodontic treatment</span></p></li><li><p><span style="font-family: Arial, sans-serif">Retainers:</span></p></li><li><p><span style="font-family: Arial, sans-serif">Fixed orthodontic retainers (Upper/Lower)</span></p></li><li><p><span style="font-family: Arial, sans-serif">Removable orthodontic retainers (Hawley/Essix), worn daily/nightly</span></p></li><li><p><span style="font-family: Arial, sans-serif">Current orthodontic treatment (Fixed appliance/Removable appliance/Aligners)</span></p></li><li><p><span style="font-family: Arial, sans-serif">Referred for orthodontic consultation</span></p></li></ul></li></ul><p></p><ul><li><p><span style="font-family: Arial, sans-serif">Implant History</span></p><ul><li><p><span style="font-family: Arial, sans-serif">Previous implants: Yes/No</span></p></li><li><p><span style="font-family: Arial, sans-serif">Location: In the UK</span></p></li><li><p><span style="font-family: Arial, sans-serif">Years ago: X years</span></p></li><li><p><span style="font-family: Arial, sans-serif">By: XXX</span></p></li></ul></li></ul><p><br></p><p><strong><span style="font-family: Arial, sans-serif">Social History</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Tobacco Use</span><strong><span style="font-family: Arial, sans-serif">:</span></strong><span style="font-family: Arial, sans-serif"> Non-smoker/Smoker, </span><em><span style="font-family: Arial, sans-serif">cigarettes/day, Smoking duration: </span></em><span style="font-family: Arial, sans-serif">years, E-cigarette usage</span></p></li><li><p><span style="font-family: Arial, sans-serif">Alcohol Consumption</span><strong><span style="font-family: Arial, sans-serif">:</span></strong><span style="font-family: Arial, sans-serif"> Drinks _ units/week or Does not drink</span></p></li><li><p><span style="font-family: Arial, sans-serif">Occupation</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p></li><li><p><span style="font-family: Arial, sans-serif">Stress Levels</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p></li><li><p><span style="font-family: Arial, sans-serif">Habits</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Clenching/Grinding</span></p></li><li><p><span style="font-family: Arial, sans-serif">Other: _</span></p></li></ul></li><li><p><span style="font-family: Arial, sans-serif">Dietary Habits</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Frequency of snacking</span></p></li><li><p><span style="font-family: Arial, sans-serif">Sugar and acid intake details</span></p></li></ul></li></ul><p></p><p></p><p><strong><span style="font-family: Arial, sans-serif">Examination</span></strong></p><p><span style="font-family: Arial, sans-serif">Extraoral Examination (E/O)</span></p><ul><li><p><span style="font-family: Arial, sans-serif">TMJ, lymph nodes, muscles of mastication (MOM), facial symmetry</span></p></li></ul><p><br></p><p><span style="font-family: Arial, sans-serif">Intraoral Examination (I/O)</span></p><ul><li><p><span style="font-family: Arial, sans-serif">Soft tissues: Oral mucosa, tongue, palate, tonsils</span></p></li><li><p><span style="font-family: Arial, sans-serif">Oral Hygiene (OH): Poor/Moderate/Good</span></p></li><li><p><span style="font-family: Arial, sans-serif">Presence of calculus and plaque deposits</span></p></li><li><p><span style="font-family: Arial, sans-serif">Teeth:</span></p><ul><li><p><span style="font-family: Arial, sans-serif">Incisor and molar relationships</span></p></li><li><p><span style="font-family: Arial, sans-serif">Overjet, overbite, lateral excursions</span></p></li><li><p><span style="font-family: Arial, sans-serif">Tooth Surface Loss (TSL): Generalized/Localized</span></p></li><li><p><span style="font-family: Arial, sans-serif">Abrasion cavities, attrition, erosion</span></p></li><li><p><span style="font-family: Arial, sans-serif">Wisdom teeth status: Upper/Lower 8s (Functional/Impacted/Unerupted)</span></p></li></ul></li><li><p><span style="font-family: Arial, sans-serif">Radiographic Findings:</span></p><ul><li><p><span style="font-family: Arial, sans-serif">Bitewing (BW) and periapical (PA) radiographs: Caries and bone level screening</span></p></li><li><p><span style="font-family: Arial, sans-serif">OPG: Condyles, sinuses, bone levels</span></p></li></ul></li></ul><p><br><strong><span style="font-family: Arial, sans-serif">Diagnoses</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Soft tissue conditions</span></p></li><li><p><span style="font-family: Arial, sans-serif">Caries (Enamel/Dentine/Pulp)</span></p></li><li><p><span style="font-family: Arial, sans-serif">Periodontal status: Health, Periodontitis (Localized/Generalized, Stage, Grade)</span></p></li><li><p><span style="font-family: Arial, sans-serif">Risk factors for dental diseases</span></p></li></ul><p><br><strong><span style="font-family: Arial, sans-serif">Treatment Plan</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Oral Health Education: Brushing technique, flossing, use of interdental brushes</span></p></li><li><p><span style="font-family: Arial, sans-serif">Specific products recommended (e.g., high fluoride toothpaste, mouthwash)</span></p></li><li><p><span style="font-family: Arial, sans-serif">Periodontal treatment plan and follow-up</span></p></li><li><p><span style="font-family: Arial, sans-serif">Dietary advice</span></p></li><li><p><span style="font-family: Arial, sans-serif">Referrals for specialist treatment</span></p></li><li><p><span style="font-family: Arial, sans-serif">Restorative options for TSL</span></p></li><li><p><span style="font-family: Arial, sans-serif">Tooth whitening and cosmetic treatments</span></p></li><li><p><span style="font-family: Arial, sans-serif">Emergency procedures and extractions</span></p></li><li><p><span style="font-family: Arial, sans-serif">Possible medical interventions affecting dental care (e.g., medications affecting salivation, manual dexterity issues)</span></p></li></ul><p><br><strong><span style="font-family: Arial, sans-serif">Next Steps</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Follow-up Appointments</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p></li><li><p><span style="font-family: Arial, sans-serif">Approximate Treatment Cost</span><strong><span style="font-family: Arial, sans-serif">:</span></strong><span style="font-family: Arial, sans-serif"> Subject to changes based on detailed review</span></p></li><li><p><span style="font-family: Arial, sans-serif">Patient's Consent</span><strong><span style="font-family: Arial, sans-serif">:</span></strong><span style="font-family: Arial, sans-serif"> Obtained for clinical photos and use in educational/marketing materials</span></p></li><li><p><span style="font-family: Arial, sans-serif">Agreed Care Plan</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p></li><li><p><span style="font-family: Arial, sans-serif">Prescriptions, dietary advice, smoking cessation options provided</span></p></li></ul><p><br></p>""",
        )
        create_custom_prompt(
            new_user["_id"],
            new_user["practice_id"],
            "Child dental consultation",
            "Convert the transcript into professional, concise but comprehensive child dental consultation notes for patient record inclusion. Include all relevant sections from the example. If nothing is mentioned then put n/a for the section.",
            """<p><strong><span style="font-family: Arial, sans-serif">Child Dental Consultation Note</span></strong></p><p><br><strong><span style="font-family: Arial, sans-serif">Nurse Information:</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Name</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p></li><li><p><span style="font-family: Arial, sans-serif">Notes:</span></p></li></ul><p><br><strong><span style="font-family: Arial, sans-serif">Chief Complaint (CO):</span></strong></p><p></p><p><strong><span style="font-family: Arial, sans-serif">Medical History (MH):</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">General Health</span><strong><span style="font-family: Arial, sans-serif">:</span></strong><span style="font-family: Arial, sans-serif"> Fit and well</span></p></li><li><p><span style="font-family: Arial, sans-serif">Medications</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p></li><li><p><span style="font-family: Arial, sans-serif">Allergies</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p></li></ul><p><br><strong><span style="font-family: Arial, sans-serif">Dental History (DH)</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Hygiene</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Brushes _ times daily (Manual/Electric)</span></p></li><li><p><span style="font-family: Arial, sans-serif">Interdental Aids:</span></p></li><li><p><span style="font-family: Arial, sans-serif">Supervision: Supervised/Unsupervised</span></p></li></ul></li><li><p><span style="font-family: Arial, sans-serif">Orthodontic History</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">History of orthodontics</span></p></li><li><p><span style="font-family: Arial, sans-serif">Retainers:</span></p><ul><li><p><span style="font-family: Arial, sans-serif">Fixed ortho retainers (Upper/Lower)</span></p></li><li><p><span style="font-family: Arial, sans-serif">Removable ortho retainers (Hawley/Essix), worn daily/nightly</span></p></li></ul></li></ul></li><li><p><span style="font-family: Arial, sans-serif">Currently undergoing orthodontic treatment (Fixed appliance)</span></p></li><li><p><span style="font-family: Arial, sans-serif">Referred for further orthodontics</span></p></li></ul><p><br></p><p><strong><span style="font-family: Arial, sans-serif">Social History (SH)</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Accompanied By</span><strong><span style="font-family: Arial, sans-serif">:</span></strong><span style="font-family: Arial, sans-serif"> Mother/Father/Siblings</span></p></li><li><p><span style="font-family: Arial, sans-serif">Smoking</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p></li><li><p><span style="font-family: Arial, sans-serif">Alcohol</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p></li><li><p><span style="font-family: Arial, sans-serif">School</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p></li><li><p><span style="font-family: Arial, sans-serif">Stress</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p></li></ul><p><br><strong><span style="font-family: Arial, sans-serif">Habits</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Clenching/Grinding/Other</span></p></li><li><p><span style="font-family: Arial, sans-serif">Reported by: Parent/Sibling/Previous Dentist</span></p></li></ul><p><br><strong><span style="font-family: Arial, sans-serif">Diet</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Frequency of Snacking:</span></p></li><li><p><span style="font-family: Arial, sans-serif">Sugar Intake:</span></p></li><li><p><span style="font-family: Arial, sans-serif">Acid Intake</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p></li><li><p><span style="font-family: Arial, sans-serif">Drinks Consumed:</span></p></li></ul><p><br></p><p><strong><span style="font-family: Arial, sans-serif">Examination</span></strong></p><p><span style="font-family: Arial, sans-serif">Extraoral (E/O)</span></p><ul><li><p><span style="font-family: Arial, sans-serif">NAD TMJ, LN, MOM, SG, no facial asymmetry</span></p></li></ul><p><br><span style="font-family: Arial, sans-serif">Intraoral (I/O)</span></p><ul><li><p><span style="font-family: Arial, sans-serif">NAD ST FOM, buccal mucosa, tongue, palate, fauces, tonsils</span></p></li><li><p><span style="font-family: Arial, sans-serif">Oral Hygiene (OH): Poor/Moderate/Good</span></p></li><li><p><span style="font-family: Arial, sans-serif">Generalised soft plaque deposits</span></p></li><li><p><span style="font-family: Arial, sans-serif">Calculus: Present lingual lower 3-3/generalised</span></p></li><li><p><span style="font-family: Arial, sans-serif">BPE:</span></p></li><li><p><span style="font-family: Arial, sans-serif">BOP:</span></p></li><li><p><span style="font-family: Arial, sans-serif">Recession:</span></p></li><li><p><span style="font-family: Arial, sans-serif">Canines: Can be palpated buccally upper/lower</span></p></li><li><p><span style="font-family: Arial, sans-serif">Malocclusion:</span><br></p></li></ul><p><span style="font-family: Arial, sans-serif">Radiographic Findings</span></p><ul><li><p><span style="font-family: Arial, sans-serif">R+L BW for caries and bone level screen</span></p></li><li><p><span style="font-family: Arial, sans-serif">RBW-Grade</span></p></li><li><p><span style="font-family: Arial, sans-serif">LBW-Grade</span></p></li><li><p><span style="font-family: Arial, sans-serif">Bone levels</span></p></li><li><p><span style="font-family: Arial, sans-serif">Contacts</span></p></li><li><p><span style="font-family: Arial, sans-serif">Restorations</span></p></li><li><p><span style="font-family: Arial, sans-serif">Deciduous teeth</span></p></li><li><p><span style="font-family: Arial, sans-serif">Permanent teeth visible on radiograph</span></p></li><li><p><span style="font-family: Arial, sans-serif">PA to assess for pa pathology/root morphology (Grade)</span></p></li><li><p><span style="font-family: Arial, sans-serif">OPG to assess for (Grade)</span></p></li></ul><p><br></p><p><strong><span style="font-family: Arial, sans-serif">Diagnosis</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Generalised plaque induced gingivitis</span></p></li><li><p><span style="font-family: Arial, sans-serif">Caries into enamel/dentine/pulp</span></p></li><li><p><span style="font-family: Arial, sans-serif">Acute/Chronic apical pathology</span></p></li><li><p><span style="font-family: Arial, sans-serif">Unrestorable teeth</span></p></li><li><p><span style="font-family: Arial, sans-serif">Malocclusion</span></p></li></ul><p><br><strong><span style="font-family: Arial, sans-serif">Risks</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Caries</span></p></li><li><p><span style="font-family: Arial, sans-serif">Periodontal disease</span></p></li><li><p><span style="font-family: Arial, sans-serif">Tooth Surface Loss (TSL)</span></p></li><li><p><span style="font-family: Arial, sans-serif">Oral Cancer</span></p></li></ul><p><br></p><p><strong><span style="font-family: Arial, sans-serif">Treatment Options</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Oral Health Education</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Advised electric toothbrush but manual is fine; shown optimal technique</span></p></li><li><p><span style="font-family: Arial, sans-serif">Advised bi-daily flossing; demonstration with floss and mirror</span></p></li><li><p><span style="font-family: Arial, sans-serif">Any fluoride-containing toothpaste advised; parent to check packaging</span></p></li><li><p><span style="font-family: Arial, sans-serif">To spit but not rinse after brushing</span></p></li><li><p><span style="font-family: Arial, sans-serif">Mouthwash to be used at a separate time to brushing</span></p></li><li><p><span style="font-family: Arial, sans-serif">High caries risk discussed; prescription of high fluoride toothpaste (Duraphat 2800ppm)</span></p></li></ul></li></ul><p></p><ul><li><p><strong><span style="font-family: Arial, sans-serif">Parental Guidance:</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Parent advised to supervise brushing or brush for the child</span></p></li></ul></li></ul><p></p><ul><li><p><strong><span style="font-family: Arial, sans-serif">Diet Advice:</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Discussed the 4 causes of caries (carbs, bacteria, time, biofilm)</span></p></li><li><p><span style="font-family: Arial, sans-serif">Emphasized importance of sugar quantity and frequency</span></p></li><li><p><span style="font-family: Arial, sans-serif">Advised keeping a diet diary</span></p></li><li><p><span style="font-family: Arial, sans-serif">Suggestions for reducing sugar and acid exposure</span></p></li></ul></li></ul><p></p><ul><li><p><span style="font-family: Arial, sans-serif">For Toddlers and Babies</span><strong><span style="font-family: Arial, sans-serif">:</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Only water/milk between meals</span></p></li><li><p><span style="font-family: Arial, sans-serif">Wean off bottle/dummy overnight once teeth erupt</span></p></li><li><p><span style="font-family: Arial, sans-serif">Change to sippy cup from bottle</span></p></li><li><p><span style="font-family: Arial, sans-serif">Only water in bottle/sippy cup at night</span></p></li><li><p><span style="font-family: Arial, sans-serif">Brush 2x daily with appropriate fluoride toothpaste as soon as teeth erupt</span></p></li><li><p><span style="font-family: Arial, sans-serif">Regular dental check-ups every 6 months after teeth eruption</span></p></li></ul></li></ul><p></p><ul><li><p><strong><span style="font-family: Arial, sans-serif">Restorative Options for Decay:</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Composite vs. GIC vs. no filling discussed</span></p></li><li><p><span style="font-family: Arial, sans-serif">Stepwise excavation for deep carious lesions</span></p></li><li><p><span style="font-family: Arial, sans-serif">Fissure sealants and Preventive Resin Restorations (PRRs) discussed</span></p></li><li><p><span style="font-family: Arial, sans-serif">Discussion on the need for regular maintenance to prevent decay progression</span></p></li></ul></li></ul><p></p><p><span style="font-family: Arial, sans-serif">&nbsp;</span><strong><span style="font-family: Arial, sans-serif">Agreed Care Plan</span></strong></p><ul><li><p><span style="font-family: Arial, sans-serif">Oral Health Instructions provided</span></p></li><li><p><span style="font-family: Arial, sans-serif">Diet advice given</span></p></li><li><p><span style="font-family: Arial, sans-serif">Fluoride application as per guidelines</span></p></li><li><p><span style="font-family: Arial, sans-serif">Fissure sealants</span></p></li><li><p><span style="font-family: Arial, sans-serif">Preventive Resin Restoration (PRR)</span></p></li><li><p><span style="font-family: Arial, sans-serif">Scale</span></p></li><li><p><span style="font-family: Arial, sans-serif">Recall frequency set</span></p></li></ul><p><br></p><p><strong><span style="font-family: Arial, sans-serif">Treatment Provided Today (Tx Today):</span></strong></p><p><br></p><p><strong><span style="font-family: Arial, sans-serif">Next Visit (N/V):</span></strong></p>""",
        )
        create_custom_prompt(
            new_user["_id"],
            new_user["practice_id"],
            "Implant placement",
            "Convert the transcript into professional, concise but comprehensive implant placement notes for patient record inclusion. Include all relevant sections from the example. If nothing is mentioned then put n/a for the section.",
            "<p><strong>Implant Placement Note</strong></p><p></p><p><strong>Medical History (MH)</strong></p><ul><li><p>Checked.</p></li></ul><p></p><p><strong>Consent Forms</strong></p><ul><li><p>Signed. Treatment discussed with patient and confirmed.</p></li></ul><p></p><p><strong>Pre-Medications Administered</strong></p><ul><li><p>Paracetamol: 1 x 500mg</p></li><li><p>Amoxicillin: 15 x 500mg; 1 tablet to be taken 3 times daily. Course started same day prior to implant appointment.</p></li><li><p>Metronidazole: 21 x 400mg; 1 tablet to be taken 3 times daily. Course started same day prior to implant appointment.</p></li></ul><p></p><p><strong>Local Anesthesia Given</strong></p><ul><li><p>Stent</p><ul><li><p>Checked.</p></li></ul></li></ul><p></p><p><strong>Surgical Procedure</strong></p><ul><li><p>Full mucoperiosteal flap raised between specified areas</p></li></ul><p></p><p><strong>Buccal Bone</strong></p><p></p><p><strong>Ridge</strong></p><p></p><p><strong>Implant System Used</strong></p><ul><li><p>Megagen</p></li></ul><p></p><p><strong>Implant Placement</strong></p><ul><li><p>Tooth Notation:</p><ul><li><p>Size:</p></li><li><p>LOT:</p></li><li><p>SN:</p></li></ul></li></ul><p></p><p><strong>Contour Augmentation</strong></p><ul><li><p>Buccally with specified materials</p></li></ul><p></p><p><strong>Flap Closure</strong></p><ul><li><p>Sutures: Prolene 5-0 used</p></li></ul><p></p><p><strong>Post-Operative Warnings</strong></p><ul><li><p>Patient advised to be cautious until local anesthesia wears off to prevent risk of burning or biting themselves.</p></li></ul><p></p><p><strong>Post-Operative Instructions</strong></p><ul><li><p>Advised on potential post-operative symptoms including pain, bleeding, swelling, bruising, and infection.</p></li><li><p>Instructed to contact the practice if post-operative conditions worsen or for any queries.</p></li></ul><p></p><p><strong>Review Appointment</strong></p><ul><li><p>Scheduled with VG in 10-14 days.</p></li></ul>",
        )
        create_custom_prompt(
            new_user["_id"],
            new_user["practice_id"],
            "Whitening",
            "Convert the transcript into professional, concise but comprehensive teeth whitening procedure notes for patient record inclusion. Include all relevant sections from the example. If nothing is mentioned then put n/a for the section.",
            """<p><strong>Tooth Whitening Consultation</strong></p><p></p><p>RFA – tooth whitening consult (+/- imps)</p><p></p><p>Nurse:</p><p></p><p>PCO:</p><p></p><p>MH:</p><p></p><p><strong>Tooth Whitening</strong></p><ul><li><p>Advantages:</p><ul><li><p>Very conservative, not many contraindications, will change the colour of teeth to be whiter, no guarantee it is permanent as this depends on patient’s oral health, smoking status, diet.</p></li></ul></li></ul><p></p><ul><li><p>Disadvantages:</p><ul><li><p>Will not change the shape or alignment of teeth</p></li></ul></li></ul><p></p><ul><li><p>Risks:</p><ul><li><p>Tooth sensitivity to hot/cold which is transient and will resolve following completion of TW treatment.</p></li><li><p>If very severe, the whitening can be alternated with toothpaste e.g., Sensodyne. This will not affect the outcome of treatment (the colour of tooth achieved) but will slow down the whitening process.</p></li><li><p>Gingival irritation which is often caused by overspill of TW gel during treatment, transient and will resolve following completion of treatment.</p></li></ul></li></ul><p></p><ul><li><p>Benefits:</p><ul><li><p>If the patient doesn’t have any dental treatment after TW which may change the shape of their teeth, then the trays can be retained and used again at a later day by purchasing more TW gels.</p></li></ul></li></ul><p></p><p><strong>Current tooth shade:</strong></p><p></p><p>Pt consented to clinical photos</p><p></p><p><strong>Process:</strong></p><ul><li><p>Impressions taken for the lab to create custom trays for the patient.</p></li></ul><p></p><ul><li><p>Home TW: the patient is given tubes of TW gel. The gel needs to be loaded into the trays each day and the trays worn. The amount loaded in each tooth is half a rice granule size. The trays need to be worn once every night. The patient must brush their teeth prior to seating the trays and after removing the trays, must not brush for at least 45 mins. The gels are enough for 14 days of TW. This method does not guarantee an outcome shade. If the patient isn’t happy with the shade at the end of treatment, they will need to purchase additional gels.</p></li></ul><p></p><ul><li><p>Guaranteed B1 TW: The gel needs to be loaded into the trays each day and the trays worn. The amount loaded in each tooth is half a rice granule size. The trays need to be worn once daily for 1 hour. The patient must brush their teeth prior to seating the trays and after removing the trays, must not brush for at least 45 mins. The gels are enough for 14 days of TW. On the 15th day, the patient comes for 1 hour of in surgery whitening with a higher strength gel which cannot be dispensed. This method guarantees a B1 shade. If this is not achieved at the end of the 15 day period, the company will provide extra gels at no extra cost.</p></li></ul><p></p><p><strong>Tips and Tricks:</strong></p><ul><li><p>The gels need to be kept in the fridge. To prevent the gels overspilling while loading, it is recommended the gels are taken out of the fridge 10 mins prior to loading.</p></li></ul><p></p><p><strong>Longevity of results:</strong></p><ul><li><p>This cannot be guaranteed for either type of TW. This depends on patient related factors such as maintenance of oral hygiene and diet (if the patient consumes foods with high pigment levels e.g., black coffee, turmeric, red wine, dark chocolate, this will adversely affect the longevity).</p></li></ul><p></p><p>All benefits and risks discussed.</p><p></p><p>All advantages and disadvantages discussed.</p><p></p><p>All costs discussed.</p><p></p>""",
        )
        create_custom_prompt(
            new_user["_id"],
            new_user["practice_id"],
            "Filling",
            "Convert the transcript into professional, concise but comprehensive filling procedure notes for patient record inclusion. Include all relevant sections from the example. If nothing is mentioned then put n/a for the section.",
            """<p><strong>Filling</strong></p><p></p><p><strong>Pt opted for:</strong></p><ul><li><p>RFA – fillings</p></li></ul><p></p><p>Nurse<strong>:</strong></p><p></p><p>PCo –</p><p></p><p>MH –</p><p></p><p><strong>Reconfirmed consent</strong></p><p></p><p></p><p><strong>Treatment options:</strong></p><ul><li><p><strong>Composite vs Amalgam vs GIC</strong></p><ul><li><p>Amalgam – long standing success data, less technique sensitive, poor aesthetics, more destructive to tooth</p></li></ul><p></p><ul><li><p>Composite – tooth coloured, restores area of caries/hole in tooth, technique sensitive, conservative, post op sensitivity</p></li></ul><p></p><ul><li><p>GIC – where moisture control difficult, lack of mechanical retention for amalgam, maintenance of otherwise unrestorable tooth, semi permanent, semi tooth coloured.</p></li></ul></li></ul><p></p><ul><li><p><strong>Composite vs no tx</strong></p><ul><li><p>No tx – risk of progression of TSL which can undermine and weaken tooth leading to fractures/pulp exposure. May also make tooth unrestorable due to location of defect (cervical/extending subgingival). Can lead to root caries when gingival recession and root exposure present.</p></li></ul><p></p><ul><li><p>Composite – acts like a bandage. Prevents progression of TSL. If worn away then can be replaced. Adhesive hence no tooth destruction. Tooth coloured so well masked. If poor oh, can introduce interface for caries.</p></li></ul></li></ul><p></p><ul><li><p>Stepwise excavation for deep carious lesions close to the pulp</p><p></p></li><li><p>Caries appears close to, but not into pulp clinically and on radiograph. Pt shown on radiograph.</p></li></ul><p></p><p></p><p><strong>Options:</strong></p><ul><li><p>Leave – risk of progression and pain and eventual pulpal involvement/loss of tooth/more extensive treatment</p></li></ul><p></p><ul><li><p>XLA – not advised as currently restorable.</p></li></ul><p></p><ul><li><p>Full caries removal which may lead to pulp exposure and tooth req rct/xla.</p></li></ul><p></p><ul><li><p>Stepwise excavation discussed. Removal of all soft caries but leaving softened stained dentine over pulp to help maintain tooth vitality. Restoration with semi permanent material – GIC – to allow tertiary dentine formation. Thereafter reassess at 3/12 radiographically and clinically.</p></li></ul><p></p><ul><li><p>If asymptomatic and evidence of tertiary dentine then can remove GIC and discuss best option for definitive restoration. If no evidence of tertiary dentine, may req further reassessment in 3/12.</p></li></ul><p></p><ul><li><p>If symptomatic at anytime, may req RCT.</p></li></ul><p></p><p>Pt understood above options and information and opted for stepwise approach as would like to avoid rct if possible but understands this may be an unavoidable eventuality for tooth in near future.</p><p></p><p>Pt consented to clinical photos</p><p></p><p>Topical LA</p><p></p><p>L/R ID Block/Buccal infiltration/Palatal infiltration/Lingual infiltration</p><p></p><p>Lidocaine 2% with adrenaline 1:80,000/ Articaine 4% with adrenaline 1:100,000</p><p></p><p>A x 2.2ml administered</p><p></p><p>Shade chosen:</p><p></p><p>Caries removed.</p><p></p><p>Tooth isolated with rubber dam/high volume suction and CWR and clamp/V3 sectional matrix/matrix band/CWR</p><p></p><p>Tooth restored with composite/amalgam/GIC</p><p></p><p>Margins and occlusion checked.</p><p></p><p>Pt happy with comfort/bite/aesthetics, Advised care with hot food/drink whilst numb.</p><p></p>""",
        )
        create_custom_prompt(
            new_user["_id"],
            new_user["practice_id"],
            "Endodontic",
            "Convert the transcript into professional, concise but comprehensive endodontic treatment notes for patient record inclusion. Include all relevant sections from the example. If nothing is mentioned then put n/a for the section.",
            """<p><strong>Endodontic Treatment:</strong></p><p></p><p>RFA: RCT (tooth)</p><p></p><p>Nurse:</p><p></p><p>PCO-</p><p></p><p>MH-checked. No change since l/v.</p><p></p><p>Confirmed pt would like RCT on this tooth.</p><p></p><p>Warnings given re: risk of unsuccessful RCT therefore tooth may req xla, surgery or re-tx/fracture file/post op pain, swelling, infection, perforation of canal or tooth, damage to nerves, sinus, phoenix abscess, re-infection, missed canal</p><p></p><p>If re-rct req at later date then this may have to be on referral to nhs/pvt specialist. No guarantee of acceptance by NHS specialist. For posterior teeth, RCT tooth will req cuspal coverage to prevent # which will incur an additional cost.</p><p></p><p><strong>Adv of endo:</strong></p><ol><li><p>Save tooth for up to 10 years however no guarantee of longevity of treatment as this depends on tooth anatomy, complexity of treatment, operator experience, patient related factors such as OH, diet, caries risk, occlusion, habits and parafunction etc.</p></li></ol><p></p><ol start="2"><li><p>Explained that for all endo tx – success higher with specialist. Simple endo unlikely to be accepted by NHS hence may req ref to pvt specialist.</p></li></ol><p></p><p></p><p>Pt consented, appeared to understand information.</p><p>Post RCT cuspal coverage discussed</p><p>Justification for cuspal coverage: to prevent #</p><p></p><p></p><p><strong>Options:</strong></p><ul><li><p>Tooth coloured: emax/zirconia/MCC – best material will be decided on based on clinical information</p></li><li><p>Metal coloured: NPM or gold</p></li><li><p>Advantages/ disadvantages, risks, benefits and costs of each option explained</p></li></ul><p></p><p><strong>Pt opted for:</strong></p><p></p><p>Pt consented to clinical photos</p><p></p><ul><li><p>Topical lA</p></li><li><p>Buccal infiltration/Right ID block/Left ID block</p></li><li><p>Lidocaine 2% with adrenaline 1:80,000/Articaine 4% with adrenaline 1:100,000</p></li><li><p>1 x 2.2ml administered</p></li><li><p>Anaesthesia achieved</p></li><li><p>Tooth accessed</p></li><li><p>X canals found.</p></li><li><p>EWL from pre-op radiograph = mm</p></li><li><p>Canals scouted to EWL using size 10, 15, and 20 k-files.</p></li><li><p>Size 20 k-files inserted to EWL</p></li><li><p>WL radiograph</p></li></ul><p></p><p>Grade</p><p></p><p>Bone levels:</p><p></p><p>Files appears to length/Files appears short by mm/Files long by mm</p><p></p><p>Apex locator used to confirm WL</p><p></p><p>Confirmed WL =</p><p></p><p>Reference point</p><p></p><p>Tooth isolated with RD and clamp</p><p></p><p>Clamp no:</p><p></p><p>Canals shaped using successive rotary files XXX to WL. Irrigated in between each file change using sodium hypochlorite 1ml. Lubricated file path using glyde. Recapitulated in between using size 10 k file.</p><p></p><p>Canals dried using paper points.</p><p></p><p>Master cone radiograph with size X master cone to WL</p><p></p><p>Grade</p><p></p><p>Bone levels:</p><p></p><p>Master cone to length/Master cones short by/Master cones long by</p><p></p><p>Dressed with CAOH</p><p></p><p>Tooth dressed with cw and cavit</p><p></p><p>Canals obturated using master size X GP points with accessory cones and tubli seal sealant. Cold lat condensation technique</p><p></p><p>Excess GP removed</p><p></p><p>Tooth restored with composite.</p><p></p><p>Post op radiograph to check quality of RF</p><p></p><p>Grade</p><p></p><p>Bone levels:</p><p></p><p>Canal well obturated to length, well tapered and condensed with no voids.</p><p></p><p>Voids present/Canal obturated short of apex by mm/Canal obturated long of apex by mm</p><p></p><p>POI given re: care with hot/chewing whilst numb, possibility of post op pain/possibility of phoenix abscess/advised painkillers if req/advised to call if any problems/advised care on tooth until crown placed as risk of # present.</p><p></p><p>N/V:</p><p></p>""",
        )
        create_custom_prompt(
            new_user["_id"],
            new_user["practice_id"],
            "Crown fit",
            "Convert the transcript into professional, concise but comprehensive Crown fit treatment notes for patient record inclusion. Include all relevant sections from the example. If nothing is mentioned then put n/a for the section.",
            """<p><strong>Onlay/ Crown fit</strong></p><p></p><p>N/V: crown/onlay fit.</p><p></p><p>RFA-crown/onlay fit (tooth)</p><p></p><p>Nurse:</p><p></p><p>PCO-</p><p>MH – checked, no change</p><p></p><p></p><ul><li><p>Crown/Onlay checked against lab docket to ensure all instructions carried out.</p></li><li><p>Crown/Onlay checked on model and die. Margins/contacts and occlusion ok. Fitting and occlusal surface ok.</p></li><li><p>Model checked for damage.</p></li></ul><p></p><p></p><p>Topical LA</p><p>Buccal infiltration/Right ID block/Left ID block</p><p>Lidocaine 2% with adrenaline 1:80,000/Articaine 4% with adrenaline 1:100,000</p><p>1 x 2.2ml administered</p><p>Anaesthesia achieved</p><p></p><p></p><ol><li><p>Temp removed from tooth</p></li><li><p>Prep cleaned of excess temp cement and debris.</p></li><li><p>Tooth dried</p></li><li><p>Crown/Onlay tried in.</p></li><li><p>Margins, occlusion, contacts all ok.</p></li></ol><p></p><ul><li><p>Tooth and crown sandblasted</p></li><li><p>Tooth isolated using CWR/rubber dam + clamp</p></li><li><p>Prep dried</p></li><li><p>Cemented using fuji/rely x</p></li><li><p>Excess cement removed</p></li><li><p>Contact flossed through</p></li><li><p>Checked margins and occlusion again – ok</p></li></ul><p></p><p>Reiterated important of OH. Esp as crown/onlay margins can attract plaque and also to floss.</p><p></p><p>Pt consented to clinical photographs</p><p></p><p>N/V:</p>""",
        )
        create_custom_prompt(
            new_user["_id"],
            new_user["practice_id"],
            "Extraction",
            "Convert the transcript into professional, concise but comprehensive tooth extraction notes for patient record inclusion. Include all relevant sections from the example. If nothing is mentioned then put n/a for the section.",
            """<p><strong>Extraction</strong></p><ul><li><p>Valid verbal consent for extraction</p></li></ul><p></p><p><strong>Risks explained:</strong></p><ul><li><p>Damage to adjacent teeth/fills/crown</p></li><li><p>ID nerve damage</p></li><li><p>Possible surgical intervention</p></li><li><p>Bleeding complications and need for sutures, arrest bleeding.</p></li><li><p>Post op pain and infection possible also.</p></li><li><p>OAC</p></li></ul><p></p><p>LA<strong>:</strong></p><p></p><p>Tooth Extracted with luxators and forceps -</p><p></p><p>POIG- written and verbal</p><p></p><p>Haemostasis achieved</p><p></p><p><strong>Post op details:</strong></p><ol><li><p>Post op pain</p></li><li><p>numbness</p></li><li><p>lip biting and sensitivity described</p></li></ol><p></p><p>Pt fit and well to discharge</p>""",
        )
        create_custom_prompt(
            new_user["_id"],
            new_user["practice_id"],
            "Treatment plan",
            "Convert the above dental dictation transcript into professional, concise but comprehensive dental treatment plan for patient record inclusion.",
            """<p><strong>1. Consultation and Assessment</strong></p><ul><li><p>Medical History Review</p></li><li><p>Dental Examination</p></li><li><p>Diagnostic Imaging (X-rays, CT scans, etc.)</p></li><li><p>Impressions for Study Models (if needed)</p></li><li><p>Discussion of Diagnosis, Procedure, Risks, and Alternatives</p></li><li><p>Presentation of Treatment Plan</p></li></ul><p></p><p></p><p><strong>2. Pre-Treatment Preparation</strong></p><ul><li><p>Medical Clearance (if required)</p></li><li><p>Professional Cleaning (if necessary)</p></li><li><p>Pre-Treatment Instructions (including medication prescriptions if needed)</p></li></ul><h4 style="text-align: start"><strong>Initial Treatment Phase</strong></h4><p style="text-align: start"></p><p style="text-align: start"><strong>3. Initial Treatment Phase</strong></p><ul><li><p style="text-align: start">Date:</p></li><li><p>Procedure<strong>:</strong></p><ul><li><p>Local Anesthesia (if applicable)</p></li><li><p>Description of specific dental procedure (e.g., filling, extraction, root canal, implant placement, etc.)</p></li><li><p>Any necessary post-procedure steps (e.g., suturing, placement of temporary restoration)</p></li></ul></li><li><p>Post-Treatment Instructions:</p></li></ul><p></p><p><strong>4. Healing and Follow-Up Care</strong></p><ul><li><p>Follow-Up Visits: (schedule based on specific treatment)</p></li><li><p>Evaluation of Healing (if applicable)</p></li><li><p>Radiographic Evaluation (if applicable)</p></li></ul><p></p><p><strong>5. Secondary Treatment Phase (if applicable)</strong></p><ul><li><p>Date<strong>:</strong></p></li><li><p>Procedure<strong>:</strong></p><ul><li><p>Local Anesthesia (if applicable)</p></li><li><p>Description of secondary dental procedure (e.g., placement of permanent restoration, abutment placement for implants, etc.)</p></li><li><p>Any necessary post-procedure steps</p></li></ul></li><li><p>Post-Treatment Instructions</p></li></ul><p></p><p><strong>6. Final Treatment Phase (if applicable)</strong></p><ul><li><p>Date:</p></li><li><p>Procedure:</p><ul><li><p>Final adjustments or placements (e.g., crown placement, final fitting of dentures, etc.)</p></li><li><p>Occlusion Check (if applicable)</p></li></ul></li><li><p>Oral Hygiene Instructions</p></li></ul><p></p><p><strong>7. Maintenance and Regular Check-Ups</strong></p><ul><li><p>Regular Check-Ups: (frequency based on specific treatment and patient needs)</p></li><li><p>Professional Cleaning</p></li><li><p>Monitoring of Treatment Outcomes</p></li></ul>""",
        )
        create_custom_prompt(
            new_user["_id"],
            new_user["practice_id"],
            "Transcribe consultation",
            "Convert the following dental consultation transcript into a concise conversation transcript between the dentist and patient. Format each line clearly as 'Dentist' or 'Patient' ",
            "<p></p>",
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
        send_email(subject="Reset password", msg=email, sender="password.manager@indentr.com", recipient=user_document["email"], password=TRIAGE_MAIL_PASSWORD)
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
