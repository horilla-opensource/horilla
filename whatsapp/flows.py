import json

from asset.models import AssetCategory
from base.models import Department, EmployeeShift, JobPosition, Tags, WorkType
from employee.models import Employee
from helpdesk.models import TicketType
from leave.models import LeaveType


def get_asset_category_flow_json():

    flow_json = {
        "version": "7.3",
        "screens": [
            {
                "id": "screen_one",
                "title": "Asset Request",
                "terminal": True,
                "data": {
                    "asset_categories": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                            },
                            "required": ["id", "title"],
                        },
                        "__example__": [
                            {"id": "1", "title": "Laptops"},
                            {"id": "2", "title": "Bags"},
                        ],
                    }
                },
                "layout": {
                    "type": "SingleColumnLayout",
                    "children": [
                        {
                            "type": "Form",
                            "name": "flow_path",
                            "children": [
                                {
                                    "type": "Dropdown",
                                    "label": "Asset Category",
                                    "required": True,
                                    "name": "asset_category",
                                    "data-source": "${data.asset_categories}",
                                },
                                {
                                    "type": "TextArea",
                                    "label": "Description",
                                    "required": True,
                                    "name": "description",
                                },
                                {
                                    "type": "Footer",
                                    "label": "Save",
                                    "on-click-action": {
                                        "name": "complete",
                                        "payload": {
                                            "asset_category": "${form.asset_category}",
                                            "description": "${form.description}",
                                            "type": "asset_request",
                                        },
                                    },
                                },
                            ],
                        }
                    ],
                },
            }
        ],
    }

    return flow_json


def get_attendance_request_json():

    flow_json = {
        "version": "7.3",
        "screens": [
            {
                "id": "screen_one",
                "title": "Attendance Request 1 of 2",
                "data": {
                    "shift": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                            },
                            "required": ["id", "title"],
                        },
                        "__example__": [
                            {"id": "1", "title": "Regular Shift"},
                            {"id": "2", "title": "Morning Shift"},
                            {"id": "3", "title": "Night Shift"},
                        ],
                    },
                    "work_type": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                            },
                            "required": ["id", "title"],
                        },
                        "__example__": [
                            {"id": "1", "title": "WFH"},
                            {"id": "2", "title": "WFO"},
                        ],
                    },
                },
                "layout": {
                    "type": "SingleColumnLayout",
                    "children": [
                        {
                            "type": "Form",
                            "name": "flow_path",
                            "children": [
                                {
                                    "type": "DatePicker",
                                    "label": "Attendance Date",
                                    "required": True,
                                    "name": "attendance_date",
                                },
                                {
                                    "type": "Dropdown",
                                    "label": "Shift",
                                    "required": True,
                                    "name": "shift",
                                    "data-source": "${data.shift}",
                                },
                                {
                                    "type": "Dropdown",
                                    "label": "Work Type",
                                    "required": True,
                                    "name": "work_type",
                                    "data-source": "${data.work_type}",
                                },
                                {
                                    "type": "TextArea",
                                    "label": "Request Description",
                                    "required": True,
                                    "name": "description",
                                },
                                {
                                    "type": "Footer",
                                    "label": "Continue",
                                    "on-click-action": {
                                        "name": "navigate",
                                        "next": {
                                            "type": "screen",
                                            "name": "screen_two",
                                        },
                                        "payload": {
                                            "attendance_date": "${form.attendance_date}",
                                            "shift": "${form.shift}",
                                            "work_type": "${form.work_type}",
                                            "description": "${form.description}",
                                        },
                                    },
                                },
                            ],
                        }
                    ],
                },
            },
            {
                "id": "screen_two",
                "title": "Attendance Request 2 of 2",
                "data": {
                    "attendance_date": {"type": "string", "__example__": "Example"},
                    "shift": {"type": "string", "__example__": "Example"},
                    "work_type": {"type": "string", "__example__": "Example"},
                    "description": {"type": "string", "__example__": "Example"},
                },
                "terminal": True,
                "layout": {
                    "type": "SingleColumnLayout",
                    "children": [
                        {
                            "type": "Form",
                            "name": "flow_path",
                            "children": [
                                {
                                    "type": "DatePicker",
                                    "label": "Check In Date",
                                    "required": True,
                                    "name": "check_in_date",
                                },
                                {
                                    "type": "TextInput",
                                    "label": "Check In Time",
                                    "name": "check_in_time",
                                    "required": True,
                                    "input-type": "text",
                                    "helper-text": "Check in time in HH:MM:SS (24 HRS format)",
                                },
                                {
                                    "type": "DatePicker",
                                    "label": "Check Out Date",
                                    "required": True,
                                    "name": "check_out_date",
                                },
                                {
                                    "type": "TextInput",
                                    "label": "Check Out Time",
                                    "name": "check_out_time",
                                    "required": True,
                                    "input-type": "text",
                                    "helper-text": "Check out time in HH:MM:SS (24 HRS format)",
                                },
                                {
                                    "type": "TextInput",
                                    "label": "Worked Hours",
                                    "name": "worked_hours",
                                    "required": True,
                                    "input-type": "text",
                                    "helper-text": "Worked hours in HH:MM",
                                },
                                {
                                    "type": "TextInput",
                                    "label": "Minimum Hours",
                                    "name": "minimum_hours",
                                    "required": True,
                                    "input-type": "text",
                                    "helper-text": "Minimum hours in HH:MM",
                                },
                                {
                                    "type": "Footer",
                                    "label": "Continue",
                                    "on-click-action": {
                                        "name": "complete",
                                        "payload": {
                                            "check_in_date": "${form.check_in_date}",
                                            "check_in_time": "${form.check_in_time}",
                                            "check_out_date": "${form.check_out_date}",
                                            "check_out_time": "${form.check_out_time}",
                                            "worked_hours": "${form.worked_hours}",
                                            "minimum_hours": "${form.minimum_hours}",
                                            "attendance_date": "${data.attendance_date}",
                                            "shift": "${data.shift}",
                                            "work_type": "${data.work_type}",
                                            "description": "${data.description}",
                                            "type": "attendance_request",
                                        },
                                    },
                                },
                            ],
                        }
                    ],
                },
            },
        ],
    }

    return flow_json


