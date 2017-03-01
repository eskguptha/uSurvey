import random
from django import forms
from cacheops import cached_as
from django import template
from django.forms import ModelForm
from survey.models import Indicator, QuestionSet, QuestionModule, Survey, QuestionOption, IndicatorVariableCriteria, \
    IndicatorVariable
from survey.models import BatchQuestion, Question, Answer, MultiChoiceAnswer, MultiSelectAnswer, NumericalAnswer
from django.core.exceptions import ValidationError
from survey.forms.form_helper import FormOrderMixin
from survey.forms.form_helper import IconName


class IndicatorVariablesField(forms.ModelMultipleChoiceField, IconName):
    pass


class IndicatorForm(ModelForm, FormOrderMixin):
    survey = forms.ModelChoiceField(queryset=Survey.objects.all(), empty_label='Select Survey')
    question_set = forms.ModelChoiceField(queryset=QuestionSet.objects.none(), empty_label='Select Question set')
    variables = IndicatorVariablesField(queryset=IndicatorVariable.objects.none())

    def __init__(self, *args, **kwargs):
        super(IndicatorForm, self).__init__(*args, **kwargs)
        if kwargs.get('instance'):
            qset = kwargs['instance'].question_set
            survey = kwargs['instance'].survey
            self.fields['survey'].initial = survey
            self.fields['survey'].widget.attrs['readonly'] = 'readonly'
            self.fields['question_set'].queryset = survey.batches.all()
            self.fields['question_set'].initial = survey.qsets
            self.fields['question_set'].widget.attrs['readonly'] = 'readonly'
            self.fields['variables'].initial = kwargs['instance'].variables.all()
            # self.fields['variables'].queryset = kwargs['instance'].variables.all()
        #self.fields['variables'].widget.attrs.update({'class': 'multi-select variables'})
        var_ids = list(self.fields['variables'].queryset.values_list('id', flat=True)) + list(
            IndicatorVariable.objects.filter(indicator__isnull=True).values_list('id', flat=True)
        )
        self.fields['variables'].queryset = self.available_variables()
        self.fields['variables'].icon_name = 'add'
        self.fields['variables'].icon_attrs.update({'data-toggle': "modal", 'data-target': "#add_variable"})
        if self.data.get('survey'):
            self.fields['question_set'].queryset = Survey.get(pk=self.data['survey']).qsets
        self.fields['name'].label = 'Indicator'
        self.order_fields(['survey', 'question_set', 'name', 'description', 'variables', 'formulae'])

    def available_variables(self):
        var_ids = list(IndicatorVariable.objects.filter(indicator__isnull=True).values_list('id', flat=True))
        if self.instance:
            var_ids.extend(self.instance.variables.values_list('id', flat=True))
        return IndicatorVariable.objects.filter(id__in=var_ids)


    def clean(self):
        super(IndicatorForm, self).clean()
        question_set = self.cleaned_data.get('question_set', None)
        survey = self.cleaned_data.get('survey', None)
        if question_set and survey.qsets.filter(id=question_set.id).exists() is False:
            message = "Question set %s does not belong to the selected Survey." % (
                question_set.name)
            self._errors['batch'] = self.error_class([message])
            del self.cleaned_data['question_set']
        return self.cleaned_data

    def clean_formulae(self):
        if self.instance.pk:
            from asteval import Interpreter
            aeval = Interpreter()
            selected_vars = IndicatorVariable.objects.filter(id__in=self.data.getlist('variables'))
            # basically substitute all place holders with random values just to see if it gives a valid math answer
            context = dict([(v.name, random.randint(1, 10000)) for v in selected_vars])
            question_context = template.Context(context)
            math_string = template.Template(self.cleaned_data['formulae']).render(question_context)
            aeval(math_string)
            if len(aeval.error) > 0:
               raise ValidationError(aeval.error[-1].get_error()[1])
        return self.cleaned_data['formulae']

    class Meta:
        model = Indicator
        exclude = []

    def save(self, commit=True, *args, **kwargs):
        instance = super(IndicatorForm, self).save(commit=commit, *args, **kwargs)
        if commit:
            self.cleaned_data['variables'].update(indicator=instance)
            instance.variables.exclude(id__in=self.data.getlist('variables')).delete()
            IndicatorVariable.objects.filter(indicator__isnull=True).delete()
        return instance


