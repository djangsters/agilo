from agilo.test import Usernames
from agilo.test.functional.agilo_functional_testcase import AgiloFunctionalTestCase
from agilo.ticket import AgiloTicket, AgiloTicketSystem

__author__ = 'cdicosmo'

class BatchModifyTest(AgiloFunctionalTestCase):
    testtype = 'windmill'
    is_abstract_test = True

    def should_be_skipped(self):
        return (not AgiloTicketSystem.is_trac_1_0()) or (self.super())


    def setUp(self):
        self.super()
        self.tester.login_as(Usernames.admin)
        self.teh.create_backlog()


    def go_to_custom_query(self):
        self.windmill.waits.forElement(link=u'Custom Query', timeout=u'8000')
        self.windmill.click(link=u'Custom Query')
        self.windmill.waits.forPageLoad(timeout=u'20000')


    def runTest(self):
        self.windmill_tester.login_as(Usernames.admin)

        self.windmill_tester.go_to_view_tickets()
        self.go_to_custom_query()

        self.windmill.click(xpath=u"//td[contains(@class,'trac-clause')]//input[@type='button']")
        self.windmill.waits.forElement(timeout=u'8000', name=u'update')




class BatchModifyMultipleTicketsStatus (BatchModifyTest):

    def runTest(self):
        self.super()

        self.windmill.click(name=u'update')
        self.windmill.waits.forPageLoad(timeout=u'20000')
        self.windmill.check(name=u'selected_ticket')
        self.windmill.check(xpath=u"//thead//input[contains(@type,'checkbox')]")
        self.windmill.click(link=u'Batch Modify')
        new_tickets_length = self.windmill_tester.output_for_js("$('table.listing.tickets .status:contains(\"new\")').length")

        self.windmill.click(id=u'action_resolve')
        self.windmill.radio(id=u'action_resolve')
        self.windmill.click(id=u'batchmod_submit')
        self.windmill.waits.forPageLoad(timeout=u'20000')
        closed_tickets_length = self.windmill_tester.output_for_js("$('table.listing.tickets .status:contains(\"closed\")').length")
        self.assert_equals(new_tickets_length,closed_tickets_length,"The number of tickets closed doesn't match")

class BatchModifyMultipleTicketsAgilo (BatchModifyTest):

    def runTest(self):
        self.super()
        story_points = 1
        self.windmill.click(xpath=u'//a[contains(@href,"#no2")]')
        self.windmill.waits.forElement(timeout=u'8000', xpath=u'//input[contains(@value,"rd_points")][contains(@type,"checkbox")]')
        self.windmill.check(xpath=u'//input[contains(@value,"rd_points")][contains(@type,"checkbox")]')

        self.windmill.click(name=u'update')

        new_tickets_length = self.windmill_tester.output_for_js("$('table.listing.tickets .type:contains(\"story\")').length")
        self.windmill.waits.forPageLoad(timeout=u'20000')
        for row in range(1,(new_tickets_length+1)):
            self.windmill.check(xpath=u"(//td[contains(@class,'type')][contains(text(),'story')]//ancestor::tr//td//input[contains(@type,'checkbox')])[%d]" % row)

        self.windmill.click(link=u'Batch Modify')

        self.windmill.select(id=u'add_batchmod_field',val=u'rd_points')
        self.windmill.select(name=u"batchmod_value_rd_points", val=u'1')
        self.windmill.click(id=u'batchmod_submit')
        self.windmill.waits.forPageLoad(timeout=u'20000')
        closed_tickets_length = self.windmill_tester.output_for_js("$('table.listing.tickets .rd_points:contains(\"%d\")').length" % story_points)

        self.assert_equals(new_tickets_length,closed_tickets_length,"The number of tickets closed doesn't match")

class BatchModifyMultipleTicketsComment (BatchModifyTest):

    def runTest(self):
        self.super()

        self.windmill.click(name=u'update')
        self.windmill.waits.forPageLoad(timeout=u'20000')

        self.windmill.check(name=u'selected_ticket')
        self.windmill.check(xpath=u"//thead//input[contains(@type,'checkbox')]")
        self.windmill.click(link=u'Batch Modify')

        comment = "comment everything"
        self.windmill.type(id=u'batchmod_value_comment', text =comment)

        self.windmill.click(id=u'batchmod_submit')
        self.windmill.waits.forPageLoad(timeout=u'20000')
        js = "$('table.listing.tickets .id:contains(\"#\")').text()"
        tickets_ids = self.windmill_tester.output_for_js(js).split('#')[1:]
        for ticket_id in tickets_ids:
            comment_tuple = AgiloTicket(self.env, ticket_id).get_comment_history(1)[0]
            self.assert_equals(comment_tuple[len(comment_tuple)-1], comment)


class BatchModifyExcludesReferenceFields (BatchModifyTest):

    def runTest(self):
        self.super()

        self.windmill.click(name=u'update')
        self.windmill.waits.forPageLoad(timeout=u'20000')

        self.windmill.check(name=u'selected_ticket')
        self.windmill.check(xpath=u"//thead//input[contains(@type,'checkbox')]")
        self.windmill.click(link=u'Batch Modify')
        js = "$('#add_batchmod_field :contains(\"%s\")').length" % 'Reference'
        matching_nodes_length = self.windmill_tester.output_for_js(js)
        self.assert_equals(matching_nodes_length, 0, "Found reference fields in batch modify UI")
