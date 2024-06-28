import time
from datetime import datetime

from app.services.openAI import (
    ask_gpt,
    calculate_openAI_gpt_cost,
    count_input_tokens,
)


async def treatment_section_referral(dentistNotes: str, gpt_model: str):
    prompt = f"""

        START_OF_CONTENT_INSTRUCTIONS

        Write a referral letter for a patient from the perspective of the referring dentist/doctor/clinician to another dentist/doctor/clinician
        The patient is a patient of your practice or may have just come to see you for an initial appointment/GP appointment/consultation, it does not matter.
        The dentist/doctor/clinician you are referring to does not need to know the nature of your relationship to the patient past the fact that they are
        currently your patient and you are referring them over to the dentist/doctor/clinician who is currently not aware of the patient in question.
        The referral letter should explain the symptoms/reason for referral. It should be written formally but not coldly.


        END_OF_CONTENT_INSTRUCTIONS

        Here are the dental/GP notes that I need you to base your answer around:
        START_OF_NOTES
        {dentistNotes}
        END_OF_NOTES

        Make sure to use english spelling. Don't include any introductions or signoffs like 'Dear...' or 'From....'
        Please format it as a html string where each paragraph is wrapped in <p></p> with an empty <p/> between each paragraph and dont wrap your response in ```html I want just a normal string response
    """
    input_tokens = count_input_tokens(prompt, gpt_model)
    section, output_tokens = await ask_gpt(
        prompt, "You're a UK based dentist/doctor writing a referral letter for your patient to go to another dentist/doctor", gpt_model
    )
    cost = calculate_openAI_gpt_cost(input_tokens, output_tokens, gpt_model)
    return section, input_tokens, output_tokens, cost


async def treatment_section(dentistNotes: str, formality_level: bool, detail_level: bool, gpt_model: str):
    example_section = "<p>Following our comprehensive consultation and review of your Cone Beam Computed Tomography (CBCT) scan, we have identified that the vertical bone height in the posterior maxilla is insufficient for standard dental implant placement. This is primarily due to the pneumatisation of the maxillary sinus. We have discussed at length the various treatment options available to you, and after careful consideration, you have decided to proceed with a Sinus Graft procedure. This letter serves to outline the details of the treatment, including the risks and benefits, to ensure that you are fully informed and have given your consent to proceed.</p><p></p><p>The Sinus Graft procedure is designed to increase the amount of bone in the posterior maxilla, which is essential for the successful placement and long-term stability of dental implants. The treatment will involve the following steps:</p><p></p><ol><li><p>Anesthetic Administration: To ensure your comfort during the procedure, local anesthesia will be administered, typically 2% lidocaine with 1:100,000 epinephrine. You have also opted for intravenous sedation, which will help you to relax and reduce any anxiety during the surgery.</p><p></p></li><li><p>Incision and Access: An intraoral incision will be made to expose the lateral wall of the maxillary sinus. A careful dissection will then be performed to create a small window in the bone, providing access to the sinus cavity.</p><p></p></li><li><p>Sinus Lift and Graft: Once access is achieved, the sinus membrane will be gently elevated to create a space for the placement of the graft material. The graft material used will be Rocky Mountain irradiated bone and Bio-Oss, which are well-established in their ability to facilitate new bone growth. In some cases, a Bio-guide membrane may be used to cover the graft or repair any incidental tears in the sinus lining.</p><p></p></li><li><p>Closure: The incision will be meticulously closed with sutures, and you will be provided with detailed postoperative instructions to ensure optimal healing.</p></li></ol><p></p><p>As with any surgical procedure, there are potential risks and benefits that must be considered. The benefits of a Sinus Graft include the ability to create sufficient bone volume for the future placement of dental implants, which can ultimately restore function and aesthetics to your dentition. This procedure is a well-established and successful technique with a high success rate when performed under the right conditions.</p><p></p><p>However, there are also risks associated with the Sinus Graft procedure. One such risk is the possibility of a large tear in the sinus membrane, which could prevent the completion of the procedure. Should this occur, we will communicate with you immediately about the situation and discuss potential alternative treatments. Another risk is the potential for the graft to be unsuccessful, particularly if an infection develops. In such cases, the graft may need to be removed, and the area will be reassessed for future treatment possibilities.</p><p></p><p>Postoperative care is crucial for the success of the Sinus Graft. You will be prescribed antibiotics and pain management medication, and follow-up appointments will be scheduled to monitor the healing process both clinically and radiographically. It is imperative that you maintain excellent oral hygiene, avoid strenuous activities, and attend all scheduled follow-up visits to ensure the best possible outcome.</p><p></p><p>The plan is to schedule the placement of the dental implants approximately six months following the Sinus Graft procedure, with the restoration of the implants planned for three months after their placement. It is essential to adhere to this timeline to allow for proper healing and integration of the graft material.</p><p></p><p>Please be assured that the procedure will be performed with the utmost care and precision, and we are committed to providing you with the highest standard of treatment. Your understanding and cooperation during the preoperative and postoperative periods are greatly appreciated.</p>"
    prompt = f"""
        I need you to write three sections: 'Introduction', 'Description of treatment' and 'Discussion of risks and benefits' for a dental consent letter, its up to you as for the length of each section but make sure the description of treatment and discussion of risks covers all necessary details. Please format it as a html string where each paragraph is wrapped in <p></p> with an empty <p/> between each paragraph.
        Here is an example of what an introduction and treatment information paragraphs look like formatted as html string:
        START_OF_EXAMPLE
        {example_section}
        END_OF_EXAMPLE

        Here are the dental notes that I need you to base your answer around:
        START_OF_NOTES
        {dentistNotes}
        END_OF_NOTES

        *** IMPORTANT SECTION ABOUT THE TONE OF THE LETTER***
        The formality of the section should be: {formality_level * 100}% (0% being very informal, 100% being very formal)
        The level of detail and length of the section should be: {detail_level * 100}% (0% being not very detailed and short, 100% being incredibly detailed and very long)
        Never use terminology like UL4, LL3 in the letter. use "upper left 3" instead for example.
        *** END OF IMPORTANT SECTION ABOUT THE TONE OF THE LETTER***

        Make sure to use english spelling. Don't include any introductions or signoffs like 'Dear...' or 'From....'
        Each new paragraph needs a: <p/> between the paragraphs as this represents a blank line and dont wrap your response in ```html I want just a normal string response
    """
    input_tokens = count_input_tokens(prompt, gpt_model)
    section, output_tokens = await ask_gpt(prompt, "You're a UK based dentist writing consent letters for patients", gpt_model)
    cost = calculate_openAI_gpt_cost(input_tokens, output_tokens, gpt_model)
    return section, input_tokens, output_tokens, cost


