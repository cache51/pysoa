from __future__ import absolute_import, unicode_literals

import datetime
import os
import sys
import uuid
import unittest

from conformity import fields
import pytest
import six

from pysoa.common.types import Error
from pysoa.server.errors import JobError
from pysoa.server.action.base import Action
from pysoa.server.server import Server
from pysoa.test.plan import ServicePlanTestCase


# Below we set up two little mini-services with which we can test fixtures

class RootAction(Action):
    request_schema = fields.Dictionary(
        {'number': fields.Integer(), 'base': fields.Integer()},
        optional_keys=('base', ),
    )

    response_schema = fields.Dictionary({'number_root': fields.Integer()})

    def run(self, request):
        base = request.body.get('base', 2)
        return {'number_root': int(round(request.body['number'] ** (1 / float(base))))}


class LoginAction(Action):
    request_schema = fields.Dictionary({'username': fields.UnicodeString()})

    response_schema = fields.Dictionary(
        {'session': fields.Dictionary({'session_id': fields.UnicodeString(), 'user': fields.UnicodeString()})},
    )

    def run(self, request):
        return {'session': {'session_id': six.text_type(uuid.uuid4().hex), 'user': request.body['username']}}


class EchoAction(Action):
    request_schema = fields.SchemalessDictionary()

    response_schema = fields.Dictionary(
        {
            'request_body': fields.SchemalessDictionary(),
            'request_context': fields.SchemalessDictionary(),
            'request_switches': fields.List(fields.Integer()),
            'request_control': fields.SchemalessDictionary(),
        },
    )

    def run(self, request):
        return {
            'request_body': request.body,
            'request_context': request.context,
            'request_switches': sorted(list(request.switches)),
            'request_control': request.control,
        }


class TypesEchoAction(Action):
    request_schema = fields.Dictionary(
        {
            'an_int': fields.Integer(),
            'a_float': fields.Float(),
            'a_bool': fields.Boolean(),
            'a_bytes': fields.ByteString(),
            'a_string': fields.UnicodeString(),
            'a_datetime': fields.DateTime(),
            'a_date': fields.Date(),
            'a_time': fields.Time(),
            'a_list': fields.List(fields.Anything(), max_length=0),
            'a_dict': fields.Nullable(fields.Dictionary({})),
        },
        optional_keys=(
            'an_int', 'a_float', 'a_bool', 'a_bytes', 'a_string', 'a_datetime', 'a_date', 'a_time', 'a_list', 'a_dict',
        ),
    )

    response_schema = fields.Dictionary(
        {'r_{}'.format(k): v for k, v in six.iteritems(request_schema.contents)},
        optional_keys=('r_{}'.format(k) for k in request_schema.optional_keys),
    )

    def run(self, request):
        return {'r_{}'.format(k): v for k, v in six.iteritems(request.body)}


class GetTinyImageAction(Action):
    response_schema = fields.Dictionary({'tiny_image': fields.ByteString()})

    def run(self, request):
        with open(os.path.dirname(__file__) + '/tiny-image.gif', 'rb') as file_input:
            return {'tiny_image': file_input.read()}


class GetDatetimeAction(Action):
    response_schema = fields.Dictionary({'current_datetime': fields.DateTime()})

    def run(self, request):
        return {'current_datetime': datetime.datetime.now()}


class WalkAction(Action):
    request_schema = fields.Dictionary({'value': fields.Any(fields.Integer(), fields.Float())})

    response_schema = request_schema

    add = 1

    def run(self, request):
        return {'value': request.body['value'] + self.add}


class RunAction(WalkAction):
    add = 5


class FirstStubServer(Server):
    service_name = 'stub'
    action_class_map = {
        'root': RootAction,
        'login': LoginAction,
        'echo': EchoAction,
        'types_echo': TypesEchoAction,
        'get_tiny_image': GetTinyImageAction,
        'get_current_datetime': GetDatetimeAction,
    }


class SecondStubServer(Server):
    service_name = 'flub'
    action_class_map = {
        'walk': WalkAction,
        'run': RunAction,
    }


# Let's put in place some instrumentation so that we can test our tests, because we're actually testing the plugin
# and grammar here, not an actual service.

