import json
import plotly.offline as opy
import plotly.graph_objs as go
from django import template
from django.utils.safestring import mark_safe
from django.utils.datastructures import SortedDict
from django.contrib import messages
from django.contrib.auth.decorators import permission_required, login_required
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from survey.models import LocationType, Location, MultiChoiceAnswer, Interview
from survey.forms.indicator import IndicatorForm, IndicatorVariableForm, IndicatorFormulaeForm
from survey.forms.filters import IndicatorFilterForm
from survey.models import Indicator, Survey, Answer, IndicatorVariable, IndicatorVariableCriteria
from survey.forms.enumeration_area import LocationsFilterForm


@login_required
@permission_required('auth.can_view_batches')
def new(request):
    indicator_form = IndicatorForm()
    if request.method == 'POST':
        indicator_form = IndicatorForm(request.POST)
        if indicator_form.is_valid():
            indicator_form.save()
            messages.success(request, "Indicator successfully created.")
            return HttpResponseRedirect(reverse('list_indicator_page'))
        messages.error(request, "Indicator was not created.")
    request.breadcrumbs([
        ('Indicators', reverse('list_indicator_page')),
    ])

    return render(request, 'indicator/new.html',
                  {'indicator_form': indicator_form, 'title': 'Add Indicator', 'button_label': 'Create',
                   'cancel_url': reverse('list_indicator_page'), 'action': '/indicators/new/',
                   'variable_form': IndicatorVariableForm(None)})


@login_required
def edit(request, indicator_id):
    indicator = Indicator.objects.get(id=indicator_id)
    indicator_form = IndicatorForm(instance=indicator)
    if request.method == 'POST':
        indicator_form = IndicatorForm(data=request.POST, instance=indicator)
        if indicator_form.is_valid():
            indicator_form.save()
            messages.success(request, "Indicator successfully edited.")
            return HttpResponseRedirect("/indicators/")
        messages.error(request, "Indicator was not successfully edited.")
    request.breadcrumbs([
        ('Indicators', reverse('list_indicator_page')),
    ])
    context = {'indicator_form': indicator_form, 'title': 'Edit Indicator',
               'button_label': 'Save', 'cancel_url': reverse('list_indicator_page'),
               'variable_form': IndicatorVariableForm(None)}
    return render(request, 'indicator/new.html', context)


def _process_form(indicator_filter_form, indicators):
    if indicator_filter_form.is_valid():
        survey_id = indicator_filter_form.cleaned_data['survey']
        batch_id = indicator_filter_form.cleaned_data['batch']
        module_id = indicator_filter_form.cleaned_data['module']
        if batch_id.isdigit() and module_id.isdigit():
            indicators = indicators.filter(batch=batch_id, module=module_id)
        elif not batch_id.isdigit() and module_id.isdigit():
            indicators = indicators.filter(module=module_id)
        elif batch_id.isdigit() and not module_id.isdigit():
            indicators = indicators.filter(batch__id=batch_id)
        elif survey_id.isdigit():
            batches = Survey.objects.get(id=survey_id).batches.values_list('id', flat=True)
            indicators = indicators.filter(batch__id__in=batches)
    return indicators


@login_required
@permission_required('auth.can_view_batches')
def index(request):
    indicators = Indicator.objects.all()
    indicator_filter_form = IndicatorFilterForm(data=request.GET)
    indicators = _process_form(indicator_filter_form, indicators)

    return render(request, 'indicator/index.html',
                  {'indicators': indicators, 'indicator_filter_form': indicator_filter_form})


@login_required
@permission_required('auth.can_view_batches')
def delete(request, indicator_id):
    indicator = Indicator.objects.get(id=indicator_id)
    indicator.indicator_criteria.all().delete()
    indicator.delete()
    messages.success(request, 'Indicator successfully deleted.')
    return HttpResponseRedirect('/indicators/')


@login_required
@permission_required('auth.can_view_household_groups')
def add_indicator_variable(request, indicator_id):
    indicator = Indicator.get(pk=indicator_id)
    request.breadcrumbs([
        ('Indicators', reverse('list_indicator_page')),
        ('Variable List', reverse('view_indicator_variables', args=(indicator_id, ))),
    ])
    return _add_variable(request, indicator=indicator)


def _add_variable(request, indicator=None):
    form_action = reverse('add_variable')
    parameter_questions = []
    if indicator:
        form_action = reverse("add_indicator_variable", args=(indicator.id, ))
        form_action = reverse("add_indicator_variable", args=(indicator.id, ))
        parameter_questions = indicator.eqset.all_questions
    variable_form = IndicatorVariableForm(indicator)
    if request.method == 'POST':
        variable_form = IndicatorVariableForm(indicator, data=request.POST)
        if variable_form.is_valid():
            variable = variable_form.save()
            if request.is_ajax() is False:
                messages.success(request, 'Variable successfully saved.')
            return HttpResponseRedirect(reverse('edit_indicator_variable', args=(variable.pk, )))
    context = {'variable_form': variable_form,
               'indicator': indicator,
               'title': "Manage Indicator Criteria",
               'button_label': 'Save',
               'id': 'add_group_form',
               "v_form_action": form_action,
               'cancel_url': reverse('list_indicator_page'),
               'parameter_questions': parameter_questions,
               'condition_title': "Conditions"}

    if request.is_ajax():
        context['cancel_url'] = None
        return render(request, 'indicator/indicator_form.html', context)
    return render(request, 'indicator/indicator_variable.html', context)


def add_variable(request):
    return _add_variable(request)