async def fees_section(
    dentistNotes: str,
    formality_level: bool,
    detail_level: bool,
    include_pricing: bool,
    pricing_list: str,
    patient_insurance_info: str,
    include_insurance_info: bool,
    gpt_model: str,
):
    example_pricing_section = "<p></p><p>The cost for a composite dental filling per tooth is £123.00, as per our current pricing list. This fee includes all materials and labor associated with the procedure. Please note that the actual cost may vary based on any additional requirements or unforeseen circumstances during the procedure.</p><p></p><p>Should you choose to proceed with the recommended treatment, we will schedule your next appointment at your earliest convenience. We will also provide you with detailed aftercare instructions to ensure the best possible outcome and recovery.</p>"
    example_insurance_section = "<p></p><p>Regarding your insurance coverage, we have on record that you are insured by DentalCare Insurance under the policy number DC123456789, with coverage valid through December 31, 2025. We will assist you in submitting the necessary claims to your insurance provider. However, please be aware that you are responsible for ensuring that the costs of the procedure are within the terms of your coverage. We recommend that you contact DentalCare Insurance directly to confirm the extent of your coverage for this procedure.</p><p></p><p>Any portion of the fees not covered by your insurance will be your responsibility, and we will provide you with a detailed breakdown of costs for your records and for submission to your insurance company. Payment for the procedure is due at the time of service unless other arrangements have been made in advance with our office.</p>"
    prompt = ""
    if not include_pricing and not include_insurance_info:
        return "", 0, 0, 0
    if include_pricing:
        prompt = f"""
            I need you to write the fees and costs section of a dental consent letter. Its important that you include any necessary detail that is typically found in a financial considerations section of a dental consent letter.
            This means a discussion of the costs associated with the treatment, and information about insurance coverage (if applicable)
            You will need to base the fees and costs off the dentist notes that are provided, along with the practice's price list.
            Your response must be a html string, with the section containing the necessary html formatting e.g. put each paragraph in <p> tag with each new line putting in empty <p></p> like so (don't use any h tags), but you can use: <ul>, <ol>,<li> etc. where you feel is appropriately needed in a consent letter.

            Here is an example fees and pricing section, that I want you to base your response on:
            START_OF_EXAMPLE_RESPONSE
            {example_pricing_section}
            END_OF_EXAMPLE_RESPONSE

            Here are the dental notes that I need you to write the costs from:
            START_OF_NOTES
            {dentistNotes}
            END_OF_NOTES

            Here is the practice's price list
            START_OF_PRICE_LIST
            {pricing_list}
            END_OF_PRICE_LIST

            {"I want you to include patient insurance coverage information in your response" if include_insurance_info else "Don't include any patient insurance information in your response"}
            {"Practice price list"+patient_insurance_info if include_insurance_info else ""}

            The formality of the section should be: {formality_level * 100}% (0% being very informal, 100% being very formal)
            The level of detail and length of the section should be: {formality_level * 100}% (0% being not very detailed and short, 100% being incredibly detailed and very long)

            Make sure to use english spelling. Only include information necessary to the fees and costs section of a consent letter, e.g. don't include opening 'Dear...' or signoff 'From...' etc.
            Important: every new paragraph needs a blank line between it so for each new line make sure to include an empty <p></p> tag and dont wrap your response in ```html I want just a normal string response
        """
    elif include_insurance_info:
        prompt = f"""
            I need you to write a short paragraph on patient insurance details for a dental consent letter. It only needs to be one paragraph specifically to do with patients insurance coverage information.
            Your response needs to be a html string where each paragraph is wrapped in a <p></p> tag.

            Here is an example of an insurance paragraph response:
            START_OF_EXAMPLE_RESPONSE
            {example_insurance_section}
            END_OF_EXAMPLE_RESPONSE

            Make sure to use english spelling. Only include information necessary to the fees and costs section of a consent letter, e.g. don't include opening 'Dear...' or signoff 'From...' etc.
            Important: every new paragraph needs a blank line between it so for each new line make sure to include an empty <p></p> tag and dont wrap your response in ```html I want just a normal string response
        """
    input_tokens = count_input_tokens(prompt, gpt_model)
    section, output_tokens = await ask_gpt(prompt, "You're a UK based dentist writing consent letters for patients", gpt_model)
    cost = calculate_openAI_gpt_cost(input_tokens, output_tokens, gpt_model)
    return section, input_tokens, output_tokens, cost