class PluginTestingOrderOfOperationsTestCase(ServicePlanTestCase):
    @classmethod
    def setUpClass(cls):
        super(PluginTestingOrderOfOperationsTestCase, cls).setUpClass()
        cls.order_of_operations.append('setUpClass')

    @classmethod
    def tearDownClass(cls):
        super(PluginTestingOrderOfOperationsTestCase, cls).tearDownClass()
        cls.order_of_operations.append('tearDownClass')

    def set_up_test_fixture(self, test_fixture, **kwargs):
        super(PluginTestingOrderOfOperationsTestCase, self).set_up_test_fixture(test_fixture, **kwargs)
        self.order_of_operations.append('set_up_test_fixture')

    def tear_down_test_fixture(self, test_fixture, **kwargs):
        super(PluginTestingOrderOfOperationsTestCase, self).tear_down_test_fixture(test_fixture, **kwargs)
        self.order_of_operations.append('tear_down_test_fixture')

    def setUp(self):
        super(PluginTestingOrderOfOperationsTestCase, self).setUp()
        self.order_of_operations.append('setUp')

    def tearDown(self):
        super(PluginTestingOrderOfOperationsTestCase, self).tearDown()
        self.order_of_operations.append('tearDown')

    def set_up_test_case(self, test_case, test_fixture, **kwargs):
        super(PluginTestingOrderOfOperationsTestCase, self).set_up_test_case(test_case, test_fixture, **kwargs)
        self.order_of_operations.append(
            'set_up_test_case.{fixture}.{case}'.format(fixture=test_case['fixture_name'], case=test_case['name']),
        )

    def tear_down_test_case(self, test_case, test_fixture, **kwargs):
        super(PluginTestingOrderOfOperationsTestCase, self).tear_down_test_case(test_case, test_fixture, **kwargs)
        self.order_of_operations.append(
            'tear_down_test_case.{fixture}.{case}'.format(fixture=test_case['fixture_name'], case=test_case['name']),
        )

    def set_up_test_case_action(self, action_name, action_case, test_case, test_fixture, **kwargs):
        super(PluginTestingOrderOfOperationsTestCase, self).set_up_test_case_action(
            action_name, action_case, test_case, test_fixture, **kwargs
        )
        self.order_of_operations.append('set_up_test_case_action.{fixture}.{case}.{action}'.format(
            fixture=test_case['fixture_name'],
            case=test_case['name'],
            action=action_name,
        ))

    def tear_down_test_case_action(self, action_name, action_case, test_case, test_fixture, **kwargs):
        super(PluginTestingOrderOfOperationsTestCase, self).tear_down_test_case_action(
            action_name, action_case, test_case, test_fixture, **kwargs
        )
        self.order_of_operations.append('tear_down_test_case_action.{fixture}.{case}.{action}'.format(
            fixture=test_case['fixture_name'],
            case=test_case['name'],
            action=action_name,
        ))


# Now let's declare our tests

class TestFirstFixtures(PluginTestingOrderOfOperationsTestCase):
    server_class = FirstStubServer
    server_settings = {}
    fixture_path = os.path.dirname(__file__) + '/first_fixtures'
    model_constants = {
        'test_first_user': {'username': 'beamerblvd'},
        'test_users': [
            {'username': 'guitar-king'},
            {'username': 'allison.agd'},
        ],
    }

    order_of_operations = []

    @staticmethod
    def _process_stub_action_stubbed_out(body):
        return {
            'user': {
                'id': body['user_id'],
                'username': 'user_{}'.format(body['user_id']),
            },
        }

    @staticmethod
    def _process_stub_action_stub_job_error(body):
        raise JobError(errors=[
            Error(code='CAT_ERROR', message='Your cat broke the vase'),
            Error(code='DOG_ERROR', message='Your dog ate the couch'),
        ])


class IntermediateTestCase(unittest.TestCase):
    test_anything_method_was_run = False
    following_test_function_was_run = False

    # noinspection PyMethodMayBeStatic
    def test_anything(self):
        """This helps us make sure no tests get lost in the collection manipulation"""
        IntermediateTestCase.test_anything_method_was_run = True


def test_following():
    """This helps us make sure no tests get lost in the collection manipulation"""
    IntermediateTestCase.following_test_function_was_run = True


class TestSecondFixtures(PluginTestingOrderOfOperationsTestCase):
    server_class = SecondStubServer
    server_settings = {}
    fixture_path = os.path.dirname(__file__) + '/second_fixtures'

    order_of_operations = []

    def test_a_regular_case(self):
        """
        Test that a regular test case works properly
        """
        self.order_of_operations.append('test_a_regular_case')

    @pytest.mark.skip(reason='Making sure skipping still works')
    def test_a_pytest_skipped_case(self):
        """
        Test that a regular skipped test case works properly
        """
        self.order_of_operations.append('test_a_pytest_skipped_case')
        self.fail('If this is not skipped, it should fail')

    def test_another_regular_case(self):
        """
        Test that another regular test case works properly
        """
        self.order_of_operations.append('test_another_regular_case')

    @unittest.skip(reason='Making sure skipping still works')
    def test_a_unittest_skipped_case(self):
        """
        Test that a regular skipped test case works properly
        """
        self.order_of_operations.append('test_a_unittest_skipped_case')
        self.fail('If this is not skipped, it should fail')


@unittest.skip(reason='Making sure skipping an entire class (and all of its fixtures) works')
class TestUnittestSkippedFixtures(PluginTestingOrderOfOperationsTestCase):
    server_class = SecondStubServer
    server_settings = {}
    fixture_path = os.path.dirname(__file__) + '/second_fixtures'

    order_of_operations = []


@pytest.mark.skip(reason='Making sure skipping an entire class (and all of its fixtures) works')
class TestPyTestSkippedFixtures(PluginTestingOrderOfOperationsTestCase):
    server_class = SecondStubServer
    server_settings = {}
    fixture_path = os.path.dirname(__file__) + '/second_fixtures'

    order_of_operations = []


@pytest.mark.skipif(sys.version_info > (2, 6), reason='Making sure skipping an entire class with skipif works')
class TestPyTestSkippedIfFixtures(PluginTestingOrderOfOperationsTestCase):
    # Also tests that the `custom_fixtures` feature works
    server_class = SecondStubServer
    server_settings = {}
    custom_fixtures = (
        os.path.dirname(__file__) + '/second_fixtures/walk_and_run.pysoa',
    )

    order_of_operations = []


class TestGlobalSkippedFixtureTests(PluginTestingOrderOfOperationsTestCase):
    server_class = SecondStubServer
    server_settings = {}
    fixture_path = os.path.dirname(__file__) + '/skipped_fixtures'

    order_of_operations = []
