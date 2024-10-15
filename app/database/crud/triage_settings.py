# Triage Settings CRUD file
# -- Files must start with either create, retrieve, update, delete

from app.database.schemas.triage_settings import TriageSettings


def create_triage_settings(practice_id: str):
    triage_setting = TriageSettings(practice_id=practice_id)

    triage_setting.save()


def retrieve_triage_settings(practice_id: str):
    triage_setting = TriageSettings.objects(practice_id=practice_id).first()

    if not triage_setting:
        return {
            "primary_color": "#1a73e8",
            "show_page_runner": True,
            "show_requested_date": False,
            "show_date_of_birth": False,
            "show_gender": False,
            "show_phone_number": True,
            "show_address": False,
        }

    triage_setting_dict = triage_setting.to_mongo().to_dict()
    triage_setting_dict["_id"] = str(triage_setting_dict["_id"])
    triage_setting_dict["practice_id"] = str(triage_setting_dict["practice_id"])

    return triage_setting_dict


def update_triage_settings(
    practice_id: str,
    primary_color: str,
    show_page_runner: bool,
    show_requested_date: bool,
    show_date_of_birth: bool,
    show_gender: bool,
    show_phone_number: bool,
    show_address: bool,
):
    triage_setting = TriageSettings.objects(practice_id=practice_id).first()

    if not triage_setting:
        new_triage_settings = TriageSettings(
            practice_id=practice_id,
            primary_color=primary_color,
            show_page_runner=show_page_runner,
            show_requested_date=show_requested_date,
            show_date_of_birth=show_date_of_birth,
            show_gender=show_gender,
            show_phone_number=show_phone_number,
            show_address=show_address,
        )
        new_triage_settings.save()

    else:
        triage_setting.primary_color = primary_color
        triage_setting.show_page_runner = show_page_runner
        triage_setting.show_requested_date = show_requested_date
        triage_setting.show_date_of_birth = show_date_of_birth
        triage_setting.show_gender = show_gender
        triage_setting.show_phone_number = show_phone_number
        triage_setting.show_address = show_address
        triage_setting.save()
