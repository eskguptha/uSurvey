from survey.models import LocationTypeDetails, Location, LocationType, Household, HouseholdMember, \
    HouseholdMemberGroup, MultiChoiceAnswer, MultiSelectAnswer
from survey.utils.views_helper import get_ancestors
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from datetime import datetime
import csv, StringIO


class ResultComposer:
    def __init__(self, user, results_download_service):
        self.results_download_service = results_download_service
        self.user = user

    def send_mail(self):
        attachment_name = '%s.csv' % (self.results_download_service.batch.name if self.results_download_service.batch  \
        else self.results_download_service.survey.name)
        subject = 'Completion report for %s'  % attachment_name
        text = 'Completion report for %s. Date: %s'  % (attachment_name, datetime.now())
        print 'commencing...'
        try:
            mail = EmailMessage(subject, text, settings.DEFAULT_EMAIL_SENDER, [self.user.email, ])
            data = self.results_download_service.generate_report()
            #data = [[unicode('"%s"' % entry) for entry in entries] for entries in data]
            f = StringIO.StringIO()
            writer = csv.writer(f)
            map(lambda row: writer.writerow(row), data)
            #data = [','.join([unicode('"%s"' % entry) for entry in entries]) for entries in data]
            f.seek(0)
            mail.attach(attachment_name, f.read(), 'text/csv')
            f.close()
            sent = mail.send()
            print 'Emailed!! ', sent
        except Exception, ex:
            print 'error while sending mail: %s', str(ex)



class ResultsDownloadService(object):
    # MEMBER_ATTRS = {
    #     'id' : 'Household ID',
    #      'name' : 'Name', 'Age', 'Date of Birth', 'Gender'
    # }
    def __init__(self, survey=None, batch=None, restrict_to=None):
        self.batch = batch
        self.survey, self.questions = self._set_survey_and_questions(survey)
        self.locations = restrict_to or Location.objects.all()

    def _set_survey_and_questions(self, survey):
        if self.batch:
            return self.batch.survey, self.batch.survey_questions
        survey_questions = []
        map(lambda batch: survey_questions.extend(list(batch.survey_questions)), survey.batches.all())
        return survey, survey_questions

    def set_report_headers(self):
        header = list(LocationType.objects.exclude(name__iexact="country").values_list('name', flat=True))

        other_headers = ['EA', 'Household Number', 'Name', 'Age', 'Date of Birth', 'Gender']
        header.extend(other_headers)
        header.extend(self.question_headers())
        return header

    def question_headers(self):
        header = []
        for question in self.questions:
            header.append(question.identifier)
            # if question.answer_type in [MultiChoiceAnswer.choice_name(), MultiSelectAnswer.choice_name()]:
            #     header.append('')
        return header

    def get_summarised_answers(self):
        data = []
        all_households = Household.objects.filter(listing__survey_houselistings__survey=self.survey)
        locations = list(set(all_households.values_list('listing__ea__locations', flat=True)))
        for location_id in locations:
            households_in_location = all_households.filter(listing__ea__locations=location_id)
            household_location = Location.objects.get(id=location_id)
            location_ancestors = household_location.get_ancestors().exclude(name__iexact='country').values_list('name', flat=True)
            answers = []
            for household in households_in_location:
                for member in household.members.all():
                    member_gender = 'Male' if member.gender == HouseholdMember.MALE else 'Female'
                    answers = list(location_ancestors)
                    answers.extend([household.listing.ea, household.house_number, '%s-%s' % (member.surname, member.first_name), str(member.age),
                                         member.date_of_birth.strftime(settings.DATE_FORMAT),
                                         member_gender])
                    for question in self.questions:
                        answers.append(member.reply(question))
            data.append(answers)
        return data

    def generate_report(self):
        data = [self.set_report_headers()]
        data.extend(self.get_summarised_answers())
        return data

    def _get_ancestors_names(self, household_location, exclude_type='country'):
        location_ancestors = get_ancestors(household_location, include_self=True)
        if exclude_type:
            exclude_location = Location.objects.filter(type__name__iexact=exclude_type.lower())
            for location in exclude_location:
                location_ancestors.remove(location)
        result= [ancestor.name for ancestor in location_ancestors]
        result.reverse()
        return result

