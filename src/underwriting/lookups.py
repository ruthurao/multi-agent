_CLAIMS = {
    "APP-1001": {"at_fault": 0, "not_at_fault": 0, "total_loss": False, "dui_related": False},
    "APP-1002": {"at_fault": 1, "not_at_fault": 0, "total_loss": False, "dui_related": False},
    "APP-1003": {"at_fault": 2, "not_at_fault": 0, "total_loss": True, "dui_related": True},
    "APP-1004": {"at_fault": 0, "not_at_fault": 0, "total_loss": False, "dui_related": False},
}

_CREDIT = {
    "APP-1001": {"band": "excellent"},
    "APP-1002": {"band": "fair"},
    "APP-1003": {"band": "poor"},
    "APP-1004": {"band": "excellent"},
}

_ASSETS = {
    "APP-1001": {"flood_zone": "X", "roof_year": 2019, "unpermitted_structure": False, "prior_damage": False},
    "APP-1002": {"flood_zone": "X", "roof_year": 2016, "unpermitted_structure": False, "prior_damage": True},
    "APP-1003": {"flood_zone": "AE", "roof_year": 2012, "unpermitted_structure": False, "prior_damage": False},
    "APP-1004": {"flood_zone": "X", "roof_year": 2019, "unpermitted_structure": False, "prior_damage": False},
}


def claims(applicant_id):
    return dict(_CLAIMS[applicant_id])


def credit(applicant_id):
    return dict(_CREDIT[applicant_id])


def assets(applicant_id):
    return dict(_ASSETS[applicant_id])