class IndicatorVariableForm(ModelForm, FormOrderMixin):
    min = forms.IntegerField(required=False)
    max = forms.IntegerField(required=False)
    value = forms.CharField(required=False)
    options = forms.ChoiceField(choices=[], required=False)
    CHOICES = [('', '--------------------')]
    CHOICES.extend(IndicatorVariableCriteria.VALIDATION_TESTS)
    validation_test = forms.ChoiceField(choices=CHOICES, required=False,
                                        label='Operator')
    test_question = forms.ModelChoiceField(queryset=Question.objects.none(), required=False)
    var_qset = forms.CharField(widget=forms.HiddenInput, required=False)

    def __init__(self, indicator, *args, **kwargs):
        super(IndicatorVariableForm, self).__init__(*args, **kwargs)
        self.indicator = indicator
        self.order_fields(['name', 'description', 'test_question', 'validation_test', 'options', 'value',
                           'min', 'max', 'var_qset'])
        if self.indicator:
            self.fields['test_question'].queryset = Question.objects.filter(pk__in=[q.pk for q in
                                                                                    indicator.question_set.all_questions
                                                                                    ])

        if self.data.get('test_question', []):
            options = QuestionOption.objects.filter(question__pk=self.data['test_question'])
            self.fields['options'].choices = [(opt.order, opt.text) for opt in options]

        if self.data.get('var_qset', []):
            self.fields['test_question'].queryset = Question.objects.filter(id__in=[q.id for q in
                                                                                    QuestionSet.get(id=
                                                                                                    self.data['var_qset']
                                                                                                    ).all_questions])

    class Meta:
        model = IndicatorVariable
        exclude = ['indicator', ]
        widgets = {'description': forms.Textarea(attrs={"rows": 2, "cols": 100}), }

    def clean_name(self):
        self.cleaned_data['name'] = self.cleaned_data['name'].replace(' ', '_')
        return self.cleaned_data['name']

    def clean(self):
        validation_test = self.cleaned_data.get('validation_test', None)
        test_question = self.cleaned_data.get('test_question', None)
        if validation_test is None or test_question is None:
            return self.cleaned_data
        answer_class = Answer.get_class(test_question.answer_type)
        method = getattr(answer_class, validation_test, None)
        if method is None:
            raise forms.ValidationError('unsupported validator defined on test question')
        if validation_test == 'between':
            if self.cleaned_data.get('min', False) is False or self.cleaned_data.get('max', False) is False:
                raise forms.ValidationError('min and max values required for between condition')
        elif self.cleaned_data.get('value', False) is False:
            raise forms.ValidationError('Value is required for %s' % validation_test)
        if test_question.answer_type in [MultiChoiceAnswer.choice_name(), MultiSelectAnswer]:
            if self.cleaned_data.get('options', False) is False:
                raise forms.ValidationError('No option selected for %s' % test_question.identifier)
            self.cleaned_data['value'] = self.cleaned_data['options']
        return self.cleaned_data

    def save(self, *args, **kwargs):
        variable = super(IndicatorVariableForm, self).save(commit=False)
        variable.indicator = self.indicator
        variable.save()
        validation_test = self.cleaned_data.get('validation_test', None)
        test_question = self.cleaned_data.get('test_question', None)
        if validation_test and test_question:
            criteria = IndicatorVariableCriteria.objects.create(test_question=test_question, variable=variable,
                                                                validation_test=validation_test)
            if validation_test == 'between':
                criteria.arguments.create(position=0, param=self.cleaned_data['min'])
                criteria.arguments.create(position=1, param=self.cleaned_data['max'])
            else:
                criteria.arguments.create(position=0, param=self.cleaned_data['value'])
        return variable


