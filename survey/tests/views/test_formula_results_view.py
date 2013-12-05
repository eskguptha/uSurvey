from datetime import date
from random import randint
from django.test.client import Client
from rapidsms.contrib.locations.models import Location, LocationType
from django.contrib.auth.models import User
from survey.models import HouseholdMemberGroup, GroupCondition, QuestionModule, Indicator, LocationTypeDetails
from survey.models.batch import Batch
from survey.models.households import HouseholdHead, Household, HouseholdMember
from survey.models.backend import Backend
from survey.models.investigator import Investigator

from survey.models.formula import *
from survey.models.question import Question, QuestionOption
from survey.views.location_widget import LocationWidget
from survey.tests.base_test import BaseTest


class NumericalFormulaResults(BaseTest):
    def setUp(self):
        self.client = Client()
        self.member_group = HouseholdMemberGroup.objects.create(name="Greater than 2 years", order=1)
        self.condition = GroupCondition.objects.create(attribute="AGE", value=2, condition="GREATER_THAN")
        self.condition.groups.add(self.member_group)

        User.objects.create_user(username='useless', email='rajni@kant.com', password='I_Suck')
        self.assign_permission_to(User.objects.create_user('Rajni', 'rajni@kant.com', 'I_Rock'), 'can_view_aggregates')
        self.client.login(username='Rajni', password='I_Rock')

        module = QuestionModule.objects.create(name='Education', description='Educational Module')
        indicator = Indicator.objects.create(name='Test Indicator', measure=Indicator.MEASURE_CHOICES[0][1],
                                             module=module, description="Indicator 1")

        self.batch = Batch.objects.create(order=1)
        self.question_1 = Question.objects.create(text="Question 1?", answer_type=Question.NUMBER, order=1, group=self.member_group)
        self.question_2 = Question.objects.create(text="Question 2?", answer_type=Question.NUMBER, order=2, group=self.member_group)
        self.question_1.batches.add(self.batch)
        self.question_2.batches.add(self.batch)
        self.formula_1 = Formula.objects.create(numerator=self.question_1, denominator=self.question_2, indicator=indicator)
        country = LocationType.objects.create(name='Country', slug='country')
        self.uganda = Location.objects.create(name='Country', type=country)
        LocationTypeDetails.objects.create(country=self.uganda, location_type=country)
        district = LocationType.objects.create(name = 'District', slug='district')
        village = LocationType.objects.create(name = 'Village', slug='village')

        self.kampala = Location.objects.create(name='Kampala', type=district, tree_parent=self.uganda)
        self.village_1 = Location.objects.create(name='Village 1', type=village, tree_parent=self.kampala)
        self.village_2 = Location.objects.create(name='Village 2', type=village, tree_parent=self.kampala)

        backend = Backend.objects.create(name='something')
        investigator = Investigator.objects.create(name="Investigator 1", mobile_number="1", location=self.village_1, backend = backend, weights = 0.3)
        self.household_1 = Household.objects.create(investigator=investigator, uid=0)
        self.household_2 = Household.objects.create(investigator=investigator, uid=1)

        investigator_1 = Investigator.objects.create(name="Investigator 2", mobile_number="2", location=self.village_2, backend = backend, weights = 0.9)
        self.household_3 = Household.objects.create(investigator=investigator_1, uid=2)
        self.household_4 = Household.objects.create(investigator=investigator_1, uid=3)

        self.member1 = self.create_household_member(self.household_1)
        self.member2 = self.create_household_member(self.household_2)
        self.member3 = self.create_household_member(self.household_3)
        self.member4 = self.create_household_member(self.household_4)

        investigator.member_answered(self.question_1, self.member1, 20, self.batch)
        investigator.member_answered(self.question_2, self.member1, 200, self.batch)
        investigator.member_answered(self.question_1, self.member2, 10, self.batch)
        investigator.member_answered(self.question_2, self.member2, 100, self.batch)

        investigator_1.member_answered(self.question_1, self.member3, 40, self.batch)
        investigator_1.member_answered(self.question_2, self.member3, 400, self.batch)
        investigator_1.member_answered(self.question_1, self.member4, 50, self.batch)
        investigator_1.member_answered(self.question_2, self.member4, 500, self.batch)
        for household in Household.objects.all():
            HouseholdHead.objects.create(household=household, surname="Surname %s" % household.pk, date_of_birth='1980-09-01')

    def create_household_member(self,household):
        return HouseholdMember.objects.create(surname="Member", date_of_birth=date(1980, 2, 2), male=False,
                                              household=household)

    def test_restricted_permissions(self):
        self.assert_restricted_permission_for("/batches/%s/formulae/%s/" % (self.batch.pk, self.formula_1.pk))

    def test_get(self):
        url = "/batches/%s/formulae/%s/" % (self.batch.pk, self.formula_1.pk)
        response = self.client.get(url)
        self.failUnlessEqual(response.status_code, 200)
        templates = [template.name for template in response.templates]
        self.assertIn('formula/show.html', templates)
        self.assertEquals(type(response.context['locations']), LocationWidget)

    def test_get_for_district(self):
        url = "/batches/%s/formulae/%s/?location=%s" % (self.batch.pk, self.formula_1.pk, self.kampala.pk)
        response = self.client.get(url)
        self.failUnlessEqual(response.status_code, 200)
        templates = [template.name for template in response.templates]
        self.assertIn('formula/show.html', templates)
        self.assertEquals(type(response.context['locations']), LocationWidget)
        self.assertEquals(response.context['computed_value'], 6)
        self.assertEquals(len(response.context['hierarchial_data']), 2)
        self.assertEquals(response.context['hierarchial_data'][self.village_1], 3)
        self.assertEquals(response.context['hierarchial_data'][self.village_2], 9)

    def test_get_for_village(self):
        url = "/batches/%s/formulae/%s/?location=%s" % (self.batch.pk, self.formula_1.pk, self.village_1.pk)
        response = self.client.get(url)
        self.failUnlessEqual(response.status_code, 200)
        templates = [template.name for template in response.templates]
        self.assertIn('formula/show.html', templates)
        self.assertEquals(type(response.context['locations']), LocationWidget)
        self.assertEquals(response.context['computed_value'], 3)
        self.assertEquals(response.context['weights'], 0.3)
        self.assertEquals(len(response.context['household_data']), 2)
        self.assertEquals(response.context['household_data'][self.household_1][self.formula_1.numerator], 20)
        self.assertEquals(response.context['household_data'][self.household_1][self.formula_1.denominator], 200)
        self.assertEquals(response.context['household_data'][self.household_2][self.formula_1.numerator], 10)
        self.assertEquals(response.context['household_data'][self.household_2][self.formula_1.denominator], 100)


