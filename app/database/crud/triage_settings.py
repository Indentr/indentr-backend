# Triage Settings CRUD file
# -- Files must start with either create, retrieve, update, delete

from app.database.schemas.triage_settings import TriageSettings


def create_triage_settings(practice_id: str):
    triage_setting = TriageSettings(practice_id=practice_id)

    triage_setting.save()


def retrieve_triage_settings(practice_id: str):
    triage_setting = TriageSettings.objects(practice_id=practice_id).first()

    if not triage_setting:
        return {"primary_color": "#1a73e8", "show_page_runner": True, "show_requested_date": True}

    triage_setting_dict = triage_setting.to_mongo().to_dict()
    triage_setting_dict["_id"] = str(triage_setting_dict["_id"])
    triage_setting_dict["practice_id"] = str(triage_setting_dict["practice_id"])

    return triage_setting_dict


def update_triage_settings(practice_id: str, primary_color: str, show_page_runner: bool, show_requested_date: bool):
    triage_setting = TriageSettings.objects(practice_id=practice_id).first()

    if not triage_setting:
        newTriageSettings = TriageSettings(
            practice_id=practice_id, primary_color=primary_color, show_page_runner=show_page_runner, show_requested_date=show_requested_date
        )
        newTriageSettings.save()
        # raise HTTPException(status_code=404, detail="No triage setting document found")

    else:
        triage_setting.primary_color = primary_color
        triage_setting.show_page_runner = show_page_runner
        triage_setting.show_requested_date = show_requested_date
        triage_setting.save()
