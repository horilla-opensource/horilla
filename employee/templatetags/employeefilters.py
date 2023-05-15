from django.template.defaultfilters import register
from django import template
from django.contrib.auth.models import User

register = template.Library()



def changed_field(fields):
    changed_fields = ''
    for field in fields:
        changed_fields = changed_fields + f'''
                <div class="field mb-2 {field}">{field}</div>
        '''.strip()
    return changed_fields

def old_value(fields,old_record):
    old_values = [getattr(old_record, field) for field in fields]
    values = ''
    for value in old_values:
        values = f'''{values}
            <div class='old_values mb-2 '>{value}</div>
        '''
    return values

def new_value(fields,new_value):
    new_values = [getattr(new_value, field) for field in fields]
    values = ''
    for value in new_values:
        values = f'''{values}
            <div class='new_value mb-2'>{value}</div>
        '''
    return values

@register.filter(name='history')
def history(history):
    length = len(history)
    if length >= 2:
        flag = 0
        html = []
        for hist in history:
            if flag < length-1:
                next_hist = history[flag+1]
                delta = hist.diff_against(next_hist)
                changed_fields= delta.changed_fields
                old_record = delta.old_record
                new_record = delta.new_record
                html.append(
                    f'''
                        <tr>
                            <td>{changed_field(changed_fields)}</td>
                            <td>{old_value(changed_fields,old_record)}</td>
                            <td>{new_value(changed_fields,new_record)}</td>
                            <td class="align-middle"><div class="history-date">{hist.history_date}</div></td>
                            <td class="align-middle"><div class="changed-by ">{User.objects.get(id=hist.history_user_id).employee_get}</div></td>
                        </tr>
                    '''
                )
            flag = flag + 1
        return html
    

    
@register.filter(name='options_get')
def options_get(opt):
    return opt.__dict__['form'].fields[opt.name].__dict__['_queryset']

