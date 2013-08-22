from django.test import TestCase
from survey.forms.batch import *

class BatchFormTest(TestCase):
    def test_valid(self):
        form_data = {
                        'name': 'Batch 1',
                        'description': 'description goes here',
                    }
        batch_form = BatchForm(form_data)
        self.assertTrue(batch_form.is_valid())

    def test_invalid(self):
        form_data = {
                        'description': 'description goes here',
                    }
        batch_form = BatchForm(form_data)
        self.assertFalse(batch_form.is_valid())
