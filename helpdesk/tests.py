from django.test import TestCase

# Create your tests here.









       
@login_required
def comment_edit(request):
    comment_id = request.POST.get('comment_id')
    new_comment = request.POST.get('new_comment')
    print(new_comment)
    if len(new_comment)>1:
        comment = Comment.objects.get(id=comment_id)
        comment.comment = new_comment
        comment.save()
        messages.success(request,_('The comment updated successfully.'))

    else:
        messages.error(request,_('The comment needs to be atleast 2 charactors.'))
    response= {
        "errors": 'no_error',
    }
    return JsonResponse(response)


@login_required
def comment_delete(request,comment_id):
    comment = Comment.objects.get(id=comment_id)
    comment.delete()
    messages.success(request,_('The comment "{}" has been deleted successfully.').format(comment))

    return  HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))