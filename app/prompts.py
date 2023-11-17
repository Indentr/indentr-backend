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