# to do: tidy this up later
class IndicatorCriteriaForm(ModelForm, FormOrderMixin):
    min = forms.IntegerField(required=False)
    max = forms.IntegerField(required=False)
    value = forms.CharField(required=False)
    options = forms.ChoiceField(choices=[], required=False)
    CHOICES = [('', '--------------------')]
    CHOICES.extend(IndicatorVariableCriteria.VALIDATION_TESTS)
    validation_test = forms.ChoiceField(choices=CHOICES,
                                        label='Operator')
    test_question = forms.ModelChoiceField(queryset=Question.objects.none())

    def __init__(self, variable, *args, **kwargs):
        super(IndicatorCriteriaForm, self).__init__(*args, **kwargs)
        self.variable = variable
        self.order_fields(['description', 'test_question', 'validation_test', 'options', 'value',
                           'min', 'max'])
        if variable.indicator:
            self.fields['test_question'].queryset = Question.objects.filter(pk__in=[q.pk
                                                                                    for q in
                                                                                    variable.indicator.batch.all_questions
                                                                                    ])
        if self.data.get('test_question', []):
            options = QuestionOption.objects.filter(question__pk=self.data['test_question'])
            self.fields['options'].choices = [(opt.order, opt.text) for opt in options]

    class Meta:
        model = IndicatorVariableCriteria
        exclude = ['variable', ]
        widgets = {'description': forms.Textarea(attrs={"rows": 2, "cols": 100}), }

    def clean(self):
        validation_test = self.cleaned_data.get('validation_test', None)
        test_question = self.cleaned_data.get('test_question', None)
        if validation_test is None or test_question is None:
            return self.cleaned_data
        answer_class = Answer.get_class(test_question.answer_type)
        method = getattr(answer_class, validation_test, None)
        if method is None:
            raise forms.ValidationError('unsupported validator defined on test question')
        if validation_test == 'between':
            if self.cleaned_data.get('min', False) is False or self.cleaned_data.get('max', False) is False:
                raise forms.ValidationError('min and max values required for between condition')
        elif self.cleaned_data.get('value', False) is False:
            raise forms.ValidationError('Value is required for %s' % validation_test)
        if test_question.answer_type in [MultiChoiceAnswer.choice_name(), MultiSelectAnswer]:
            if self.cleaned_data.get('options', False) is False:
                raise forms.ValidationError('No option selected for %s' % test_question.identifier)
            self.cleaned_data['value'] = self.cleaned_data['options']
        return self.cleaned_data

    def save(self, *args, **kwargs):
        criteria = super(IndicatorCriteriaForm, self).save(commit=False)
        criteria.variable = self.variable
        criteria.save()
        validation_test = self.cleaned_data.get('validation_test', None)
        if validation_test == 'between':
            criteria.arguments.create(position=0, param=self.cleaned_data['min'])
            criteria.arguments.create(position=1, param=self.cleaned_data['max'])
        else:
            criteria.arguments.create(position=0, param=self.cleaned_data['value'])
        return criteria


class IndicatorFormulaeForm(forms.ModelForm):

    class Meta:
        model = Indicator
        fields = ['formulae', ]

    def clean_formulae(self):
        if self.instance.pk:
            from asteval import Interpreter
            aeval = Interpreter()
            # basically substitute all place holders with 1 and see if it gives a valid math function
            context = dict([(v.name, 1) for v in self.instance.variables.all()])
            question_context = template.Context(context)
            math_string =  template.Template(self.cleaned_data['formulae']).render(question_context)
            aeval(math_string)
            if len(aeval.error) > 0:
               raise ValidationError(aeval.error[-1].get_error()[1])
        return self.cleaned_data['formulae']