class MultichoiceResults(BaseTest):

    def create_household_head(self, uid, investigator):
        self.household = Household.objects.create(investigator=investigator, location=investigator.location,
                                                  uid=uid)
        return HouseholdHead.objects.create(household=self.household, surname="Name " + str(randint(1, 9999)),
                                            date_of_birth="1990-02-09")

    def setUp(self):
        self.client = Client()
        self.member_group = HouseholdMemberGroup.objects.create(name="Greater than 2 years", order=1)
        self.condition = GroupCondition.objects.create(attribute="AGE", value=2, condition="GREATER_THAN")
        self.condition.groups.add(self.member_group)

        user_without_permission = User.objects.create_user(username='useless', email='rajni@kant.com', password='I_Suck')
        raj = self.assign_permission_to(User.objects.create_user('Rajni', 'rajni@kant.com', 'I_Rock'), 'can_view_aggregates')
        self.client.login(username='Rajni', password='I_Rock')

        self.batch = Batch.objects.create(order=1)
        self.question_1 = Question.objects.create(text="Question 1?", answer_type=Question.NUMBER, order=1, group=self.member_group)
        self.question_2 = Question.objects.create(text="Question 2?", answer_type=Question.NUMBER, order=2, group=self.member_group)
        self.question_3 = Question.objects.create(text="This is a question", answer_type=Question.MULTICHOICE, order=3, group=self.member_group)
        self.question_1.batches.add(self.batch)
        self.question_2.batches.add(self.batch)
        self.question_3.batches.add(self.batch)
        self.option_1 = QuestionOption.objects.create(question=self.question_3, text="OPTION 2", order=1)
        self.option_2 = QuestionOption.objects.create(question=self.question_3, text="OPTION 1", order=2)

        module = QuestionModule.objects.create(name='Education', description='Educational Module')
        indicator = Indicator.objects.create(name='Test Indicator', measure=Indicator.MEASURE_CHOICES[0][1],
                                             module=module, description="Indicator 1")

        self.formula = Formula.objects.create(numerator=self.question_3, denominator=self.question_1, indicator=indicator)
        self.country = LocationType.objects.create(name='Country', slug='country')
        self.uganda = Location.objects.create(name='Country', type=self.country)
        country_type_details = LocationTypeDetails.objects.create(country=self.uganda, location_type=self.country)

        self.district = LocationType.objects.create(name = 'District', slug='district')
        self.village = LocationType.objects.create(name = 'Village', slug='village')

        self.kampala = Location.objects.create(name='Kampala', type=self.district, tree_parent=self.uganda)
        self.village_1 = Location.objects.create(name='Village 1', type=self.village, tree_parent=self.kampala)
        self.village_2 = Location.objects.create(name='Village 2', type=self.village, tree_parent=self.kampala)

        backend = Backend.objects.create(name='something')
        investigator = Investigator.objects.create(name="Investigator 1", mobile_number="1", location=self.village_1, backend = backend, weights = 0.3)
        household_1 = Household.objects.create(investigator=investigator, uid=0)
        household_2 = Household.objects.create(investigator=investigator, uid=1)
        household_3 = Household.objects.create(investigator=investigator, uid=2)
        self.household_1 = household_1
        self.household_2 = household_2
        self.household_3 = household_3

        investigator_1 = Investigator.objects.create(name="Investigator 2", mobile_number="2", location=self.village_2, backend = backend, weights = 0.9)
        household_4 = Household.objects.create(investigator=investigator_1, uid=3)
        household_5 = Household.objects.create(investigator=investigator_1, uid=4)
        household_6 = Household.objects.create(investigator=investigator_1, uid=5)

        self.member1 = self.create_household_member(self.household_1)
        self.member2 = self.create_household_member(self.household_2)
        self.member3 = self.create_household_member(self.household_3)
        self.member4 = self.create_household_member(household_4)
        self.member5 = self.create_household_member(household_5)
        self.member6 = self.create_household_member(household_6)

        investigator.member_answered(self.question_1, self.member1, 20, self.batch)
        investigator.member_answered(self.question_3, self.member1, 1, self.batch)
        investigator.member_answered(self.question_1, self.member2, 10, self.batch)
        investigator.member_answered(self.question_3, self.member2, 1, self.batch)
        investigator.member_answered(self.question_1, self.member3, 30, self.batch)
        investigator.member_answered(self.question_3, self.member3, 2, self.batch)

        investigator_1.member_answered(self.question_1, self.member4, 30, self.batch)
        investigator_1.member_answered(self.question_3, self.member4, 2, self.batch)
        investigator_1.member_answered(self.question_1, self.member5, 20, self.batch)
        investigator_1.member_answered(self.question_3, self.member5, 2, self.batch)
        investigator_1.member_answered(self.question_1, self.member6, 40, self.batch)
        investigator_1.member_answered(self.question_3, self.member6, 1, self.batch)
        for household in Household.objects.all():
            HouseholdHead.objects.create(household=household, surname="Surname %s" % household.pk, date_of_birth='1980-09-01')

    def create_household_member(self,household):
        return HouseholdMember.objects.create(surname="Member", date_of_birth=date(1980, 2, 2), male=False,
                                              household=household)

    def test_get_for_district(self):
        url = "/batches/%s/formulae/%s/?location=%s" % (self.batch.pk, self.formula.pk, self.kampala.pk)
        response = self.client.get(url)
        self.failUnlessEqual(response.status_code, 200)
        templates = [template.name for template in response.templates]
        self.assertIn('formula/show.html', templates)
        self.assertEquals(type(response.context['locations']), LocationWidget)
        self.assertEquals(response.context['computed_value'], {self.option_1.text: 27.5, self.option_2.text: 32.5})
        self.assertEquals(len(response.context['hierarchial_data']), 2)
        self.assertEquals(response.context['hierarchial_data'][self.village_1], {self.option_1.text: 15, self.option_2.text: 15})
        self.assertEquals(response.context['hierarchial_data'][self.village_2], {self.option_1.text: 40, self.option_2.text: 50})

    def test_get_for_village(self):
        url = "/batches/%s/formulae/%s/?location=%s" % (self.batch.pk, self.formula.pk, self.village_1.pk)
        response = self.client.get(url)
        self.failUnlessEqual(response.status_code, 200)
        templates = [template.name for template in response.templates]
        self.assertIn('formula/show.html', templates)
        self.assertEquals(type(response.context['locations']), LocationWidget)
        self.assertEquals(response.context['computed_value'], {self.option_1.text: 15, self.option_2.text: 15})
        self.assertEquals(response.context['weights'], 0.3)
        self.assertEquals(len(response.context['household_data']), 3)
        self.assertEquals(response.context['household_data'][self.household_1][self.formula.numerator], self.option_1)
        self.assertEquals(response.context['household_data'][self.household_1][self.formula.denominator], 20)
        self.assertEquals(response.context['household_data'][self.household_2][self.formula.numerator], self.option_1)
        self.assertEquals(response.context['household_data'][self.household_2][self.formula.denominator], 10)
        self.assertEquals(response.context['household_data'][self.household_3][self.formula.numerator], self.option_2)
        self.assertEquals(response.context['household_data'][self.household_3][self.formula.denominator], 30)

    def test_restricted_permissions(self):
        self.assert_restricted_permission_for("/batches/%s/formulae/%s/?location=%s" % (self.batch.pk, self.formula.pk, self.kampala.pk))

    def test_get_data_for_simple_indicator_chart(self):
        Location.objects.all().delete()
        region = LocationType.objects.create(name="Region", slug="region")

        uganda = Location.objects.create(name="Uganda", type=self.country)
        west = Location.objects.create(name="WEST", type=region, tree_parent=uganda)
        central = Location.objects.create(name="CENTRAL", type=region, tree_parent=uganda)
        kampala = Location.objects.create(name="Kampala", tree_parent=central, type=self.district)
        mbarara = Location.objects.create(name="Mbarara", tree_parent=west, type=self.district)


        backend = Backend.objects.create(name='BACKEND')

        investigator = Investigator.objects.create(name="Investigator 1", mobile_number="122000", location=kampala,
                                                   backend=backend)
        investigator_2 = Investigator.objects.create(name="Investigator 1", mobile_number="3333331", location=mbarara,
                                                     backend=backend)

        health_module = QuestionModule.objects.create(name="Health")
        member_group = HouseholdMemberGroup.objects.create(name="Greater than 2 years", order=33)
        self.question_3 = Question.objects.create(text="This is a question",
                                                  answer_type=Question.MULTICHOICE, order=3,
                                                  module=health_module, group=member_group)
        yes_option = QuestionOption.objects.create(question=self.question_3, text="Yes", order=1)
        no_option = QuestionOption.objects.create(question=self.question_3, text="No", order=2)

        self.question_3.batches.add(self.batch)

        indicator = Indicator.objects.create(name="indicator name", description="rajni indicator", measure='Percentage',
                                             batch=self.batch, module=health_module)
        formula = Formula.objects.create(count=self.question_3, indicator=indicator)

        household_head_1 = self.create_household_head(0, investigator)
        household_head_2 = self.create_household_head(1, investigator)
        household_head_3 = self.create_household_head(2, investigator)
        household_head_4 = self.create_household_head(3, investigator)
        household_head_5 = self.create_household_head(4, investigator)

        household_head_6 = self.create_household_head(5, investigator_2)
        household_head_7 = self.create_household_head(6, investigator_2)
        household_head_8 = self.create_household_head(7, investigator_2)
        household_head_9 = self.create_household_head(8, investigator_2)

        investigator.member_answered(self.question_3, household_head_1, yes_option.order, self.batch)
        investigator.member_answered(self.question_3, household_head_2, yes_option.order, self.batch)
        investigator.member_answered(self.question_3, household_head_3, yes_option.order, self.batch)
        investigator.member_answered(self.question_3, household_head_4, no_option.order, self.batch)
        investigator.member_answered(self.question_3, household_head_5, no_option.order, self.batch)

        investigator_2.member_answered(self.question_3, household_head_6, yes_option.order, self.batch)
        investigator_2.member_answered(self.question_3, household_head_7, yes_option.order, self.batch)
        investigator_2.member_answered(self.question_3, household_head_8, no_option.order, self.batch)
        investigator_2.member_answered(self.question_3, household_head_9, no_option.order, self.batch)
        central_region_responses = {yes_option.text: 3, no_option.text: 2}
        west_region_responses = {yes_option.text: 2, no_option.text: 2}
        url = "/indicators/%s/simple/" % indicator.id
        response = self.client.get(url)
        self.failUnlessEqual(response.status_code, 200)
        templates = [template.name for template in response.templates]
        self.assertIn('formula/simple_indicator.html', templates)
        self.assertEquals(response.context['simple_indicator_count'][west], west_region_responses)
        self.assertEquals(response.context['simple_indicator_count'][central], central_region_responses)
