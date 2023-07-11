from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime,date, timedelta
from dateutil.relativedelta import relativedelta
import calendar

today = datetime.now()
 
def leave_reset():      
    from leave.models import LeaveType
    leave_types = LeaveType.objects.filter(reset=True)
    #Looping through filtered leave types with reset is true
    for leave_type in leave_types:
        reset_based = leave_type.reset_based
        reset_month = leave_type.reset_month
        reset_day = leave_type.reset_day
        reset_weekend = leave_type.reset_weekend
        reset_date = ""
        #Checking that reset based is yearly
        if reset_based == 'monthly':
            if reset_day == "last day":
                reset_day = calendar.monthrange(today.year, today.month)[1]
            reset_date = date(today.year,today.month,int(reset_day))

        elif reset_based == 'weekly':
            if today.weekday() == int(reset_weekend):
                reset_date = today.date()

        elif reset_based == "yearly":
            if reset_day == "last day":
                reset_day = calendar.monthrange(today.year, int(reset_month))[1]
            reset_date = date(today.year,int(reset_month),int(reset_day))
        #Checking that reset date is today
        if reset_date == today.date():     

            available_leaves = leave_type.employee_available_leave.all()

            #Looping through all available leaves
            for available_leave in available_leaves:
                carryforward_type = leave_type.carryforward_type
                carryforward_max = leave_type.carryforward_max
                carryforward_expire_in = leave_type.carryforward_expire_in
                assigned_date = available_leave.assigned_date
                carryforward_date = ""

                #Cheking if carryforward type is carryforward or carryforward expire
                if (
                    carryforward_type
                    in ['carryforward', 'carryforward expire']
                    and available_leave.carryforward_days < carryforward_max
                ):
                    if carryforward_max > available_leave.available_days + available_leave.carryforward_days:
                        available_leave.carryforward_days += available_leave.available_days
                    else:
                        available_leave.carryforward_days  = carryforward_max

                #Checking if carryforward type is carryforward expire
                if carryforward_type == 'carryforward expire':          
                    carryforward_expire_period = leave_type.carryforward_expire_period
                    if carryforward_expire_period == "day":
                        carryforward_date = assigned_date + timedelta(days=carryforward_expire_in)


                    elif carryforward_expire_period == "month":
                        carryforward_date = assigned_date + relativedelta(months=1)
                    elif carryforward_expire_period == "year":
                        carryforward_date = assigned_date + timedelta(days=365*carryforward_expire_in)
                if carryforward_date == today.date():
                    available_leave.carryforward_days = 0

                available_leave.available_days = leave_type.total_days
                # available_leave.carryforward_days = leave_type.exceed_day
                available_leave.save()   


def recurring_holiday():
    from leave.models import Holiday
    recurring_holidays = Holiday.objects.filter(recurring = True)
    #Looping through all recurring holiday
    for recurring_holiday in recurring_holidays: 
        start_date = recurring_holiday.start_date
        end_date = recurring_holiday.end_date
        #Checking that end date is not none
        if end_date is None:
            #checking if that start date is day before today
            if start_date == (today - timedelta(days=1)).date(): 
                recurring_holiday.start_date = start_date + timedelta(days=365)
        elif end_date == (today - timedelta(days=1)).date(): 
            recurring_holiday.start_date = start_date + timedelta(days=365)
            recurring_holiday.end_date = end_date + timedelta(days=365)
        recurring_holiday.save()  
                           

    

scheduler = BackgroundScheduler()
scheduler.add_job(leave_reset, 'interval', seconds=10)  
scheduler.add_job(recurring_holiday, 'interval', seconds=10)

scheduler.start() 
