import json
from django.test.client import Client
from mock import *
from django.contrib.auth.models import User, Group
from survey.models import RespondentGroup, ParameterTemplate, RespondentGroupCondition, Interviewer
from survey.models import *
from survey.forms import *
from django.core.urlresolvers import reverse
from survey.tests.base_test import BaseTest
from survey.forms.respondent_group import GroupForm
from django.core.urlresolvers import reverse

class RespondentViewTest(BaseTest):

    def setUp(self):
        self.client = Client()
        User.objects.create_user(
            username='useless', email='demo8@kant.com', password='I_Suck')
        raj = self.assign_permission_to(User.objects.create_user('demo8', 'demo8@kant.com', 'demo8'),
                                        'can_view_household_groups')
        self.assign_permission_to(raj, 'can_view_household_groups')
        x = self.client.login(username='demo8', password='demo8')
        self.form_data = {"name":'G-1',"description":"blah blah"}

        country = LocationType.objects.create(name="Country", slug="country")
        uganda = Location.objects.create(name="Uganda", type=country, code="1")
        district = LocationType.objects.create(
            name='District', parent=country, slug='district')
        kampala = Location.objects.create(
            name="Kampala", type=district, parent=uganda, code="2")
        ea = EnumerationArea.objects.create(name="Kampala EA")
        ea.locations.add(kampala)

    def test_new(self):
        response = self.client.get(reverse('new_respondent_groups_page'))
        self.assertIn(response.status_code, [302,200])
        templates = [template.name for template in response.templates]
        self.assertIn('respondent_groups/new.html', templates)
        self.assertIsInstance(response.context['groups_form'], GroupForm)
        self.assertIn('add_group_form', response.context['id'])
        self.assertIn('Create', response.context['button_label'])
        self.assertIn('New Group', response.context['title'])
        self.assertIn(response.context['action'], [reverse('new_respondent_groups_page'),'.'])

    def test_index(self):
        g = RespondentGroup.objects.create(name='g111',description='des')
        response = self.client.get(reverse('respondent_groups_page'))
        self.assertEquals(response.status_code, 200)
        self.assertIn(g, response.context['groups'])

    def test_list_groups(self):
        g = RespondentGroup.objects.create(name='g1',description='des')
        response = self.client.get(reverse('respondent_groups_page'))
        self.assertEquals(response.status_code, 200)
        templates = [template.name for template in response.templates]
        self.assertIn('respondent_groups/index.html', templates)
        self.assertIn(g, response.context['groups'])
        self.assertNotEqual(None, response.context['request'])

    def test_edit_group_view(self):
        g = RespondentGroup.objects.create(name='g1',description='des')
        url = reverse(
            'respondent_groups_edit',
            kwargs={"group_id": g.pk})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        templates = [template.name for template in response.templates]
        self.assertIn('respondent_groups/new.html', templates)
        self.assertEquals(response.context['action'], url)
        self.assertEquals(response.context['id'], 'add_group_form')
        self.assertEquals(response.context['title'], 'Edit Group')
        self.assertEquals(response.context['button_label'], 'Save')
        self.assertEquals(response.context['condition_title'], 'New Eligibility Criteria')
        # self.assertIsInstance(response.context['group_form'], GroupForm)

    # def test_group_does_not_exist(self):
    #     g1 = RespondentGroup.objects.create(name='g1s',description='dess')
    #     # message = "Group does not exist."
    #     response = self.client.get(reverse('respondent_groups_edit',kwargs={"group_id":456789}))
    #     # url = reverse('respondent_groups_edit',kwargs={"group_id":g1.id})

    #     # response = self.client.get(url)
    #     self.assertIn(response.status_code, [200,302])
    #     self.assertIn('Group does not exist.', response.cookies['messages'].__str__())
    #     self.assertRedirects(response, expected_url=reverse['respondent_groups_page'], msg_prefix='')

    #     # self.assertEquals(message,response.cookies['message'].value)

    def test_should_throw_error_if_deleting_non_existing_group(self):
        message = "Group does not exist."
        url = reverse('respondent_groups_delete',kwargs={"group_id":50011})
        response = self.client.get(url)
        self.assertEquals(message,response.cookies['message'].value)

    # @patch('django.contrib.messages.success')
    # def test_create_group_onpost(self, success_message):
    #     form_data = self.form_data
    #     g = RespondentGroup.objects.filter(name=form_data['name'])
    #     self.failIf(g)
    #     response = self.client.post(reverse('new_respondent_groups_page'), data=form_data)
    #     self.assertEquals(response.status_code, 302)
    #     # self.rsp = RespondentGroup.objects.create(name="G-1")
    #     # g = RespondentGroup.objects.get(name=self.rsp)
    #     # self.failUnless(g.id)
    #     for key in ['name','description']:
    #         value = getattr(g, key)
    #         self.assertEqual(form_data[key], str(value))
    #     glist = Interviewer.objects.filter(name=g)
    #     self.failUnless(glist)
    #     self.assertEquals(
    #         glist[0].description, form_data['description'])
    #     assert success_message.called

    @patch('django.contrib.messages.warning')
    def test_failure_group_onpost(self, success_message):
        form_data = self.form_data
        form_data['name']  = ''
        response = self.client.post(reverse('new_respondent_groups_page'), data=form_data)
        self.assertEqual(response.status_code, 200)

    def test_restricted_permission(self):
        self.assert_restricted_permission_for(reverse('new_respondent_groups_page'))
        self.assert_restricted_permission_for(reverse('respondent_groups_page'))
        url = reverse('respondent_groups_edit',kwargs={"group_id":500})
        self.assert_restricted_permission_for(url)

    # def test_delete_should_delete_the_group(self):
    #     pt = ParameterTemplate.objects.create(templatequestion_ptr_id=1)
    #     glo= RespondentGroup.objects.create(name='gdaf',description='deasfds')
    #     response = self.client.get(reverse('respondent_groups_delete'),kwargs={"group_id":pt.id})
    #     # self.assertIn('Group successfully deleted.', response.cookies['messages'].__str__())
    #     # self.assertRedirects(response, expected_url= reverse('respondent_groups_page', kwargs={"group_id" : g.id}), msg_prefix='')
    #     self.assertIn(response.status_code, [200,302])

        # url = reverse('respondent_groups_delete',kwargs={"group_id":g.id})
        # response = self.client.get(url)        
        # self.assertRedirects(response, expected_url=reverse('respondent_groups_delete'), status_code=302,
        #                      target_status_code=200, msg_prefix='')

    def test_should_throw_error_if_deleting_non_existing_group(self):
        message = "Group does not exist."
        url = reverse('respondent_groups_delete',kwargs={"group_id":500})
        self.assert_object_does_not_exist(url, message)

    # def test_delete_should_delete_the_groupcondition(self):
    #     rg = RespondentGroup.objects.create(name='rg1_c', description='blah')
    #     p = ParameterTemplate.objects.create(id=1)
    #     self.failUnless(p.id)
    #     p = ParameterTemplate.objects.all()[0]
    #     rgc = RespondentGroupCondition.objects.create(respondent_group_id=rg,test_question=p.id,validation_test='abcd')
    #     g = RespondentGroup.objects.get(name='rg1_c')
    #     self.failUnless(rgc.id)
    #     self.failUnless(g.id)
    #     url = reverse('delete_condition_page',kwargs={"condition_id":rgc.id})
    #     response = self.client.get(url)
    #     self.assertRedirects(
    #         response, reverse('respondent_groups_page'), status_code=302, target_status_code=200, msg_prefix='')
    
    # def test_should_throw_error_if_deleting_non_existing_groupcondition(self):
    #     message = "Group does not exist."
    #     url = reverse('delete_condition_page',kwargs={"condition_id":99999})
    #     self.assert_object_does_not_exist(url, message)