def get_shift_request_json():

    flow_json = {
        "version": "7.3",
        "screens": [
            {
                "id": "screen_one",
                "title": "Shift Request",
                "terminal": True,
                "data": {
                    "shift": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                            },
                            "required": ["id", "title"],
                        },
                        "__example__": [
                            {"id": "1", "title": "Regular Shift"},
                            {"id": "2", "title": "Morning Shift"},
                            {"id": "3", "title": "Night Shift"},
                        ],
                    }
                },
                "layout": {
                    "type": "SingleColumnLayout",
                    "children": [
                        {
                            "type": "Form",
                            "name": "flow_path",
                            "children": [
                                {
                                    "type": "Dropdown",
                                    "label": "Shift",
                                    "name": "shift",
                                    "required": True,
                                    "data-source": "${data.shift}",
                                },
                                {
                                    "type": "DatePicker",
                                    "label": "Requested Date",
                                    "name": "requested_date",
                                    "required": True,
                                },
                                {
                                    "type": "DatePicker",
                                    "label": "Requested Till",
                                    "name": "requested_till",
                                    "required": True,
                                },
                                {
                                    "type": "TextArea",
                                    "label": "Description",
                                    "name": "description",
                                    "required": True,
                                },
                                {
                                    "type": "OptIn",
                                    "label": "permentent request",
                                    "name": "permenent_request",
                                    "required": False,
                                },
                                {
                                    "type": "Footer",
                                    "label": "Save",
                                    "on-click-action": {
                                        "name": "complete",
                                        "payload": {
                                            "shift": "${form.shift}",
                                            "requested_date": "${form.requested_date}",
                                            "requested_till": "${form.requested_till}",
                                            "description": "${form.description}",
                                            "permanent": "${form.permenent_request}",
                                            "type": "shift_request",
                                        },
                                    },
                                },
                            ],
                        }
                    ],
                },
            }
        ],
    }

    return flow_json


