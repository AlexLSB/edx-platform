"""
Views related to EdxNotes.
"""
import json
import logging
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.conf import settings
from django.core.urlresolvers import reverse
from django.views.decorators.http import require_GET
from edxmako.shortcuts import render_to_response
from opaque_keys.edx.keys import CourseKey
from courseware.courses import get_course_with_access
from courseware.model_data import FieldDataCache
from courseware.module_render import get_module_for_descriptor
from util.json_request import JsonResponse, JsonResponseBadRequest
from edxnotes.exceptions import EdxNotesParseError, EdxNotesServiceUnavailable
from edxnotes.helpers import (
    get_edxnotes_id_token,
    get_notes,
    is_feature_enabled,
    get_course_position,
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
)


log = logging.getLogger(__name__)


@login_required
def edxnotes(request, course_id):
    """
    Displays the EdxNotes page.

    Arguments:
        request: HTTP request object
        course_id: course id

    Returns:
        Rendered HTTP response.
    """
    course_key = CourseKey.from_string(course_id)
    course = get_course_with_access(request.user, "load", course_key)

    if not is_feature_enabled(course):
        raise Http404

    try:
        notes_info = get_notes(request, course)
    except (EdxNotesParseError, EdxNotesServiceUnavailable) as err:
        return JsonResponseBadRequest({"error": err.message}, status=500)

    context = {
        "course": course,
        "notes_endpoint": reverse("notes", kwargs={"course_id": course_id}),
        "notes": notes_info,
        "page_size": DEFAULT_PAGE_SIZE,
        "debug": json.dumps(settings.DEBUG),
        'position': None,
    }

    if len(json.loads(notes_info)['results']) == 0:
        field_data_cache = FieldDataCache.cache_for_descriptor_descendents(
            course.id, request.user, course, depth=2
        )
        course_module = get_module_for_descriptor(
            request.user, request, course, field_data_cache, course_key, course=course
        )
        position = get_course_position(course_module)
        if position:
            context.update({
                'position': position,
            })

    return render_to_response("edxnotes/edxnotes.html", context)


@require_GET
@login_required
def notes(request, course_id):
    """
    Notes view to handle list and search requests.

    Query parameters:
        page: page number to get
        page_size: number of items in the page
        text: text string to search. If `text` param is missing then get all the
              notes for the current user for this course else get only those notes
              which contain the `text` value.

    Arguments:
        request: HTTP request object
        course_id: course id

    Returns:
        Paginated response as JSON. A sample response is below.
        {
          "count": 101,
          "num_pages": 11,
          "current_page": 1,
          "results": [
            {
              "chapter": {
                "index": 4,
                "display_name": "About Exams and Certificates",
                "location": "i4x://org/course/category/name@revision",
                "children": [
                  "i4x://org/course/category/name@revision"
                ]
              },
              "updated": "Dec 09, 2015 at 09:31 UTC",
              "tags": ["shadow","oil"],
              "quote": "foo bar baz",
              "section": {
                "display_name": "edX Exams",
                "location": "i4x://org/course/category/name@revision",
                "children": [
                  "i4x://org/course/category/name@revision",
                  "i4x://org/course/category/name@revision",
                ]
              },
              "created": "2015-12-09T09:31:17.338305Z",
              "ranges": [
                {
                  "start": "/div[1]/p[1]",
                  "end": "/div[1]/p[1]",
                  "startOffset": 0,
                  "endOffset": 6
                }
              ],
              "user": "50cf92f9a3d8489df95e583549b919df",
              "text": "first angry height hungry structure",
              "course_id": "edx/DemoX/Demo",
              "id": "1231",
              "unit": {
                "url": "/courses/edx%2FDemoX%2FDemo/courseware/1414ffd5143b4b508f739b563ab468b7/workflow/1",
                "display_name": "EdX Exams",
                "location": "i4x://org/course/category/name@revision"
              },
              "usage_id": "i4x://org/course/category/name@revision"
            } ],
          "next": "http://0.0.0.0:8000/courses/edx%2FDemoX%2FDemo/edxnotes/notes/?page=2&page_size=10",
          "start": 0,
          "previous": null
        }
    """
    course_key = CourseKey.from_string(course_id)
    course = get_course_with_access(request.user, 'load', course_key)

    if not is_feature_enabled(course):
        raise Http404

    page = request.GET.get('page') or DEFAULT_PAGE
    page_size = request.GET.get('page_size') or DEFAULT_PAGE_SIZE
    text = request.GET.get('text')

    try:
        notes_info = get_notes(
            request,
            course,
            page=page,
            page_size=page_size,
            text=text
        )
    except (EdxNotesParseError, EdxNotesServiceUnavailable) as err:
        return JsonResponseBadRequest({"error": err.message}, status=500)

    return HttpResponse(notes_info, content_type="application/json")


# pylint: disable=unused-argument
@login_required
def get_token(request, course_id):
    """
    Get JWT ID-Token, in case you need new one.
    """
    return HttpResponse(get_edxnotes_id_token(request.user), content_type='text/plain')


@login_required
def edxnotes_visibility(request, course_id):
    """
    Handle ajax call from "Show notes" checkbox.
    """
    course_key = CourseKey.from_string(course_id)
    course = get_course_with_access(request.user, "load", course_key)
    field_data_cache = FieldDataCache([course], course_key, request.user)
    course_module = get_module_for_descriptor(
        request.user, request, course, field_data_cache, course_key, course=course
    )

    if not is_feature_enabled(course):
        raise Http404

    try:
        visibility = json.loads(request.body)["visibility"]
        course_module.edxnotes_visibility = visibility
        course_module.save()
        return JsonResponse(status=200)
    except (ValueError, KeyError):
        log.warning(
            "Could not decode request body as JSON and find a boolean visibility field: '%s'", request.body
        )
        return JsonResponseBadRequest()
