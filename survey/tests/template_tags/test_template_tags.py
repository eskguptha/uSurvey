from datetime import date
from django.test.client import Client
from django.contrib.auth.models import User
from django.db.models import Q
from django.core.urlresolvers import reverse
from model_mommy import mommy
from django.test import TestCase
from survey.models import *
from survey.models.locations import *
from survey.templatetags.template_tags import *
from survey.models.questions import *
from survey.models.respondents import (RespondentGroupCondition, GroupTestArgument,
                                       ParameterQuestion, SurveyParameterList, RespondentGroup,
                                       ParameterTemplate)


class TemplateTagsTest(TestCase):

    def setUp(self):
        self.survey = mommy.make(Survey)
        self.batch = mommy.make(Batch, survey=self.survey)
        self.qset = QuestionSet.get(pk=self.batch.id)
        self.question = mommy.make(Question, qset=self.qset, answer_type=NumericalAnswer.choice_name())
        self.ea = EnumerationArea.objects.create(name="BUBEMBE", code="11-BUBEMBE")
        self.investigator = Interviewer.objects.create(name="InvestigatorViewdata",
                                                       ea=self.ea,
                                                       gender='1', level_of_education='Primary',
                                                       language='Eglish', weights=0,date_of_birth='1987-01-01')

        self.surveyAllocation_obj = SurveyAllocation.objects.create(
            interviewer=self.investigator,
            survey=self.survey,
            allocation_ea=self.ea,
            status=1
            )
        self.interview = Interview.objects.create(
            interviewer=self.investigator,
            ea=self.ea,
            survey=self.survey,
            question_set=self.qset,
            )
        self.listingsample = ListingSample.objects.create(survey=self.survey, interview=self.interview)

    def test_get_value(self):
        class A(object):
            b = 5
        a = A()
        self.assertEquals(get_value(a, 'b'), 5)
        a = {'c': 7}
        self.assertEquals(get_value(a, 'c'), 7)

    def test_show_flow_condition(self):
        # flow without validation
        flow = mommy.make(QuestionFlow, question=self.question)
        self.assertEquals(show_condition(flow), '')
        validation = mommy.make(ResponseValidation, validation_test=NumericalAnswer.equals.__name__)
        text_argument = mommy.make(TextArgument, validation=validation, position=1, param=1)
        flow.validation = validation
        self.assertIn(flow.validation.validation_test, show_condition(flow))

    def test_modulo_understands_number_is_modulo_of_another(self):
        self.assertTrue(modulo(4, 2))

    def test_modulo_understands_number_is_not_modulo_of_another(self):
        self.assertFalse(modulo(4, 3))

    def test_knows_mobile_number_not_in_field_string(self):
        self.assertFalse(is_mobile_number(""))

    def test_knows_mobile_number_in_field_string(self):
        self.assertTrue(is_mobile_number("mobile number : 1234567"))

    def test_gets_key_value_from_location_dict(self):
        country_name = 'Uganda'
        district_name = 'Kampala'
        county_name = 'Bukoto'

        location_dict = {'Country': country_name,
                         'District': district_name, 'County': county_name}

        self.assertEqual(get_value(location_dict, 'Country'), country_name)
        self.assertEqual(get_value(location_dict, 'District'), district_name)
        self.assertEqual(get_value(location_dict, 'County'), county_name)

    def test_returns_empty_string_if_key_does_not_exist_from_location_dict(self):
        country_name = 'Uganda'
        district_name = 'Kampala'

        location_dict = {'Country': country_name, 'District': district_name}

        self.assertEqual(get_value(location_dict, 'Country'), country_name)
        self.assertEqual(get_value(location_dict, 'District'), district_name)
        self.assertEqual(get_value(location_dict, 'County'), "")

    def test_should_know_how_to_format_date(self):
        date_entered = date(2008, 4, 5)
        date_expected = "Apr 05, 2008"
        self.assertEqual(format_date(date_entered), date_expected)

    def test_shoud_return_months_given_month_number(self):
        self.assertEqual('January', get_month(0))
        self.assertEqual('March', get_month(2))
        self.assertEqual('N/A', get_month(None))
        self.assertEqual('N/A', get_month(''))

    def test_should_return_url_given_url_name(self):
        self.assertEqual('/surveys/', get_url_without_ids('survey_list_page'))

    def test_should_return_url_given_url_name_and_ids(self):
        self.assertEqual('/surveys/1/delete/',
                         get_url_with_ids(1, 'delete_survey'))
        self.assertEqual('/surveys/1/batches/2/',
                         get_url_with_ids("1, 2", 'batch_show_page'))

    def test_current(self):
        l= [1,2]
        self.assertEqual(1,current(l,0))
        self.assertEqual(None,current(l,10))

    def test_replace(self):
        str = " world"
        self.assertEqual("helloworld", replace_space(str, "hello"))

    def test_should_return_concatenated_ints_in_a_single_string(self):
        self.assertEqual('1, 2', add_string(1, 2))
        self.assertEqual('1, 2', add_string('1', '2'))

    def test_concat_strings(self):
        arg = "abc"
        self.assertEqual('abc', arg)

    def test_condition_text(self):        
        self.assertEqual('EQUALS', condition_text('EQUALS'))
        self.assertEqual('', condition_text('abv'))

    def test_should_return_repeated_string(self):
        self.assertEqual('000', repeat_string('0', 4))

    def test_should_return_selected_for_selected_batch(self):
        survey = Survey.objects.create(
            name="open survey", description="open survey", has_sampling=True)
        batch = Batch.objects.create(name="open survey", survey=survey)
        self.assertEqual("selected='selected'",
                         is_survey_selected_given(survey, batch))

    def test_should_return_selected_for_is_selected(self):
        # survey = Survey.objects.create(
        #     name="open survey", description="open survey", has_sampling=True)
        batch = Batch.objects.create(name="batchnames")        
        self.assertEqual("selected='selected'",
                         is_selected(batch,batch))        

    def test_should_return_none_for_selected_batch(self):
        survey = Survey.objects.create(
            name="open survey", description="open survey", has_sampling=True)
        batch = Batch.objects.create(name="Batch not belonging to survey")
        self.assertIsNone(is_survey_selected_given(survey, batch))

    def test_should_return_none_if_selected_batch_has_no_survey(self):
        survey = Survey.objects.create(
            name="open survey", description="open survey", has_sampling=True)
        batch = Batch.objects.create(name="Batch not belonging to survey")
        self.assertIsNone(is_survey_selected_given(survey, batch))

    def test_should_return_none_when_selected_batch_is_none(self):
        survey = Survey.objects.create(
            name="open survey", description="open survey", has_sampling=True)
        self.assertIsNone(is_survey_selected_given(survey, None))

    def test_knows_batch_is_activated_for_non_response_for_location(self):
        country = LocationType.objects.create(name="Country", slug='country')
        district = LocationType.objects.create(
            name="District", parent=country, slug='district')
        uganda = Location.objects.create(name="Uganda", type=country)
        kampala = Location.objects.create(
            name="Kampala", type=district, parent=uganda)

        all_open_locations = Location.objects.all()
        self.assertEqual("checked='checked'", non_response_is_activefor(
            all_open_locations, kampala))

    def test_knows_batch_is_not_activated_for_non_response_for_location(self):
        country = LocationType.objects.create(name="Country", slug='country')
        district = LocationType.objects.create(
            name="District", parent=country, slug='district')
        uganda = Location.objects.create(name="Uganda", type=country)
        kampala = Location.objects.create(
            name="Kampala", type=district, parent=uganda)

        all_open_locations = Location.objects.filter(name="Mbarara")
        self.assertEqual(None, non_response_is_activefor(
            all_open_locations, kampala))

    def test_knows_ea_is_selected_given_location_data(self):
        country = LocationType.objects.create(name="Country", slug='country')
        district = LocationType.objects.create(
            name="District", parent=country, slug='district')
        uganda = Location.objects.create(name="Uganda", type=country)

        kisasi = Location.objects.create(
            name='Kisaasi', type=district, parent=uganda)

        ea1 = EnumerationArea.objects.create(name="EA Kisasi1")
        ea2 = EnumerationArea.objects.create(name="EA Kisasi2")
        ea1.locations.add(kisasi)
        ea2.locations.add(kisasi)
 
    def test_ea_is_location_selected(self):
        country = LocationType.objects.create(name="Country1", slug='country')
        district = LocationType.objects.create(
            name="District1", parent=country, slug='district')
        uganda = Location.objects.create(name="Uganda1", type=country)

        kisasi = Location.objects.create(
            name='Kisaasi1', type=district, parent=uganda)

        ea1 = EnumerationArea.objects.create(name="EA Kisasi11")
        ea2 = EnumerationArea.objects.create(name="EA Kisasi12")
        ea1.locations.add(kisasi)
        ea2.locations.add(kisasi)

    def test_batch_is_selected(self):
        batch = Batch.objects.create(order=1, name="Batch name")
        self.assertFalse(batch.is_open())
        country = LocationType.objects.create(name='Country', slug='country')
        district = LocationType.objects.create(
            name='District', parent=country, slug='district')
        uganda = Location.objects.create(name="Uganda", type=country)
        kampala = Location.objects.create(
            name="Kampala", type=district, parent=uganda)
        batch.open_for_location(kampala)
        expected = "selected='selected'"
        self.assertEqual(expected, is_selected(batch, batch))

    def test_is_batch_open_for_location(self):
        batch = Batch.objects.create(order=1, name="Batch name")
        self.assertFalse(batch.is_open())
        country = LocationType.objects.create(name='Country', slug='country')
        district = LocationType.objects.create(
            name='District', parent=country, slug='district')
        uganda = Location.objects.create(name="Uganda", type=country)
        kampala = Location.objects.create(
            name="Kampala", type=district, parent=uganda)
        batch.open_for_location(kampala)
        open_locations = [uganda, kampala]
        self.assertEqual("checked='checked'",
                         is_batch_open_for_location(open_locations, kampala))

    def test_condition(self):
        condition = RespondentGroupCondition.objects.create(validation_test="EQUALS",
                                                            respondent_group_id=1,test_question_id=1)
        self.assertEqual("EQUALS", condition.validation_test)

    def test_quest_validation_opts(self):
        batch = Batch.objects.create(order=1, name="Batch name")        
        condition = RespondentGroupCondition.objects.create(validation_test="EQUALS",
                                                            respondent_group_id=1,
                                                            test_question_id=1)

    def test_ancestors_reversed_reversed(self):
        country = LocationType.objects.create(name='Country', slug='country')
        region = LocationType.objects.create(name='Region', slug='region')
        city = LocationType.objects.create(name='City', slug='city')
        parish = LocationType.objects.create(name='Parish', slug='parish')
        village = LocationType.objects.create(name='Village', slug='village')
        subcounty = LocationType.objects.create(
            name='Subcounty', slug='subcounty')
        africa = Location.objects.create(name='Africa', type=country)
        uganda = Location.objects.create(
            name='Uganda', type=region, parent=africa)
        abim = Location.objects.create(name='ABIM', parent=uganda, type=city)
        abim_son = Location.objects.create(
            name='LABWOR', parent=abim, type=parish)
        abim_son_son = Location.objects.create(
            name='KALAKALA', parent=abim_son, type=village)
        abim_son_daughter = Location.objects.create(
            name='OYARO', parent=abim_son, type=village)
        abim_son_daughter_daughter = Location.objects.create(
            name='WIAWER', parent=abim_son_daughter, type=subcounty)
        abim_son_son_daughter = Location.objects.create(
            name='ATUNGA', parent=abim_son_son, type=subcounty)
        abim_son_son_son = Location.objects.create(
            name='WICERE', parent=abim_son_son, type=subcounty)
        self.assertEqual([], ancestors_reversed(africa))
        self.assertEqual([africa], ancestors_reversed(uganda))
        self.assertEqual([africa, uganda], ancestors_reversed(abim))
        self.assertEqual([africa, uganda, abim], ancestors_reversed(abim_son))
        self.assertEqual([africa, uganda, abim, abim_son],
                         ancestors_reversed(abim_son_son))
        self.assertEqual([africa, uganda, abim, abim_son,
                          abim_son_son], ancestors_reversed(abim_son_son_son))

    def test_trim(self):
        str1 = "survey_test"
        self.assertEquals(str1.strip(), trim(str1))
    # def test_get_question_text(self):
    #     self.assertIsNotNone(get_question_text(self.question))

    # def test_get_name_references(self):
    #     self.assertIsNotNone(get_name_references(self.qset))        
    # def test_get_node_path(self):
    #     self.assertIsNotNone(get_node_path(self.question))

    # def test_get_loop_aware_path(self):
    #     self.assertIsNotNone(get_loop_aware_path(self.question))
    

