from django.contrib import admin
from . models import Comment,EmployeeKeyResult,Period,EmployeeObjective
from . models import Question,QuestionTemplate,Feedback,Answer,KeyresultFeedback, QuestionOptions
from .models import EmployeeObjective
from simple_history.admin import SimpleHistoryAdmin


# Register your models here.

objective = [Period]
feedback = [ Question,QuestionTemplate,Feedback,Answer, QuestionOptions]
admin.site.register(EmployeeObjective,SimpleHistoryAdmin)
admin.site.register(EmployeeKeyResult,SimpleHistoryAdmin)
admin.site.register(objective)
admin.site.register(feedback)
admin.site.register(KeyresultFeedback)
admin.site.register(Comment,SimpleHistoryAdmin)