def format_address(address: str):
    address_parts = address.split(", ")
    # generates the HTML lines dynamically
    html_lines = "".join([f"<p style='text-align: right'>{part},</p>" for part in address_parts])
    # formats the address into the HTML string
    return (f"""{html_lines}""") + ("<p></p><p></p>")


def format_image_header(image: str, header: str):
    header = f"""
        <table>
            <tbody>
                <tr>
                    <td colspan="1" rowspan="1">
                        <p>
                            <img style="max-width: 100%; height: auto;" src="data:image/png;base64,{image}" />
                        </p>
                    </td>
                    <td colspan="3">{header}</td>
                </tr>
            </tbody>
        </table>
    """
    return header


def generate_formatted_date():
    current_date = datetime.now()
    uk_date_format = current_date.strftime("%d/%m/%y")
    date = f"""
        <p></p>
        <p></p>
        <p>
            {uk_date_format}
        </p>
        <p></p>
    """
    return date


def generate_formatted_dear(gender: str, salutation: str, forename: str, recipient_naming: str, surname: str):
    mrOrMrs = "Mr" if gender == "Male" else "Mrs"
    dear = f"""
        <p></p>
        <p>
            {salutation} {forename if recipient_naming == 'first_lastname' else mrOrMrs} {surname},
        </p>
        <p></p>
    """
    return dear


def format_contact_details_text(contact_details_text: str):
    contact_details_text_formatted = f"""
        <p></p>
        <p>{contact_details_text}</p>
        <p></p>
    """
    return contact_details_text_formatted


def generate_signoff(sign_off: str, name: str, dentist_naming: str, practice_name: str):
    signoff = f"""
        <p></p>
        <p>
            {sign_off} {name if dentist_naming == 'dentist_name' else ''} {(name+', '+practice_name)  if dentist_naming == 'dentist_practice_name' else ''} {practice_name if dentist_naming == 'practice_name' else ''}
        </p>
        <p></p>
    """
    return signoff


def generate_formatted_completed_in(treatment_section_cost, fees_section_cost, gpt_model: str, start):
    completed_in = f"""
        <p></p>
        <p>
            completed in {round((time.time() - start), 2)} seconds
        </p>
        <p/>
        <p>
            cost: ${treatment_section_cost + fees_section_cost}
        </p>
        <p/>
        <p>
            used gpt model: {gpt_model}
        </p>
    """
    return completed_in


dentist_signature = """
    <p></p>
    <p></p>
    <p>Dentist's Signature: ___________________________________ Date: __________________</p>
    <p></p>
"""

patient_signature = """
    <p></p>
    <p></p>
    <p>Patient's Signature: ___________________________________ Date: __________________</p>
    <p></p>
    <p></p>
"""