def get_work_type_request_json():

    flow_json = {
        "version": "7.3",
        "screens": [
            {
                "id": "screen_one",
                "title": "Work Type Request",
                "terminal": True,
                "data": {
                    "work_type": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                            },
                            "required": ["id", "title"],
                        },
                        "__example__": [
                            {"id": "1", "title": "WFO"},
                            {"id": "2", "title": "WFH"},
                        ],
                    }
                },
                "layout": {
                    "type": "SingleColumnLayout",
                    "children": [
                        {
                            "type": "Form",
                            "name": "flow_path",
                            "children": [
                                {
                                    "type": "Dropdown",
                                    "label": "work type",
                                    "required": True,
                                    "name": "work_type",
                                    "data-source": "${data.work_type}",
                                },
                                {
                                    "type": "DatePicker",
                                    "label": "Requested date",
                                    "required": True,
                                    "name": "request_date",
                                },
                                {
                                    "type": "DatePicker",
                                    "label": "requested till",
                                    "required": True,
                                    "name": "requested_till",
                                },
                                {
                                    "type": "TextArea",
                                    "label": "description",
                                    "required": True,
                                    "name": "description",
                                },
                                {
                                    "type": "OptIn",
                                    "label": "permentent request",
                                    "required": False,
                                    "name": "permenent_request",
                                },
                                {
                                    "type": "Footer",
                                    "label": "Save",
                                    "on-click-action": {
                                        "name": "complete",
                                        "payload": {
                                            "work_type": "${form.work_type}",
                                            "requested_date": "${form.request_date}",
                                            "requested_till": "${form.requested_till}",
                                            "description": "${form.description}",
                                            "permenent_request": "${form.permenent_request}",
                                            "type": "work_type",
                                        },
                                    },
                                },
                            ],
                        }
                    ],
                },
            }
        ],
    }

    return flow_json


def get_leave_request_json():

    flow_json = {
        "version": "7.3",
        "screens": [
            {
                "id": "screen_one",
                "title": "Leave request",
                "terminal": True,
                "data": {
                    "leave_types": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                            },
                            "required": ["id", "title"],
                        },
                        "__example__": [
                            {"id": "1", "title": "Casual Leave"},
                            {"id": "2", "title": "Sick Leave"},
                            {"id": "3", "title": "Paid Leave"},
                        ],
                    }
                },
                "layout": {
                    "type": "SingleColumnLayout",
                    "children": [
                        {
                            "type": "Form",
                            "name": "flow_path",
                            "children": [
                                {
                                    "type": "Dropdown",
                                    "label": "Leave type",
                                    "required": True,
                                    "name": "leave_type",
                                    "data-source": "${data.leave_types}",
                                },
                                {
                                    "type": "DatePicker",
                                    "label": "Start Date",
                                    "required": True,
                                    "name": "start_date",
                                },
                                {
                                    "type": "Dropdown",
                                    "label": "Start Date breakdown",
                                    "required": True,
                                    "name": "start_date_breakdown",
                                    "data-source": [
                                        {"id": "full_day", "title": "Full day"},
                                        {"id": "first_half", "title": "First half"},
                                        {"id": "second_half", "title": "Second Half"},
                                    ],
                                },
                                {
                                    "type": "DatePicker",
                                    "label": "End Date",
                                    "required": True,
                                    "name": "end_date",
                                },
                                {
                                    "type": "Dropdown",
                                    "label": "End Date Breakdown",
                                    "required": True,
                                    "name": "end_date_breakdown",
                                    "data-source": [
                                        {"id": "full_day", "title": "Full Day"},
                                        {"id": "first_half", "title": "First Half"},
                                        {"id": "second_half", "title": "Second Half"},
                                    ],
                                },
                                {
                                    "type": "DocumentPicker",
                                    "name": "document_picker",
                                    "label": "Upload photos",
                                    "description": "Please attach images about the received items",
                                    "max-file-size-kb": 10240,
                                    "max-uploaded-documents": 1,
                                },
                                {
                                    "type": "TextArea",
                                    "label": "Description",
                                    "required": True,
                                    "name": "description",
                                },
                                {
                                    "type": "Footer",
                                    "label": "Save",
                                    "on-click-action": {
                                        "name": "complete",
                                        "payload": {
                                            "leave_type": "${form.leave_type}",
                                            "start_date": "${form.start_date}",
                                            "start_date_breakdown": "${form.start_date_breakdown}",
                                            "end_date": "${form.end_date}",
                                            "end_date_breakdown": "${form.end_date_breakdown}",
                                            "description": "${form.description}",
                                            "document_picker": "${form.document_picker}",
                                            "type": "leave_request",
                                        },
                                    },
                                },
                            ],
                        }
                    ],
                },
            }
        ],
    }

    return flow_json


