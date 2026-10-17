"""
Tests for newly added features:
1. Activity Labels & Questionnaire Settings
2. Lead Questionnaire retrieval & updates
3. Lead Creation with profession & service_type
4. CSV / JSON Lead Import with duplicate detection
5. Auto-update lead stages trigger
6. Sales Manager summary endpoint
"""

import os
import sys
import json
import io

os.environ['FLASK_CONFIG'] = 'testing'
os.environ['DISABLE_SCHEDULER'] = 'true'

sys.path.insert(0, os.path.dirname(__file__))
from app import create_app
from app.extensions import db
from app.models import User, UserRole, Opportunity, Contact, PipelineStage

app = create_app('testing')
client = app.test_client()

def test_suite():
    print("\nRunning New Features Test Suite...")
    with app.app_context():
        # Setup admin user
        admin = User(email="admin_test@southeast.com", full_name="Admin Test", role=UserRole.ADMIN)
        admin.set_password("AdminPass123!")
        db.session.add(admin)

        # Setup manager user
        mgr = User(email="manager_test@southeast.com", full_name="Manager Test", role=UserRole.MANAGER)
        mgr.set_password("ManagerPass123!")
        db.session.add(mgr)

        # Setup lead owner user
        owner = User(email="owner_test@southeast.com", full_name="Owner Test", role=UserRole.LEAD_OWNER)
        owner.set_password("OwnerPass123!")
        db.session.add(owner)
        db.session.commit()

        # Login admin
        res = client.post('/api/auth/login', json={"email": "admin_test@southeast.com", "password": "AdminPass123!"})
        assert res.status_code == 200, f"Login failed: {res.data}"
        token = res.json.get('access_token')
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Activity Labels
        print("1. Testing Activity Labels endpoints...")
        res = client.get('/api/settings/activity-labels', headers=headers)
        assert res.status_code == 200
        labels = res.json
        assert len(labels) >= 5, "Default labels should be seeded"
        print(f"   [PASS] Seeded labels count: {len(labels)}")

        res = client.post('/api/settings/activity-labels', headers=headers, json={"name": "Urgent Token", "color": "#f43f5e", "description": "Token pending"})
        assert res.status_code == 201
        new_label_id = res.json['id']
        print("   [PASS] Created custom activity label")

        # 2. Questionnaire Settings
        print("2. Testing Questionnaire Settings...")
        res = client.get('/api/settings/questionnaire', headers=headers)
        assert res.status_code == 200
        questions = res.json
        assert len(questions) >= 10, "Default questionnaire should be seeded"
        print(f"   [PASS] Seeded questionnaire count: {len(questions)}")

        # 3. Create Lead with Profession & Service Type
        print("3. Testing Lead creation with profession, service_type, questionnaire...")
        lead_payload = {
            "full_name": "Engr. Kabir Ahmed",
            "phone": "01799887766",
            "email": "kabir@test.com",
            "source": "Facebook Ad",
            "profession": "Engineer",
            "service_type": "Residential Plot",
            "activity_label": "VIP Client",
            "questionnaire_answers": {
                "profession": "Engineer",
                "service_type": "Residential Plot",
                "plot_size": "5 Katha",
                "budget_range": "40 - 70 Lakhs"
            }
        }
        res = client.post('/api/leads/', headers=headers, json=lead_payload)
        assert res.status_code == 201, f"Lead create failed: {res.data}"
        lead_id = res.json['id']
        assert res.json['contact']['profession'] == "Engineer"
        assert res.json['contact']['service_type'] == "Residential Plot"
        assert res.json['service_type'] == "Residential Plot"
        print("   [PASS] Created lead with profession & service_type")

        # 4. Get & Update Lead Questionnaire
        print("4. Testing Lead questionnaire get & update...")
        res = client.get(f'/api/leads/{lead_id}/questionnaire', headers=headers)
        assert res.status_code == 200
        assert res.json['answers']['plot_size'] == "5 Katha"

        res = client.put(f'/api/leads/{lead_id}/questionnaire', headers=headers, json={
            "answers": {
                "plot_size": "10 Katha",
                "purchasing_timeline": "Immediate / Ready to Buy",
                "profession": "Lead Architect"
            }
        })
        assert res.status_code == 200
        assert res.json['answers']['plot_size'] == "10 Katha"
        print("   [PASS] Updated lead questionnaire answers")

        # 5. Lead Import with Duplicate Detection
        print("5. Testing Lead Import & Auto-Deduplication...")
        csv_data = (
            "Full Name,Phone Number,Email,Profession,Service Type,Project Name,Budget Range,Source,Notes\n"
            "Engr. Kabir Ahmed,01799887766,kabir_new@test.com,Senior Engineer,Villa / Duplex Plot,Green Valley,70 Lakhs,Walk-in,Wants corner plot\n"
            "Mrs. Sultana Rahman,01555112233,sultana@test.com,Doctor,Commercial Plot,Lake View,1 Crore,Referral,High priority\n"
        )
        data = {
            'file': (io.BytesIO(csv_data.encode('utf-8')), 'test_leads.csv'),
            'duplicate_strategy': 'merge'
        }
        res = client.post('/api/leads/import', headers=headers, data=data, content_type='multipart/form-data')
        assert res.status_code == 200, f"Import failed: {res.data}"
        import_stats = res.json
        assert import_stats['total_processed'] == 2
        assert import_stats['merged_count'] == 1, "Kabir Ahmed should be recognized as duplicate and merged"
        assert import_stats['created_count'] == 1, "Sultana Rahman should be imported as new"
        print(f"   [PASS] Lead Import successful: {import_stats}")

        # 6. Auto-Update Stages Trigger
        print("6. Testing Auto-update lead stages trigger...")
        res = client.post('/api/leads/auto-update-stages', headers=headers)
        assert res.status_code == 200
        assert res.json['status'] == 'success'
        print("   [PASS] Auto-update stages executed successfully")

        # 7. Sales Manager Summary
        print("7. Testing Sales Manager summary endpoint...")
        res = client.get('/api/reports/sales-manager-summary', headers=headers)
        assert res.status_code == 200
        summary = res.json
        assert "team_metrics" in summary
        assert "agent_workload" in summary
        assert summary['team_metrics']['total_agents'] >= 2
        print(f"   [PASS] Sales manager summary returned {len(summary['agent_workload'])} agent workloads")

        print("\nALL NEW FEATURES TESTS PASSED SUCCESSFULLY! (7/7)\n")

if __name__ == '__main__':
    test_suite()