@login_required
@permission_required('auth.can_view_household_groups')
def edit_indicator_variable(request, variable_id):
    variable = IndicatorVariable.get(id=variable_id)
    variable_form = IndicatorVariableForm(variable.indicator, instance=variable)
    parameter_questions = []
    if variable.indicator:
        parameter_questions = variable.indicator.eqset.all_questions
    if request.method == 'POST':
        variable_form = IndicatorVariableForm(variable.indicator, instance=variable, data=request.POST)
        if variable_form.is_valid():
            variable_form.save()
            if request.is_ajax() is False:
                messages.success(request, 'Variable successfully saved.')
            return HttpResponseRedirect(reverse('edit_indicator_variable', args=(variable.pk, )))
    context = {'variable_form': variable_form,
               'indicator': variable.indicator,
               'title': "Manage Indicator Criteria",
               'button_label': 'Save',
               'id': 'add_group_form',
               "v_form_action": reverse("edit_indicator_variable", args=(variable_id, )),
               'cancel_url': reverse('list_indicator_page'),
               'parameter_questions': parameter_questions,
               'conditions': variable.criteria.all(),
               'condition_title': "Conditions"}
    if request.is_ajax():
        context['cancel_url'] = None
        return render(request, 'indicator/indicator_form.html', context)
    breadcrumbs = [
        ('Indicators', reverse('list_indicator_page')),
    ]
    if variable.indicator:
        breadcrumbs.append(
        ('Variable List', reverse('view_indicator_variables', args=(variable.indicator.pk, ))))
    request.breadcrumbs(breadcrumbs)
    return render(request, 'indicator/indicator_variable.html', context)


@login_required
@permission_required('auth.can_view_household_groups')
def delete_indicator_variable(request, variable_id):
    get_object_or_404(IndicatorVariable, id=variable_id).delete()
    if request.is_ajax():
        return add_variable(request)
    messages.info(request, 'Variable removed successfully')
    return HttpResponseRedirect(reverse('list_indicator_page'))


@login_required
@permission_required('auth.can_view_household_groups')
def delete_indicator_criteria(request, indicator_criteria_id):
    criterion = get_object_or_404(IndicatorVariableCriteria, id=indicator_criteria_id)
    variable = criterion.variable
    criterion.delete()
    if request.is_ajax() is False:
        messages.info(request, 'condition removed successfully')
    return HttpResponseRedirect(reverse('edit_indicator_variable', args=(variable.pk, )))


def view_indicator_variables(request, indicator_id):
    indicator = get_object_or_404(Indicator, id=indicator_id)
    request.breadcrumbs([
        ('Indicators', reverse('list_indicator_page')),
    ])
    context = {'indicator': indicator, 'variables': indicator.variables.all()}
    return render(request, 'indicator/indicator_variable_list.html', context)


@login_required
def variables(request):
    # return questions before last question
    if request.GET.get('id', None):
        indicator = Indicator.get(pk=request.GET.get('id', None))
        json_dump = json.dumps(list(indicator.variables.values_list('name', flat=True)))
    else:
        var_ids = request.GET.getlist('var_id[]')
        json_dump = json.dumps(list(IndicatorVariable.objects.filter(id__in=var_ids).values_list('name', flat=True)))
    return HttpResponse(json_dump, content_type='application/json')


@login_required
@permission_required('auth.can_view_batches')
def indicator_formula(request, indicator_id):
    indicator = Indicator.get(id=indicator_id)
    if request.method == 'POST':
        formulae_form = IndicatorFormulaeForm(instance=indicator, data=request.POST)
        if formulae_form.is_valid():
            formulae_form.save()
            messages.info(request, 'Formulae has been saved!')
            return HttpResponseRedirect(reverse('list_indicator_page'))
    else:
        formulae_form = IndicatorFormulaeForm(instance=indicator)
    request.breadcrumbs([
        ('Indicator List', reverse('list_indicator_page')),
    ])
    context = {'indicator_form': formulae_form, 'title': 'Indicator Formulae',
               'button_label': 'Save', 'cancel_url': reverse('list_indicator_page')}
    return render(request, 'indicator/formulae.html', context)


@permission_required('auth.can_view_batches')
def simple_indicator(request, indicator_id):
    hierarchy_limit = 2
    selected_location = Location.objects.get(parent__isnull=True)
    params = request.GET or request.POST
    locations_filter = LocationsFilterForm(data=params)
    first_level_location_analyzed = Location.objects.filter(
        type__name__iexact="country")[0]
    indicator = Indicator.objects.get(id=indicator_id)
    request.breadcrumbs([
        ('Indicator List', reverse('list_indicator_page')),
    ])
    if locations_filter.last_location_selected:
        selected_location = locations_filter.last_location_selected
    report_locations = selected_location.get_children().order_by('name')
    reports_df = indicator.get_data(report_locations)
        # hence set the location where the report is based. i.e the child current selected location.
    context = {'request': request, 'indicator': indicator,
               'locations_filter': locations_filter,
               'selected_location': selected_location,
               }
    context['report'] = mark_safe(reports_df.to_html(
        classes='table table-striped table-bordered table-hover table-sort'))
    if report_locations:
        trace1 = go.Bar(x=reports_df.index,
                        y=reports_df[indicator.REPORT_FIELD_NAME], x0=0, y0=0,
                        name=indicator.name)
        data = go.Data([trace1])
        layout = go.Layout(title=indicator.name, xaxis={'title': report_locations[0].type.name},
                           yaxis={'title': 'Values per %s' % report_locations[0].type.name})
        figure = go.Figure(data=data, layout=layout)
        graph_div = opy.plot(figure, auto_open=False, output_type='div')
        context['graph'] = mark_safe(graph_div)
    return render(request, 'indicator/simple_indicator.html', context)