def get_reimbursement_request_json():

    flow_json = {
        "version": "7.3",
        "screens": [
            {
                "id": "screen_one",
                "title": "Reimbursements",
                "data": {},
                "terminal": True,
                "layout": {
                    "type": "SingleColumnLayout",
                    "children": [
                        {
                            "type": "Form",
                            "name": "flow_path",
                            "children": [
                                {
                                    "type": "TextInput",
                                    "label": "Title",
                                    "name": "title",
                                    "required": True,
                                    "input-type": "text",
                                },
                                {
                                    "type": "DatePicker",
                                    "label": "Allowance on",
                                    "required": True,
                                    "name": "allowance_date",
                                },
                                {
                                    "type": "TextInput",
                                    "label": "Amount",
                                    "name": "amount",
                                    "required": True,
                                    "input-type": "number",
                                },
                                {
                                    "type": "DocumentPicker",
                                    "name": "document_picker",
                                    "label": "Upload photos",
                                    "description": "Please attach images about the received items",
                                    "max-file-size-kb": 10240,
                                    "max-uploaded-documents": 10,
                                },
                                {
                                    "type": "TextArea",
                                    "label": "description",
                                    "required": True,
                                    "name": "description",
                                },
                                {
                                    "type": "Footer",
                                    "label": "Save",
                                    "on-click-action": {
                                        "name": "complete",
                                        "payload": {
                                            "title": "${form.title}",
                                            "allowance_date": "${form.allowance_date}",
                                            "document_picker": "${form.document_picker}",
                                            "amount": "${form.amount}",
                                            "description": "${form.description}",
                                            "type": "reimbursement",
                                        },
                                    },
                                },
                            ],
                        }
                    ],
                },
            }
        ],
    }

    return flow_json


def get_bonus_point_json():

    flow_json = {
        "version": "7.3",
        "screens": [
            {
                "id": "screen_one",
                "title": "Bonus Point",
                "data": {},
                "terminal": True,
                "layout": {
                    "type": "SingleColumnLayout",
                    "children": [
                        {
                            "type": "Form",
                            "name": "flow_path",
                            "children": [
                                {
                                    "type": "TextInput",
                                    "label": "Title",
                                    "name": "title",
                                    "required": True,
                                    "input-type": "text",
                                },
                                {
                                    "type": "DatePicker",
                                    "label": "Allowance on",
                                    "required": True,
                                    "name": "allowance_on",
                                },
                                {
                                    "type": "TextInput",
                                    "label": "Bonus Points",
                                    "name": "bonus_point",
                                    "required": True,
                                    "input-type": "number",
                                },
                                {
                                    "type": "TextArea",
                                    "label": "description",
                                    "required": True,
                                    "name": "description",
                                },
                                {
                                    "type": "Footer",
                                    "label": "Save",
                                    "on-click-action": {
                                        "name": "complete",
                                        "payload": {
                                            "title": "${form.title}",
                                            "allowance_on": "${form.allowance_on}",
                                            "bonus_point": "${form.bonus_point}",
                                            "description": "${form.description}",
                                            "type": "bonus_point",
                                        },
                                    },
                                },
                            ],
                        }
                    ],
                },
            }
        ],
    }

    return flow_json


