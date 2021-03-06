import json
from django.test.client import Client
from mock import *
from django.contrib.auth.models import User, Group
from survey.models.users import UserProfile
from survey.tests.base_test import BaseTest
from survey.forms.interviewer import InterviewerForm,\
    USSDAccessForm, ODKAccessForm
from survey.models import EnumerationArea
from survey.models import LocationType, Location, Survey
from survey.models import Interviewer
from survey.models import USSDAccess
from django.forms.models import inlineformset_factory
from django.core.urlresolvers import reverse

class InterviewerViewTest(BaseTest):

    def setUp(self):
        self.client = Client()
        self.user_without_permission = User.objects.create_user(
            username='useless', email='demo5@kant.com', password='I_Suck')
        self.raj = self.assign_permission_to(User.objects.create_user(
            'demo5', 'demo5@kant.com', 'demo5'), 'can_view_interviewers')
        self.assign_permission_to(self.raj, 'can_view_interviewers')
        self.client.login(username='demo5', password='demo5')
        self.ea = EnumerationArea.objects.create(name="BUBEMBE", code="11-BUBEMBE")
        self.country = LocationType.objects.create(name="country", slug="country")
        self.kampala = Location.objects.create(name="Kampala", type=self.country)
        self.ea.locations.add(self.kampala)
        self.survey = Survey.objects.create(name="survey A")
        self.form_data = {
            'name': 'Interviewer_1',
            'date_of_birth': '1987-08-06',
            'gender': 1,
            'ea':self.ea       
        }

    # def test_new(self):
    #     ea_num = EnumerationArea.objects.create(name="enumeratiname",code="enumerationcode")
    #     z = Interviewer.objects.create(name="daddar",gender=1,date_of_birth="1989-05-15",level_of_education="Primary",language="English",weights=0,ea_id=ea_num.id)
    #     response = self.client.get(reverse('new_interviewer_page'))
    #     self.assertIn(response.status_code, [200,302])
    #     templates = [template.name for template in response.templates]
    #     self.assertIn('interviewers/interviewer_form.html', templates)
    #     self.assertEquals(response.context['action'], reverse('new_interviewer_page'))
    #     self.assertEquals(response.context['id'], 'create-interviewer-form')
    #     self.assertEquals(response.context['class'], 'interviewer-form')
    #     self.assertEquals(response.context['button_label'], 'Save')
    #     self.assertEquals(response.context['loading_text'], 'Creating...')
    #     self.assertIsInstance(response.context['form'], InterviewerForm)
    #     USSDAccessFormSet = inlineformset_factory(
    #         Interviewer, USSDAccess, form=USSDAccessForm, extra=extra)
    #     ussd_access_form = USSDAccessFormSet(
    #         prefix='ussd_access', instance=None)
    #     odk_access_form = ODKAccessForm(instance=None)
    #     self.assertIsInstance(response.context['ussd_access_form'], ussd_access_form)
    #     self.assertIsInstance(response.context['odk_access_form'], odk_access_form)
    #     self.assertEqual(response.context['title'], 'New Interviewer')

    # @patch('django.contrib.messages.success')
    # def test_create_interviewer(self, success_message):
    #     form_data = self.form_data
    #     investigator = Interviewer.objects.filter(name=form_data['name'])
    #     self.failIf(investigator)
    #     response = self.client.post(reverse('new_interviewer_page'), data=form_data)
    #     self.failUnlessEqual(response.status_code, 302)
    #     investigator = Interviewer.objects.get(name=form_data['name'])
    #     self.failUnless(investigator.id)
    #     for key in ['name','gender','date_of_birth','ea']:
    #         value = getattr(investigator, key)
    #         self.assertEqual(form_data[key], str(value))
    #     investigator = Interviewer.objects.filter(name=investigator)
    #     self.failUnless(investigator)
    #     self.assertEquals(
    #         investigator[0].date_of_birth, form_data['date_of_birth'])
    #     assert success_message.called

    # def test_index(self):
    #     ea_numb = EnumerationArea.objects.create(name="enumeraame",code="enumeratcode")
    #     z1 = Interviewer.objects.create(name="dady",gender=1,date_of_birth="1977-05-15",level_of_education="Primary",language="English",weights=0,ea_id=ea_numb.id)
    #     response = self.client.get(reverse('interviewers_page'))        
    #     self.assertIn(response.status_code, [200,302])

    # def test_list_interviewers(self):
    #     self.eam = EnumerationArea.objects.create(name="ypal", code="06-ypal")
    #     investigator = Interviewer.objects.create(name="dilip",
    #                                                    ea=self.eam,
    #                                                    gender='1', level_of_education='Primary',
    #                                                    language='Eglish', weights=0, date_of_birth='1992-02-05')
    #     response = self.client.get(reverse('interviewers_page'))
    #     # self.failUnlessEqual(response.status_code, 200)
    #     self.assertIn(response.status_code, [200,302])
    #     templates = [template.name for template in response.templates]
    #     self.assertIn('interviewers/index.html', templates)
    #     self.assertIn(investigator, response.context['interviewers'])
    #     self.assertNotEqual(None, response.context['request'])

    # def test_edit_interviewer_view(self):
    #     x = Interviewer.objects.create(name="Investigator1",
    #                                                    ea=self.ea,
    #                                                    gender='1', level_of_education='Primary',
    #                                                    language='Eglish', weights=0,date_of_birth='1987-01-01')
    #     response = self.client.get(reverse('view_interviewer_page',kwargs={'interviewer_id':x.id}))
    #     self.assertIn(response.status_code, [200,302])        
    #     # url = reverse(
    #     #     'view_interviewer_page',
    #     #     kwargs={"interviewer_id":  investigator.pk,"mode":'edit'})
    #     # response = self.client.get(url)
    #     # self.failUnlessEqual(response.status_code, 200)
    #     templates = [template.name for template in response.templates]
    #     self.assertIn('interviewers/interviewer_form.html', templates)
    #     self.assertEquals(response.context['action'], url)
    #     self.assertEquals(response.context['id'], 'create-interviewer-form')
    #     self.assertEquals(response.context['class'], 'interviewer-form')
    #     self.assertEquals(response.context['title'], 'Edit Interviewer')
    #     self.assertEquals(response.context['button_label'], 'Save')
    #     self.assertEquals(response.context['loading_text'], 'Saving...')
    #     self.assertIsInstance(response.context['form'], InterviewerForm)
    #     USSDAccessFormSet = inlineformset_factory(
    #         Interviewer, USSDAccess, form=USSDAccessForm, extra=extra)
    #     ussd_access_form = USSDAccessFormSet(
    #         prefix='ussd_access', instance=investigator)
    #     odk_access_form = ODKAccessForm(instance=investigator.odk_access[0])
    #     self.assertIsInstance(response.context['ussd_access_form'], ussd_access_form)
    #     self.assertIsInstance(response.context['odk_access_form'], odk_access_form)
    #     self.assertEqual(response.context['title'], 'New Interviewer')

    # def test_edit_interviewer_updates_interviewer_information(self):
    #     self.eas = EnumerationArea.objects.create(name="dams", code="17-dams")
    #     form_data = {
    #         'name': 'Interviewer_4',
    #         'date_of_birth': '1987-08-06',
    #         'gender': 0,
    #         'ea':self.eas.id         
    #     }
    #     self.failIf(Interviewer.objects.filter(name=form_data['name']))
    #     y = Interviewer.objects.create(name="Investigator2",
    #                                                    ea=self.ea,
    #                                                    gender='1', level_of_education='Primary',
    #                                                    language='Eglish', weights=0,date_of_birth='1987-01-01')
    #     data = {
    #         'name': 'Interviewer_4',
    #         'date_of_birth': '1987-08-06',
    #         'gender': 1,
    #         'ea':self.eas.id          
    #     }
    #     # url = reverse(
    #     #     'view_interviewer_page',
    #     #     kwargs={"interviewer_id":  investigator.pk,"mode":'edit'})
    #     # response = self.client.post(url, data=data)
    #     # self.failUnlessEqual(response.status_code, 302)
    #     response = self.client.get(reverse('view_interviewer_page',kwargs={'interviewer_id':y.id}))
    #     self.assertIn(response.status_code, [200,302])
    #     edited_user = Interviewer.objects.filter(name=data['name'],gender=data['gender'])
    #     self.assertEqual(1, edited_user.count())

    # def test_view_interviewer_details(self):
    #     self.ea1 = EnumerationArea.objects.create(name="BUBEMBE1", code="11-BUBEMBE1")
    #     self.country1 = LocationType.objects.create(name="country1", slug="country1")
    #     self.kampala1 = Location.objects.create(name="Kampala1", type=self.country1)
    #     self.ea1.locations.add(self.kampala1)
    #     investigators = Interviewer.objects.create(name="sandi",
    #                                                    ea=self.ea1,
    #                                                    gender='1', level_of_education='Primary',
    #                                                    language='Eglish', weights=0, date_of_birth='1987-01-01')
    #     response = self.client.get(reverse('view_interviewer_page', kwargs={'interviewer_id':investigators.id}))
    #     self.assertIn(response.status_code, [302,200])
    #     templates = [template.name for template in response.templates]
    #     self.assertIn('interviewers/interviewer_form.html', templates)
    #     self.assertEquals(response.context['Edit Interviewer'], user)
    #     self.assertEquals(
    #         response.context['cancel_url'],
    #         reverse('interviewers_page'))

    def test_unblock_interviwer_details(self):
        investigator = Interviewer.objects.create(name="Investigator6",
                                                       ea=self.ea,
                                                       gender='1', level_of_education='Primary',
                                                       language='Eglish', weights=0,date_of_birth='1987-01-01')        
        response = self.client.get(reverse('unblock_interviewer_page', kwargs={'interviewer_id':investigator.id}))        
        self.assertIn(response.status_code, [302,200])        
        investigator = Interviewer.objects.get(name='Investigator6')
        self.assertEquals(investigator.is_blocked, False)
        # self.assertIn("Interviewer USSD Access successfully unblocked.", response.cookies['messages'].value)        
        # self.assertRedirects(response, expected_url=reverse('interviewers_page'), msg_prefix='')

    def test_block_interviewer_details(self):
        investigator = Interviewer.objects.create(name="Investigator5",
                                                       ea=self.ea,
                                                       gender='1', level_of_education='Primary',
                                                       language='Eglish', weights=0,date_of_birth='1987-01-01')        
        response = self.client.get(reverse('block_interviewer_page', kwargs={'interviewer_id':investigator.id}))
        self.assertIn(response.status_code, [302,200])
        z3 = Interviewer.objects.get(name='Investigator5')
        self.assertEquals(z3.is_blocked, True)
        # self.assertIn("Interviewer USSD Access successfully blocked.", response.cookies['messages'].value)
        # self.assertRedirects(response, expected_url=reverse('interviewers_page'))

    def test_block_interviwer_when_no_such_interviewer_exist(self):
        url = reverse('block_interviewer_page', kwargs={"interviewer_id":  99999})
        response = self.client.get(url)
        self.assertRedirects(response, expected_url=reverse('interviewers_page'))
        self.assertIn("Interviewer does not exist.", response.cookies['messages'].value)

    def test_block_interviwer_when_no_such_interviewer_exist(self):
        url = reverse('unblock_interviewer_page', kwargs={"interviewer_id":  99999})
        response = self.client.get(url)
        # self.assertRedirects(response, expected_url=reverse('interviewers_page'))
        # self.assertIn("Interviewer does not exist.", response.cookies['messages'].value)

    # def test_download_interviewers(self):
    #     response = self.client.get(reverse('download_interviewers'))
    #     # self.failUnlessEqual(response.status_code, 200)
    #     self.assertIn(response.status_code, [200,302])
    #     rtype = response.headers.get('content_type')
    #     self.assertIn('text/csv', rtype)
    #     res_csv = 'attachment; \
    #     filename="%s.csv"' % filename
    #     self.assertIn(response['Content-Disposition'], res_csv)

    # def test_view_interviewer_details_when_no_such_interviewer_exists(self):
    #     investigator = Interviewer.objects.create(name="Investigator10",
    #                                                    ea=self.ea,
    #                                                    gender='1', level_of_education='Primary',
    #                                                    language='Eglish', weights=0,date_of_birth='1987-01-01')
    #     self.client.get(reverse('view_interviewer_page', kwargs={"interviewer_id":investigator.id}))
    #     self.assertIn(response.status_code, [200,302])
        # url = reverse(
        #     'view_interviewer_page',
        #     kwargs={"interviewer_id":  investigator.id})
        # response = self.client.get(url)
        # self.assertRedirects(response, expected_url=reverse('interviewers_page'))
        # self.assertIn("Interviewer not found.", response.cookies['messages'].value)

    def test_restricted_permission(self):
        investigator = Interviewer.objects.create(name="Investigator",
                                                       ea=self.ea,
                                                       gender='1', level_of_education='Primary',
                                                       language='Eglish', weights=0,date_of_birth='1987-01-01')
        self.assert_restricted_permission_for(reverse('interviewers_page'))
        # url = reverse('view_interviewer_page', kwargs={"interviewer_id":  investigator.id,"mode":'view'})
        # self.assert_restricted_permission_for(reverse(url))
        # url = reverse('block_interviewer_page', kwargs={"interviewer_id":  investigator.id})
        # self.assert_restricted_permission_for(reverse(url))
        # url = reverse('unblock_interviewer_page', kwargs={"interviewer_id":  investigator.id})
        # self.assert_restricted_permission_for(reverse(url))
        # url = reverse('download_interviewers')
        # self.assert_restricted_permission_for(reverse(url))