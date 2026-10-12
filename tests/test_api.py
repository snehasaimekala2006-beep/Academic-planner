import pytest
import json
from app.models.syllabus import Topic
from tests.conftest import login_helper


def test_unauthorized_api_requests(client, init_database):
    """
    TEST 12 Acceptance Test:
    Unauthorized API request is attempted. Server returns 401/403/redirect appropriately.
    """
    topic = Topic.query.first()
    
    # 1. Unauthenticated request to protected topic completion API
    res_unauth = client.post(
        f'/api/topics/{topic.id}/completion',
        data=json.dumps({'completed': True}),
        content_type='application/json'
    )
    # LoginManager redirects or returns 401/302 for unauthenticated
    assert res_unauth.status_code in [302, 401]
    
    # 2. Login as Faculty and verify topic completion API succeeds for Faculty
    login_helper(client, 'faculty_cse1', 'FacPass123')
    res_fac = client.post(
        f'/api/topics/{topic.id}/completion',
        data=json.dumps({'completed': True}),
        content_type='application/json'
    )
    assert res_fac.status_code == 200
    assert res_fac.get_json()['role'] == 'faculty'

    # 3. Login as HOD/Admin without student/faculty profile and attempt topic completion API
    login_helper(client, 'hod_cse', 'HodPass123')
    res_forbidden = client.post(
        f'/api/topics/{topic.id}/completion',
        data=json.dumps({'completed': True}),
        content_type='application/json'
    )
    assert res_forbidden.status_code == 403


def test_public_api_endpoints(client, init_database):
    res_b = client.get('/api/branches')
    assert res_b.status_code == 200
    data_b = res_b.get_json()
    assert len(data_b) >= 2
    
    res_s = client.get('/api/semesters')
    assert res_s.status_code == 200
    data_s = res_s.get_json()
    assert len(data_s) >= 1
