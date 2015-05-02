from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from survey.models import BatchQuestionOrder
from survey.models.batch import Batch
from django.utils.safestring import mark_safe

from survey.models.formula import *


class TableRowForm(forms.Form):
    '''
    This form is special, because usually, forms include a range of inputs
    to be filled out by the user. This form however, no inputs are filled in. The
    form is given a queryset of objects and a list of field names, and with those,
    a table is made. Each row in the table represents an object. clicking a row
    will select the object. Multiple submit buttons can be given with various
    functions. What these buttons have in common is that they all operate on the
    selected objects, e.g. selecting three objects and pressing delete will delete
    those three objects. The form is different in that it does not create new objects,
    it manipulates already existing objects.
    '''
    def __init__(self, queryset, fields):
        if not fields:
            raise Exception('A TableRowForm must be supplied both queryset and fields')
        self.queryset = queryset
        self.fields = fields

    def __unicode__(self):
        '''
        Builds the html table rows for the form.
        '''
        if not self.queryset: return '<tr><td>No data...<td></tr>'
        colcount = 0
        res = ""
        res += "<tr>"
        for f in self.fields:
            res += "<th>"+self.queryset[0]._meta.get_field_by_name(f)[0].verbose_name.upper()+"</th>"
        res += "</tr>\n"
        for obj in self.queryset:
            res += '<tr onclick="selectRow(this)">'
            res += '<td><input style="display:none;" type="checkbox" name="slct" id="%s" value="%s"/>'%(obj.pk,obj.pk)

            vals = [getattr(obj, x) for x in self.fields]
            colcount = len(vals)
            for x in vals:
                res += '%s</td><td>'%(x.encode('ascii', 'ignore'))
            res = res[:-4]
            res += '</tr>\n'
        res += '<tr><th colspan="%d"><span style="font-size:9pt;"><b>Selctable table:</b> Click a row to select it</span></th></tr>'%(colcount)

        # Add the javascript that implements functionality
        res += '''\
        <script>
        // Allows for selectable tablerows in forms
        function selectRow(row)
        {
            // Check/uncheck the checkbox
            var chk = row.getElementsByTagName('input')[0];
            chk.checked = !chk.checked;

            // Color the row in response to the checkbox's boolean value
            if (chk.checked) {
                row.style.backgroundColor = 'gray';
            } else {
                row.style.backgroundColor = 'white';
            }
        }
        </script>'''
        return res



class TableMultiSelect(forms.SelectMultiple):

    class Media:
        css = ('css/tablemultiselect.css',)
        js = ('js/tablemultiselect.js', )    

    def render(self, name, value, attrs=None, choices=()):
        if attrs is None: attrs = {}
        questions = Question.objects.filter(subquestion=False).exclude(group__name='REGISTRATION GROUP')
        question_items = []
        map(lambda q: question_items.append((int(q.pk), q.identifier, q.text, q.answer_type.upper())), questions) 
        html = []
        #html.append(super(TableMultiSelect, self).render(name, value, attrs, choices))
	
        html.append( """
        
	<div class="form-horizontal" role="form" style="width: 600px;margin: auto;margin-top:150px;">
        <div id="question_table">
        <div class="form-group" style="border: 1px solid #ddd">
        <table id="table1" class="display">
            <thead>
            
                <th>#</th>
                <th>Code</th>
                <th>Text</th>
                <th>Answer Type</th>
           </thead>
           <tbody>
        """
        )
        for items in question_items:
            html.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % items)
        html.append("""
                </tbody></table></div>
            
<script src="/static/jquery.dataTables.min.js" type="text/javascript"></script>
<script src="/static/jquery-1.11.1.min.js"></script>
	
</div>
            
<link href="/static/jquerysctipttop.css" rel="stylesheet" type="text/css">
<link href="/static/jquery.dataTables.css" rel="stylesheet" type="text/css">
    <link href="/static/bootstrap.min.css" type="text/css" rel="stylesheet">

<script type="text/javascript">
$(document).ready(function() {
    var table = $('#table1').DataTable();
 
    $('#table1 tbody').on( 'click', 'tr', function () {
        $(this).toggleClass('selected');
    } );
 
    $('#button').click( function () {
        alert( table.rows('.selected').data().length +' row(s) selected' );
    } );
} );
</script>

        """
        )
        return mark_safe("\r\n".join(html))


class BatchForm(ModelForm):

    class Meta:
        model = Batch
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={"rows": 4, "cols": 50})
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        existing_batches = Batch.objects.filter(name=name, survey=self.instance.survey)
        if existing_batches.count() > 0 and self.initial.get('name', None) != str(name):
            raise ValidationError('Batch with the same name already exists.')
        return self.cleaned_data['name']


class BatchQuestionsForm(ModelForm):
    questions = forms.ModelMultipleChoiceField(label=u'', queryset=Question.objects.filter(subquestion=False).exclude(group__name='REGISTRATION GROUP'),
                                               widget=forms.SelectMultiple(attrs={'class': 'multi-select'}))

    class Meta:
        model = Batch
        fields = ['questions']

    def __init__(self, batch=None, *args, **kwargs):
        super(BatchQuestionsForm, self).__init__(*args, **kwargs)
        self.fields['questions'].queryset = Question.objects.filter(subquestion=False).exclude(group__name='REGISTRATION GROUP').exclude(batches=batch)

    def save_question_to_batch(self, batch):
        for question in self.cleaned_data['questions']:
            question.save()
            order = BatchQuestionOrder.next_question_order_for(batch)
            BatchQuestionOrder.objects.create(question=question, batch=batch, order=order)
            question.batches.add(batch)

    def save(self, commit=True, *args, **kwargs):
        batch = super(BatchQuestionsForm, self).save(commit=commit, *args, **kwargs)

        if commit:
            batch.save()
            self.save_question_to_batch(batch)

class TableBatchQuestionsForm(TableRowForm):
#    questions = TableRowForm(queryset=Question.objects.filter(subquestion=False).exclude(group__name='REGISTRATION GROUP'), fields=('identifier', 'text', 'answer_type')

#forms.ModelMultipleChoiceField(label=u'', queryset=Question.objects.filter(subquestion=False).exclude(group__name='REGISTRATION GROUP'),
#                                               widget=forms.SelectMultiple(attrs={'class': 'multi-select'}))

    def __init__(self, batch=None, *args, **kwargs):
        super(TableBatchQuestionsForm, self).__init__(queryset=Question.objects.filter(subquestion=False).exclude(group__name='REGISTRATION GROUP', batches=batch), fields=('identifier', 'text', 'answer_type'))
        self.questions = Question.objects.filter(subquestion=False).exclude(group__name='REGISTRATION GROUP').exclude(batches=batch)
        if kwargs.get('data', None):
            self.questions = self.questions.filter(pk__in=kwargs.get('data').getlist('slct'))
        self.batch = batch

    def is_valid(self):
        return True

    def save_question_to_batch(self, batch):
        for question in self.questions:
            order = BatchQuestionOrder.next_question_order_for(batch)
            BatchQuestionOrder.objects.create(question=question, batch=batch, order=order)
            question.batches.add(batch)

    def save(self, *args, **kwargs):
        batch = self.batch
        self.save_question_to_batch(batch)
