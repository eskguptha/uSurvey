import json

from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from survey.interviewer_configs import *
from survey.models import HouseholdMemberGroup, QuestionModule
from survey.models import Survey, Location, LocationType
from survey.models import Survey, Batch, QuestionTemplate
from survey.models.batch import Batch
from survey.forms.batch import BatchForm, BatchQuestionsForm


@login_required
@permission_required('auth.can_view_batches')
def index(request, survey_id):
    survey = Survey.objects.get(id=survey_id)
    batches = Batch.objects.filter(survey__id=survey_id)
    if request.is_ajax():
        batches = batches.values('id', 'name').order_by('name')
        json_dump = json.dumps(list(batches), cls=DjangoJSONEncoder)
        return HttpResponse(json_dump, mimetype='application/json')
    request.breadcrumbs([
        ('Surveys', reverse('survey_list_page')),
    ])
    context = {'batches': batches, 'survey': survey,
               'request': request, 'batchform': BatchForm(instance=Batch(survey=survey)),
               'action': '/surveys/%s/batches/new/' % survey_id, }
    return render(request, 'batches/index.html',
                  context)


@login_required
@permission_required('auth.can_view_batches')
def show(request, survey_id, batch_id):
    batch = Batch.objects.get(id=batch_id)
    prime_location_type = LocationType.largest_unit()
    locations = Location.objects.filter(type=prime_location_type).order_by('name')
    batch_location_ids = batch.open_locations.values_list('location_id', flat=True)
    open_locations = Location.objects.filter(id__in=batch_location_ids)
    if request.GET.has_key('status'):
        if request.GET['status'] == 'open':
            locations = locations.filter(id__in=batch_location_ids)       
        else:
            locations = locations.exclude(id__in=batch_location_ids)     
    request.breadcrumbs([
        ('Surveys', reverse('survey_list_page')),
        (batch.survey.name, reverse('batch_index_page', args=(batch.survey.pk, ))),
#         (_('%s %s') % (action.title(),model.title()),'/crud/%s/%s' % (model,action)),
    ])
#     import pdb; pdb.set_trace()  
    context = {'batch': batch,
               'locations': locations,
               'open_locations': open_locations,
               'all_locations' : Location.objects.exclude(parent=None),
               'non_response_active_locations': batch.get_non_response_active_locations()}
    return render(request, 'batches/show.html', context)

@login_required
@permission_required('auth.can_view_batches')
def all_locs(request, batch_id):
    batch = Batch.objects.get(id=batch_id)
    action = request.POST['action']
    locations = Location.objects.filter(type=LocationType.largest_unit()).order_by('name')
    if action.lower() == 'open all':
        for location in locations:
            batch.open_for_location(location)
    if action.lower() == 'close all':
        for location in locations:
            batch.close_for_location(location)
    return HttpResponseRedirect(reverse('batch_show_page', args=(batch.survey.id, batch_id, )))

@login_required
@permission_required('auth.can_view_batches')
def open(request, batch_id):
    batch = Batch.objects.get(id=batch_id)
    location = Location.objects.get(id=request.POST['location_id'])
    other_surveys = batch.other_surveys_with_open_batches_in(location)
    batch.open_for_location(location)
    return HttpResponse(json.dumps(""), content_type="application/json")


@login_required
@permission_required('auth.can_view_batches')
def close(request, batch_id):
    batch = Batch.objects.get(id=batch_id)
    location = Location.objects.get(id=request.POST['location_id'])
    batch.close_for_location(location)
    return HttpResponse(json.dumps(""), content_type="application/json")


@login_required
@permission_required('auth.can_view_batches')
def new(request, survey_id):
    survey=Survey.objects.get(id=survey_id)
    batch_form = BatchForm(initial={'survey' : survey})
    response, batchform = _process_form(request, survey_id, action_str='added')
    request.breadcrumbs([
        ('Surveys', reverse('survey_list_page')),
        (batch.survey.name, reverse('batch_index_page', args=(batch.survey.pk, ))),
#         (_('%s %s') % (action.title(),model.title()),'/crud/%s/%s' % (model,action)),
    ])
    context = {'batchform': batchform, 'button_label': "Create", 'id': 'add-batch-form', 'title': 'New Batch',
               'action': '/surveys/%s/batches/new/' % survey_id, 'cancel_url': '/surveys/'}
    return response or render(request, 'batches/new.html', context)


def _process_form(request, survey_id, instance=None, action_str='edited'):
    batch_form = BatchForm(instance=instance)
    response = None
    if request.method == 'POST':
        batch_form = BatchForm(data=request.POST, instance=instance)
        if batch_form.is_valid():
            batch_form.save(**request.POST)
            messages.success(request, 'Question successfully %sed.' % action_str)
            response = HttpResponseRedirect(reverse('batch_index_page', args=(survey_id,)))
        else:
            messages.error(request, 'Question was not %sed.' % action_str)
    return response, batch_form



