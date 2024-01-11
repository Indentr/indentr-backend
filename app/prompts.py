dentist_notes_prompt = """
        Based on the dentists notes, please ask the dentist however many questions you want (between 0 and 10).
        These questions should aim to gather more information from the dentist filling any gaps that they might have left in their notes.
        The reason we are gathering this information is so that we can use ai to automatically generate a consent letter that can be sent to
        the patient expaining the treatment etc. To this end focus the questions appropriatly. They should focus on the current state of the
        symptoms and what the dentist wants to do moving forward. including questions about any risk factors associated.
        The final question should suggest several forms of treatment and ask the dentist what they would like to proceed with.
        Please format your response as JSON, as shown below:
        [
            {
                "symptom": "[Symptom name]",
                "q1": "[Insert q1]",
                "q2": "[q2]",
                "q3": "[q3]"
            },
            {
                etc.
            }
        ]
        Do not provide any additional text other then the required JSON array as shown above
        IMPORTANT: the questions you ask must be asked using a passive voice
    """


symptoms_details_prompt = """
        For each symptom, please ask the dentist three follow-up questions.
        These questions should aim to gather more information from the dentist about the patient's symptoms.
        Please format your response as JSON, as shown below:
        [
            {
                "symptom": "[Symptom name]",
                "q1": "[Insert q1]",
                "q2": "[q2]",
                "q3": "[q3]"
            },
            {
                etc.
            }
        ]
        Do not provide any additional text other then the required JSON array as shown above
        IMPORTANT: the questions you ask must be asked using a passive voice
    """


generate_consent_letter_prompt = """
    I want you to write a dental consent letter based on the notes and symptom details provided.
    I have provided an example to use as a guide on how to structure a consent letter. The aim of the letter is to provide the patient,
    with the information that they need to make a decision to go forward with the treatment. The letter should provide some information about the
    possible complications. The letter is, however, essentially a final sales pitch for the treatment that has already been discusssed in person
    with the patient.

    Your response must be written as an HTML string in the format provided below,
    where each paragraph is wrapped in a <p> tag:

    <p class="p1-title">[insert paragraph text, do not include dear ....]</p>
    <p></p> // IMPORTANT: for each new paragraph or section insert an empty p tag like this one
    <p class="etc">[etc.]</p>

    // if letter requires an undordered list or bullet list then within a paragraph you can insert html for ul/ol
    <p class="insert-pX-title]">
        <ul>
            <li>[insert list item]</li>
            <li>[etc.]</li>
        </ul>
    </p>
    <p></p>
    <p class="insert-pX-title]">
        <ol>
            <li>[insert list item]</li>
            <li>[etc.]</li>
        </ol>
    </p>

    Using the example dental consent letter as a template, I want you to tailor it
    for the patient (Make sure to remove or
    change unnecessary content from the example letter so it fits the patient symptoms)
"""


upload_transcript_prompt = """
    Objective: Convert the above dental dictation transcript into professional, concise but comprehensive
    dental notes for patient record inclusion.

    Important points: Bare in mind that it is an ai generated audio transcription so some of the words
    maybe incorrectly recorded, do your best to guess what the correct sentence would have been.
    eg upper last 3 probably means upper left 3, UL3 or something phonetically similar but written
    in words that do not appear to fit the context will mean Upper left 3

    do not include sections for patient information e.g. patient name as this notes record will be saved to
    a patient file anyway.

    It is critical that you do not make up sections that are not mentioned in the transcript if the audio
    transcript is empty or unusable then please do not try to guess. just reply that the transcript is unusable/empty.
"""


create_triage_request_prompt = """
    A patient has just filled out a dental triage form where they were asked 3 questions based on a dental symptom they have.

    Based on the patients patients response I need you to give a response to the following:
    1. A diagnosis title, a very short title of like 5 words max
    2. A general overview of the problem, a dentist will be reading this so you don't have to explain what anything means. If the diagnosis is unclear then say so.
    3. A severity score out of 10 (10 being absolutely must see a dentist in the next hour or they will die, 1 being tooth hurts slightly)

    Your responses to the following must be formatted as JSON, as shown below:
    {{
        "diagnosis": "[Your diagnosis title],
        "overview": "[A general overview of the problem]",
        "severity": "[An int value between 0/10]":
    }}
"""


generate_triage_questions_prompt = """
    Please ask the patient three follow-up questions.
    The questions show aim to gather more information from the patient so the dentist has all the necessary information in terms of severity of condition etc.
    Please format your response as JSON, as shown below:
    [
        {{
            "symptom": "[Symptom name]",
            "q1": "[Insert q1]",
            "q2": "[q2]",
            "q3": "[q3]"
        }},
        {{
            etc.
        }}
    ]
"""
