import sys
sys.path.insert(0, 'backend')
from app import create_app
from app.extensions import db
from app.models import User, UserRole, Opportunity, Contact

def test_sim():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        admin = User(email='admin_sim_test@crm.com', role=UserRole.ADMIN, full_name='Admin Sim')
        admin.set_password('AdminPass123!')
        db.session.add(admin)
        db.session.commit()

        with app.test_client() as client:
            login_res = client.post('/api/auth/login', json={'email': 'admin_sim_test@crm.com', 'password': 'AdminPass123!'})
            token = login_res.get_json()['access_token']
            headers = {'Authorization': f'Bearer {token}'}

            sim_res = client.post('/api/settings/simulate-meta-lead', json={
                'full_name': 'Dr. Test Simulation User',
                'phone': '01888999000',
                'email': 'dr_sim_test@example.com',
                'profession': 'Surgeon',
                'service_type': 'Commercial Plot',
                'budget': '1-2 Crore',
                'plot_size': '10 Katha',
                'campaign_name': 'FACEBOOK_SIMULATED_AD'
            }, headers=headers)

            print('STATUS:', sim_res.status_code)
            res_data = sim_res.get_json()
            print('RESPONSE:', res_data)
            assert sim_res.status_code == 200, f'Expected 200, got {sim_res.status_code}'
            assert res_data['success'] is True

            contact = Contact.query.filter_by(phone_raw='01888999000').first()
            assert contact is not None, 'Contact not created!'
            print('CONTACT FOUND:', contact.full_name, '|', contact.profession, '|', contact.service_type)

            opp = Opportunity.query.filter_by(contact_id=contact.id).first()
            assert opp is not None, 'Opportunity not created!'
            print('OPPORTUNITY CREATED:', opp.id, '| Campaign:', opp.campaign_name, '| Source:', opp.source)
            print('QUESTIONNAIRE ANSWERS:', opp.questionnaire_answers)
            print('\nALL SIMULATION CHECKS PASSED SUCCESSFULLY!')

if __name__ == '__main__':
    test_sim()