@permission_required('auth.can_view_batches')
def edit(request, survey_id, batch_id):
    batch = Batch.objects.get(id=batch_id, survey__id=survey_id)
    response, batchform = _process_form(request, survey_id, instance=batch, action_str='edited')
    request.breadcrumbs([
        ('Surveys', reverse('survey_list_page')),
        (batch.survey.name, reverse('batch_index_page', args=(batch.survey.pk, ))),
#         (_('%s %s') % (action.title(),model.title()),'/crud/%s/%s' % (model,action)),
    ])
    context = {'batchform': batchform, 'button_label': "Save", 'id': 'edit-batch-form', 'title': 'Edit Batch',
               'action': '/surveys/%s/batches/%s/edit/' % (survey_id, batch.id)}
    return response or render(request, 'batches/new.html', context)


def _add_success_message(request, action_str):
    messages.success(request, 'Batch successfully %s.' % action_str)


@permission_required('auth.can_view_batches')
def delete(request, survey_id, batch_id):
    batch = Batch.objects.get(id=batch_id)
    can_be_deleted, message = batch.can_be_deleted()
    if not can_be_deleted:
        messages.error(request, message)
    else:
        batch.delete()
        _add_success_message(request, 'deleted')
    return HttpResponseRedirect(reverse('batch_index_page', args=(survey_id,)))


@permission_required('auth.can_view_batches')
def assign(request, batch_id):
    batch = Batch.objects.get(id=batch_id)
    
    if batch.is_open():
        error_message = "Questions cannot be assigned to open batch: %s." % batch.name.capitalize()
        messages.error(request, error_message)
        return HttpResponseRedirect("/batches/%s/questions/" % batch_id)
    
    batch_questions_form = BatchQuestionsForm(batch=batch)
    batch = Batch.objects.get(id=batch_id)
    groups = HouseholdMemberGroup.objects.all()
    if request.method == 'POST':
        batch_questions_form = BatchQuestionsForm(batch=batch, data=request.POST, instance=batch)
        if batch_questions_form.is_valid():
            batch_question_form.save()
            success_message = "Questions successfully assigned to batch: %s." % batch.name.capitalize()
            messages.success(request, success_message)
            return HttpResponseRedirect("/batches/%s/questions/" % batch_id)
    all_modules = QuestionModule.objects.all()
    used_identifiers = [question.identifier for question in batch.batch_questions.all()]
    library_questions = QuestionTemplate.objects.exclude(identifier__in=used_identifiers)
    request.breadcrumbs([
        ('Surveys', reverse('survey_list_page')),
        (batch.survey.name, reverse('batch_index_page', args=(batch.survey.pk, ))),
#         (_('%s %s') % (action.title(),model.title()),'/crud/%s/%s' % (model,action)),
    ])
    context = {'batch_questions_form': unicode(batch_questions_form), 'batch': batch,
               'button_label': 'Save', 'id': 'assign-question-to-batch-form', 'groups': groups,
               'library_questions' : library_questions,
               'modules': all_modules}
#    import pdb;pdb.set_trace()
    return render(request, 'batches/assign.html',
                  context)


@permission_required('auth.can_view_batches')
def update_orders(request, batch_id):
    batch = Batch.objects.get(id=batch_id)
    new_orders = request.POST.getlist('order_information', None)
    if len(new_orders) > 0:
        for new_order in new_orders:
            print 'this order', new_order
            BatchQuestionOrder.update_question_order(new_order, batch)
        success_message = "Question orders successfully updated for batch: %s." % batch.name.capitalize()
        messages.success(request, success_message)
    else:
        messages.error(request, 'No questions orders were updated.')
    return HttpResponseRedirect("/batches/%s/questions/" % batch_id)


@login_required
def check_name(request, survey_id):
    response = Batch.objects.filter(name=request.GET['name'], survey__id=survey_id).exists()
    return HttpResponse(json.dumps(not response), content_type="application/json")


@permission_required('auth.can_view_batches')
def list_batches(request):
    if request.is_ajax():
        batches = Batch.objects.values('id', 'name').order_by('name')
        json_dump = json.dumps(list(batches), cls=DjangoJSONEncoder)
        return HttpResponse(json_dump, mimetype='application/json')
    request.breadcrumbs([
        ('Surveys', reverse('survey_list_page')),
    ])
    return render(request, 'layout.html')


def activate_non_response(request, batch_id):
    batch = Batch.objects.get(id=batch_id)
    location = Location.objects.get(id=request.POST['non_response_location_id'])
    if batch.is_open_for(location):
        batch.activate_non_response_for(location)
        return HttpResponse(json.dumps(""), content_type="application/json")
    message = "%s is not open for %s" % (batch.name, location.name)
    return HttpResponse(json.dumps(message), content_type="application/json")


def deactivate_non_response(request, batch_id):
    batch = Batch.objects.get(id=batch_id)
    location = Location.objects.get(id=request.POST['non_response_location_id'])
    if batch.is_open_for(location):
        batch.deactivate_non_response_for(location)
    return HttpResponse(json.dumps(""), content_type="application/json")