def get_ticket_json():

    ticket_type_data = [
        {"id": str(ticket_type.id), "title": ticket_type.title}
        for ticket_type in TicketType.objects.all()
    ]

    priority_data = [
        {"id": "low", "title": "Low"},
        {"id": "medium", "title": "Medium"},
        {"id": "high", "title": "High"},
    ]

    assigning_type_data = [
        {"id": "department", "title": "Department"},
        {"id": "job_position", "title": "Job Position"},
        {"id": "individual", "title": "Individual"},
    ]

    department_data = [
        {"id": str(department.id), "title": department.department}
        for department in Department.objects.all()
    ]

    job_position_data = [
        {"id": str(job_position.id), "title": job_position.job_position}
        for job_position in JobPosition.objects.all()
    ]

    individual_data = [
        {"id": str(individual.id), "title": individual.get_full_name()}
        for individual in Employee.objects.all()
    ]

    tags_data = [{"id": str(tag.id), "title": tag.title} for tag in Tags.objects.all()]

    flow_json = {
        "version": "7.3",
        "screens": [
            {
                "id": "screen_one",
                "title": "Raise Ticket 1 of 2",
                "data": {},
                "layout": {
                    "type": "SingleColumnLayout",
                    "children": [
                        {
                            "type": "Form",
                            "name": "flow_path",
                            "children": [
                                {
                                    "type": "TextInput",
                                    "name": "title",
                                    "label": "Title",
                                    "required": True,
                                    "input-type": "text",
                                },
                                {
                                    "type": "Dropdown",
                                    "label": "Ticket Type",
                                    "required": True,
                                    "name": "ticket_type",
                                    "data-source": ticket_type_data,
                                },
                                {
                                    "type": "Dropdown",
                                    "label": "Priority",
                                    "required": True,
                                    "name": "priority",
                                    "data-source": priority_data,
                                },
                                {
                                    "type": "TextArea",
                                    "label": "description",
                                    "required": True,
                                    "name": "description",
                                },
                                {
                                    "type": "Footer",
                                    "label": "Continue",
                                    "on-click-action": {
                                        "name": "navigate",
                                        "next": {
                                            "type": "screen",
                                            "name": "screen_quhode",
                                        },
                                        "payload": {
                                            "title": "${form.title}",
                                            "ticket_type": "${form.ticket_type}",
                                            "priority": "${form.priority}",
                                            "description": "${form.description}",
                                        },
                                    },
                                },
                            ],
                        }
                    ],
                },
            },
            {
                "id": "screen_two",
                "title": "Raise Ticket 2 of 2",
                "data": {
                    "title": {
                        "type": "string",
                        "__example__": "Example",
                    },
                    "ticket_type": {"type": "string", "__example__": "Example"},
                    "priority": {"type": "string", "__example__": "Example"},
                    "description": {"type": "string", "__example__": "Example"},
                },
                "terminal": True,
                "layout": {
                    "type": "SingleColumnLayout",
                    "children": [
                        {
                            "type": "Form",
                            "name": "flow_path",
                            "children": [
                                {
                                    "type": "Dropdown",
                                    "label": "Assigning Type",
                                    "required": True,
                                    "name": "assigning_type",
                                    "data-source": assigning_type_data,
                                },
                                {
                                    "type": "Dropdown",
                                    "label": "Forward To",
                                    "required": True,
                                    "name": "forward_to",
                                    "data-source": [
                                        {"id": "0_Option_1", "title": "Option 1"},
                                        {"id": "1_Option_2", "title": "Option 2"},
                                    ],
                                },
                                {
                                    "type": "DatePicker",
                                    "label": "Deadline",
                                    "required": True,
                                    "name": "deadline",
                                },
                                {
                                    "type": "Dropdown",
                                    "label": "Tags",
                                    "required": False,
                                    "name": "tags",
                                    "data-source": tags_data,
                                },
                                {
                                    "type": "Footer",
                                    "label": "Save",
                                    "on-click-action": {
                                        "name": "complete",
                                        "payload": {
                                            "screen_1_Dropdown_0": "${form.assigning_type}",
                                            "screen_1_Dropdown_1": "${form.forward_to}",
                                            "screen_1_DatePicker_2": "${form.deadline}",
                                            "screen_1_Dropdown_3": "${form.tags}",
                                            "title": "${data.title}",
                                            "ticket_type": "${data.ticket_type}",
                                            "priority": "${data.priority}",
                                            "description": "${data.description}",
                                            "type": "ticket",
                                        },
                                    },
                                },
                            ],
                        }
                    ],
                },
            },
        ],
    }
    return json.dumps(flow_json)
