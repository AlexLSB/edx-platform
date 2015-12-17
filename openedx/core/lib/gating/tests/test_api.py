"""
Tests for the gating API
"""
from mock import patch
from milestones.tests.utils import MilestonesTestCaseMixin
from opaque_keys.edx.keys import CourseKey, UsageKey
from openedx.core.lib.gating import api as gating_api
from openedx.core.lib.gating.exceptions import GatingValidationError


@patch.dict('django.conf.settings.FEATURES', {'MILESTONES_APP': True})
class TestGatingApi(MilestonesTestCaseMixin):
    """
    Tests for the gating API
    """

    def setUp(self):
        """
        Initial test setup
        """
        super(TestGatingApi, self).setUp()

        self.test_course_key = CourseKey.from_string('the/course/key')
        self.test_usage_key = UsageKey.from_string('i4x://the/content/key/12345678')

    @patch('openedx.core.lib.gating.api.log.warning')
    def test_get_prerequisite_milestone_returns_none(self, mock_log):
        """ Test test_get_prerequisite_milestone_returns_none """
        prereq = gating_api._get_prerequisite_milestone(self.test_usage_key)  # pylint: disable=protected-access
        self.assertIsNone(prereq)
        self.assertTrue(mock_log.called)

    def test_get_prerequisite_milestone_returns_milestone(self):
        """ Test test_get_prerequisite_milestone_returns_milestone """
        gating_api.add_prerequisite(self.test_course_key, self.test_usage_key)
        prereq = gating_api._get_prerequisite_milestone(self.test_usage_key)  # pylint: disable=protected-access
        self.assertIsNotNone(prereq)

    def test_validate_min_score_is_valid(self):
        """ Test test_validate_min_score_is_valid """
        # pylint: disable=protected-access
        self.assertIsNone(gating_api._validate_min_score(''))
        self.assertIsNone(gating_api._validate_min_score('0'))
        self.assertIsNone(gating_api._validate_min_score('50'))
        self.assertIsNone(gating_api._validate_min_score('100'))

    def test_validate_min_score_non_integer(self):
        """ Test test_validate_min_score_non_integer """
        # pylint: disable=protected-access
        with self.assertRaises(GatingValidationError):
            gating_api._validate_min_score('abc')

    def test_validate_min_score_below_lower_bound(self):
        """ Test test_validate_min_score_below_lower_bound """
        # pylint: disable=protected-access
        with self.assertRaises(GatingValidationError):
            gating_api._validate_min_score('-10')

    def test_validate_min_score_above_upper_bound(self):
        """ Test test_validate_min_score_below_lower_bound """
        # pylint: disable=protected-access
        with self.assertRaises(GatingValidationError):
            gating_api._validate_min_score('110')
