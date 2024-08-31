"""Module for handling attendance error data."""


def handle_attendance_errors(error_list):
    """
    Reorganize a list of error dictionaries into a structured error data dictionary
    and remove keys with all None values.

    Parameters:
        error_list (list of dict): A list of dictionaries containing error details.

    Returns:
        dict: A structured dictionary where keys represent error types and values are lists
              of error details for each type.
    """
    keys_to_remove = []
    error_data = {
        "Badge ID": [],
        "Shift": [],
        "Work type": [],
        "Attendance date": [],
        "Check-in date": [],
        "Check-in": [],
        "Check-out date": [],
        "Check-out": [],
        "Worked hour": [],
        "Minimum hour": [],
        "Badge ID Error": [],
        "Shift Error": [],
        "Work Type Error": [],
        "Check-in Validation Error": [],
        "Check-out Validation Error": [],
        "Attendance Error": [],
        "Attendance Date Validation Error": [],
        "Check-in Error": [],
        "Check-out Error": [],
        "Worked Hours Error": [],
        "Minimum Hour Error": [],
        "Attendance Date Error": [],
        "Check-out Date Error": [],
        "Check-out Date Error": [],
        "Other Errors": [],
    }
    for item in error_list:
        for key, value in error_data.items():
            if key in item:
                value.append(item[key])
            else:
                value.append(None)

    keys_to_remove = [
        key for key, value in error_data.items() if all(v is None for v in value)
    ]

    for key in keys_to_remove:
        del error_data[key]

    return error_data
